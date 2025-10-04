"""
Priority-based scheduling policy

Schedules higher priority pods first, with optional preemption.
"""

from typing import List, Optional
import logging
from kubernetes import client

from .base import SchedulingPolicy

logger = logging.getLogger(__name__)


class PriorityPolicy(SchedulingPolicy):
    """Priority-based scheduling with preemption support"""
    
    def select_node(self, pod: client.V1Pod, 
                   nodes: List[client.V1Node],
                   scheduler) -> Optional[client.V1Node]:
        """
        Select best node considering pod priority
        
        Strategy:
        1. Try to find a node with available resources
        2. If preemption enabled and no resources, try to preempt lower priority pods
        3. Select node that minimizes fragmentation
        """
        if not nodes:
            return None
        
        pod_priority = self.get_pod_priority(pod)
        required_gpus = scheduler.get_gpu_resource(pod)
        
        # Try to find node with available resources
        best_node = None
        min_waste = float('inf')
        
        for node in nodes:
            gpu_info = scheduler.get_node_gpu_capacity(node)
            available = gpu_info['allocatable']
            
            if available >= required_gpus:
                # Calculate resource waste (prefer tighter fits)
                waste = available - required_gpus
                if waste < min_waste:
                    min_waste = waste
                    best_node = node
        
        if best_node:
            return best_node
        
        # If preemption enabled, try to preempt lower priority pods
        if self.config.preemption_enabled:
            logger.info(f"Attempting preemption for pod {pod.metadata.name} (priority: {pod_priority})")
            preemptible_node = self._find_preemptible_node(
                pod, nodes, pod_priority, required_gpus, scheduler
            )
            if preemptible_node:
                return preemptible_node
        
        return None
    
    def _find_preemptible_node(self, pod: client.V1Pod, nodes: List[client.V1Node],
                               pod_priority: int, required_gpus: int, scheduler) -> Optional[client.V1Node]:
        """Find a node where we can preempt lower priority pods"""
        for node in nodes:
            # Get all pods on this node
            node_pods = scheduler.get_pods_on_node(node.metadata.name)
            
            # Find pods with lower priority that use GPUs
            preemptible_pods = []
            preemptible_gpus = 0
            
            for p in node_pods:
                p_priority = self.get_pod_priority(p)
                if p_priority < pod_priority:
                    p_gpus = scheduler.get_gpu_resource(p)
                    if p_gpus > 0:
                        preemptible_pods.append((p, p_gpus))
                        preemptible_gpus += p_gpus
            
            # Check if preempting would free enough resources
            gpu_info = scheduler.get_node_gpu_capacity(node)
            if gpu_info['allocatable'] + preemptible_gpus >= required_gpus:
                # Preempt the pods
                self._preempt_pods(preemptible_pods, scheduler)
                logger.info(
                    f"Preempted {len(preemptible_pods)} pods on {node.metadata.name} "
                    f"to make room for {pod.metadata.name}"
                )
                return node
        
        return None
    
    def _preempt_pods(self, pods_to_preempt: List[tuple], scheduler):
        """Preempt (delete) lower priority pods"""
        for pod, _ in pods_to_preempt:
            try:
                scheduler.v1.delete_namespaced_pod(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    grace_period_seconds=30
                )
                logger.info(f"Preempted pod {pod.metadata.namespace}/{pod.metadata.name}")
            except Exception as e:
                logger.error(f"Failed to preempt pod {pod.metadata.name}: {e}")

