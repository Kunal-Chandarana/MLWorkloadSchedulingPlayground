"""
Gang scheduling policy

All-or-nothing scheduling for distributed training jobs that require multiple pods.
"""

from typing import List, Optional, Dict, Set
from collections import defaultdict
import time
import logging
from kubernetes import client

from .base import SchedulingPolicy

logger = logging.getLogger(__name__)


class GangSchedulingPolicy(SchedulingPolicy):
    """Gang scheduling for distributed training jobs"""
    
    def __init__(self, config):
        super().__init__(config)
        # Track pod groups (gang members)
        self.pod_groups: Dict[str, Set[str]] = defaultdict(set)
        self.group_readiness: Dict[str, Dict] = {}
    
    def select_node(self, pod: client.V1Pod, 
                   nodes: List[client.V1Node],
                   scheduler) -> Optional[client.V1Node]:
        """
        Select node for gang scheduling
        
        Strategy:
        1. Identify pod's gang group
        2. Check if all gang members can be scheduled
        3. Only schedule if entire gang can fit
        4. Otherwise, wait or timeout
        """
        # Check if pod belongs to a gang
        gang_name = self._get_gang_name(pod)
        
        if not gang_name:
            # Not a gang member, use simple FIFO
            return self._simple_select(nodes, scheduler)
        
        # Get gang requirements
        min_members = self._get_gang_min_members(pod)
        
        # Get all pods in this gang
        gang_pods = self._get_gang_pods(gang_name, scheduler)
        
        logger.info(
            f"Gang scheduling for {gang_name}: "
            f"found {len(gang_pods)} pods, need {min_members}"
        )
        
        # Check if we have enough pods in the gang
        if len(gang_pods) < min_members:
            logger.info(f"Gang {gang_name} not ready: {len(gang_pods)}/{min_members} pods")
            return None
        
        # Try to schedule all gang members
        scheduled = self._try_schedule_gang(gang_pods, nodes, scheduler)
        
        if scheduled and pod.metadata.name in scheduled:
            # Return the node assigned to this specific pod
            return scheduled[pod.metadata.name]
        
        # Check for timeout
        if self._is_gang_timeout(gang_name, pod):
            logger.warning(f"Gang {gang_name} scheduling timeout, failing")
            # In a real system, you might want to fail the entire gang
        
        return None
    
    def _get_gang_name(self, pod: client.V1Pod) -> Optional[str]:
        """Extract gang name from pod labels/annotations"""
        if pod.metadata.labels:
            return pod.metadata.labels.get('gang.scheduling.k8s.io/name')
        return None
    
    def _get_gang_min_members(self, pod: client.V1Pod) -> int:
        """Get minimum number of pods required for gang"""
        if pod.metadata.annotations:
            min_str = pod.metadata.annotations.get(
                'gang.scheduling.k8s.io/min-members', '1'
            )
            try:
                return int(min_str)
            except ValueError:
                pass
        return 1
    
    def _get_gang_pods(self, gang_name: str, scheduler) -> List[client.V1Pod]:
        """Get all pods belonging to a gang"""
        try:
            pods = scheduler.v1.list_pod_for_all_namespaces(
                label_selector=f'gang.scheduling.k8s.io/name={gang_name}'
            )
            return [p for p in pods.items if not p.spec.node_name]
        except Exception as e:
            logger.error(f"Error getting gang pods: {e}")
            return []
    
    def _try_schedule_gang(self, gang_pods: List[client.V1Pod], 
                          nodes: List[client.V1Node],
                          scheduler) -> Optional[Dict[str, client.V1Node]]:
        """
        Try to find nodes for all gang members
        
        Returns:
            Dict mapping pod name to assigned node, or None if can't fit all
        """
        # Calculate total GPU requirements
        total_gpus_needed = sum(scheduler.get_gpu_resource(p) for p in gang_pods)
        
        # Calculate available GPUs across all nodes
        total_gpus_available = sum(
            scheduler.get_node_gpu_capacity(n)['allocatable'] 
            for n in nodes
        )
        
        if total_gpus_available < total_gpus_needed:
            logger.info(
                f"Insufficient total GPUs: need {total_gpus_needed}, "
                f"have {total_gpus_available}"
            )
            return None
        
        # Try to assign each pod to a node (simple greedy allocation)
        assignments = {}
        node_available = {
            n.metadata.name: scheduler.get_node_gpu_capacity(n)['allocatable']
            for n in nodes
        }
        
        for pod in sorted(gang_pods, 
                         key=lambda p: scheduler.get_gpu_resource(p), 
                         reverse=True):
            gpu_needed = scheduler.get_gpu_resource(pod)
            
            # Find a node that can fit this pod
            assigned = False
            for node in nodes:
                if node_available[node.metadata.name] >= gpu_needed:
                    assignments[pod.metadata.name] = node
                    node_available[node.metadata.name] -= gpu_needed
                    assigned = True
                    break
            
            if not assigned:
                logger.info(f"Could not assign pod {pod.metadata.name} to any node")
                return None
        
        logger.info(f"Successfully planned gang scheduling for {len(gang_pods)} pods")
        return assignments
    
    def _is_gang_timeout(self, gang_name: str, pod: client.V1Pod) -> bool:
        """Check if gang has exceeded scheduling timeout"""
        if gang_name not in self.group_readiness:
            self.group_readiness[gang_name] = {
                'first_seen': time.time()
            }
        
        first_seen = self.group_readiness[gang_name]['first_seen']
        elapsed = time.time() - first_seen
        
        return elapsed > self.config.gang_scheduling_timeout
    
    def _simple_select(self, nodes: List[client.V1Node], scheduler) -> Optional[client.V1Node]:
        """Simple node selection for non-gang pods"""
        if not nodes:
            return None
        
        best_node = None
        max_available = -1
        
        for node in nodes:
            gpu_info = scheduler.get_node_gpu_capacity(node)
            available = gpu_info['allocatable']
            
            if available > max_available:
                max_available = available
                best_node = node
        
        return best_node

