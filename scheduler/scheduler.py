#!/usr/bin/env python3
"""
Custom Kubernetes GPU Scheduler

This scheduler watches for unscheduled pods with GPU requirements,
evaluates available nodes using configurable policies, and binds pods to nodes.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

from policies.base import SchedulingPolicy
from policies.fifo import FIFOPolicy
from policies.priority import PriorityPolicy
from policies.fair_share import FairSharePolicy
from policies.gang_scheduling import GangSchedulingPolicy
from metrics import MetricsCollector
from config import SchedulerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GPUScheduler:
    """Custom Kubernetes scheduler for GPU workloads"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the scheduler"""
        self.config = SchedulerConfig(config_path)
        self.scheduler_name = self.config.scheduler_name
        
        # Initialize Kubernetes client
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except config.ConfigException:
            config.load_kube_config()
            logger.info("Loaded local Kubernetes config")
        
        self.v1 = client.CoreV1Api()
        self.scheduling_api = client.SchedulingV1Api()
        
        # Initialize scheduling policy
        self.policy = self._init_policy()
        
        # Initialize metrics collector
        self.metrics = MetricsCollector(self.config.metrics_port)
        
        # Track scheduled pods for metrics
        self.scheduled_pods: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Scheduler initialized with policy: {self.config.policy}")
    
    def _init_policy(self) -> SchedulingPolicy:
        """Initialize the scheduling policy based on config"""
        policy_name = self.config.policy.lower()
        
        policies = {
            'fifo': FIFOPolicy,
            'priority': PriorityPolicy,
            'fair_share': FairSharePolicy,
            'gang': GangSchedulingPolicy,
        }
        
        if policy_name not in policies:
            logger.warning(f"Unknown policy '{policy_name}', defaulting to FIFO")
            policy_name = 'fifo'
        
        policy_class = policies[policy_name]
        return policy_class(self.config)
    
    def get_gpu_resource(self, pod: client.V1Pod) -> int:
        """Extract GPU resource request from pod"""
        gpu_count = 0
        
        for container in pod.spec.containers:
            if container.resources and container.resources.requests:
                # Check for nvidia.com/gpu or amd.com/gpu
                for gpu_key in ['nvidia.com/gpu', 'amd.com/gpu', 'gpu']:
                    if gpu_key in container.resources.requests:
                        gpu_count += int(container.resources.requests[gpu_key])
        
        return gpu_count
    
    def get_available_nodes(self) -> List[client.V1Node]:
        """Get all schedulable nodes with GPU resources"""
        try:
            nodes = self.v1.list_node()
            available_nodes = []
            
            for node in nodes.items:
                # Check if node is schedulable
                if node.spec.unschedulable:
                    continue
                
                # Check if node is ready
                is_ready = False
                for condition in node.status.conditions:
                    if condition.type == "Ready" and condition.status == "True":
                        is_ready = True
                        break
                
                if not is_ready:
                    continue
                
                # Check if node has GPU resources
                if node.status.allocatable:
                    has_gpu = any(
                        key in node.status.allocatable 
                        for key in ['nvidia.com/gpu', 'amd.com/gpu', 'gpu']
                    )
                    if has_gpu:
                        available_nodes.append(node)
            
            return available_nodes
        
        except ApiException as e:
            logger.error(f"Error listing nodes: {e}")
            return []
    
    def get_node_gpu_capacity(self, node: client.V1Node) -> Dict[str, int]:
        """Get GPU capacity and available GPUs on a node"""
        capacity = 0
        allocatable = 0
        
        if node.status.capacity:
            for key in ['nvidia.com/gpu', 'amd.com/gpu', 'gpu']:
                if key in node.status.capacity:
                    capacity = int(node.status.capacity[key])
                    break
        
        if node.status.allocatable:
            for key in ['nvidia.com/gpu', 'amd.com/gpu', 'gpu']:
                if key in node.status.allocatable:
                    allocatable = int(node.status.allocatable[key])
                    break
        
        # Calculate used GPUs by checking running pods
        used = capacity - allocatable
        
        return {
            'capacity': capacity,
            'allocatable': allocatable,
            'used': used
        }
    
    def get_pods_on_node(self, node_name: str) -> List[client.V1Pod]:
        """Get all pods running on a specific node"""
        try:
            field_selector = f"spec.nodeName={node_name}"
            pods = self.v1.list_pod_for_all_namespaces(field_selector=field_selector)
            return pods.items
        except ApiException as e:
            logger.error(f"Error listing pods on node {node_name}: {e}")
            return []
    
    def can_fit_on_node(self, pod: client.V1Pod, node: client.V1Node) -> bool:
        """Check if pod can fit on node based on GPU resources"""
        required_gpus = self.get_gpu_resource(pod)
        
        if required_gpus == 0:
            return True  # Non-GPU pods can be scheduled
        
        gpu_info = self.get_node_gpu_capacity(node)
        return gpu_info['allocatable'] >= required_gpus
    
    def bind_pod_to_node(self, pod: client.V1Pod, node: client.V1Node) -> bool:
        """Bind a pod to a node"""
        binding = client.V1Binding(
            api_version="v1",
            kind="Binding",
            metadata=client.V1ObjectMeta(
                name=pod.metadata.name,
                namespace=pod.metadata.namespace
            ),
            target=client.V1ObjectReference(
                api_version="v1",
                kind="Node",
                name=node.metadata.name
            )
        )
        
        try:
            self.v1.create_namespaced_binding(
                namespace=pod.metadata.namespace,
                body=binding
            )
            
            # Log scheduling decision
            gpu_count = self.get_gpu_resource(pod)
            logger.info(
                f"✓ Scheduled pod {pod.metadata.namespace}/{pod.metadata.name} "
                f"to node {node.metadata.name} (GPUs: {gpu_count})"
            )
            
            # Record metrics
            self.scheduled_pods[f"{pod.metadata.namespace}/{pod.metadata.name}"] = {
                'scheduled_at': datetime.now(),
                'node': node.metadata.name,
                'gpus': gpu_count
            }
            self.metrics.record_pod_scheduled(pod, node)
            
            # Send event
            self._send_event(pod, node, "Scheduled", "Successfully scheduled pod")
            
            return True
        
        except ApiException as e:
            if e.status == 409:
                logger.debug(f"Pod {pod.metadata.name} already bound")
            else:
                logger.error(f"Error binding pod {pod.metadata.name} to {node.metadata.name}: {e}")
            return False
    
    def _send_event(self, pod: client.V1Pod, node: client.V1Node, 
                    reason: str, message: str):
        """Send a Kubernetes event for the scheduling decision"""
        try:
            event = client.CoreV1Event(
                metadata=client.V1ObjectMeta(
                    name=f"{pod.metadata.name}.{int(time.time())}",
                    namespace=pod.metadata.namespace
                ),
                involved_object=client.V1ObjectReference(
                    api_version="v1",
                    kind="Pod",
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    uid=pod.metadata.uid
                ),
                reason=reason,
                message=message,
                first_timestamp=datetime.utcnow(),
                last_timestamp=datetime.utcnow(),
                count=1,
                type="Normal",
                source=client.V1EventSource(component=self.scheduler_name)
            )
            
            self.v1.create_namespaced_event(
                namespace=pod.metadata.namespace,
                body=event
            )
        except ApiException as e:
            logger.debug(f"Could not create event: {e}")
    
    def schedule_pod(self, pod: client.V1Pod):
        """Schedule a single pod"""
        # Get available nodes
        nodes = self.get_available_nodes()
        
        if not nodes:
            logger.warning(f"No available GPU nodes for pod {pod.metadata.name}")
            self.metrics.record_scheduling_failure(pod, "NoAvailableNodes")
            return
        
        # Filter nodes that can fit the pod
        suitable_nodes = [node for node in nodes if self.can_fit_on_node(pod, node)]
        
        if not suitable_nodes:
            logger.warning(
                f"No suitable nodes for pod {pod.metadata.name} "
                f"(requires {self.get_gpu_resource(pod)} GPUs)"
            )
            self.metrics.record_scheduling_failure(pod, "InsufficientResources")
            return
        
        # Use policy to select best node
        selected_node = self.policy.select_node(pod, suitable_nodes, self)
        
        if selected_node:
            self.bind_pod_to_node(pod, selected_node)
        else:
            logger.warning(f"Policy did not select a node for pod {pod.metadata.name}")
            self.metrics.record_scheduling_failure(pod, "PolicyRejected")
    
    def watch_for_pods(self):
        """Watch for unscheduled pods and schedule them"""
        logger.info(f"Starting scheduler watch loop (scheduler: {self.scheduler_name})")
        
        w = watch.Watch()
        
        try:
            for event in w.stream(
                self.v1.list_pod_for_all_namespaces,
                field_selector=f"spec.schedulerName={self.scheduler_name}"
            ):
                event_type = event['type']
                pod = event['object']
                
                # Only handle ADDED or MODIFIED events
                if event_type not in ['ADDED', 'MODIFIED']:
                    continue
                
                # Skip if already scheduled
                if pod.spec.node_name:
                    continue
                
                # Skip if pod is being deleted
                if pod.metadata.deletion_timestamp:
                    continue
                
                logger.info(
                    f"New pod to schedule: {pod.metadata.namespace}/{pod.metadata.name}"
                )
                
                # Schedule the pod
                try:
                    self.schedule_pod(pod)
                except Exception as e:
                    logger.error(f"Error scheduling pod {pod.metadata.name}: {e}", exc_info=True)
        
        except ApiException as e:
            logger.error(f"API exception in watch loop: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in watch loop: {e}", exc_info=True)
        finally:
            w.stop()
    
    def run(self):
        """Run the scheduler"""
        logger.info("Starting GPU Scheduler...")
        
        # Start metrics server
        self.metrics.start()
        
        # Main scheduling loop
        while True:
            try:
                self.watch_for_pods()
            except Exception as e:
                logger.error(f"Scheduler crashed: {e}", exc_info=True)
                logger.info("Restarting in 5 seconds...")
                time.sleep(5)


def main():
    """Main entry point"""
    scheduler = GPUScheduler()
    scheduler.run()


if __name__ == "__main__":
    main()

