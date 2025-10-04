"""
First-In-First-Out (FIFO) scheduling policy

Schedules pods in order of arrival, selecting nodes with most available GPUs.
"""

from typing import List, Optional
from kubernetes import client

from .base import SchedulingPolicy


class FIFOPolicy(SchedulingPolicy):
    """Simple FIFO scheduling - first come, first served"""
    
    def select_node(self, pod: client.V1Pod, 
                   nodes: List[client.V1Node],
                   scheduler) -> Optional[client.V1Node]:
        """
        Select node with most available GPUs
        
        This implements a simple greedy strategy:
        1. Choose the node with the most available GPU resources
        2. This helps with resource consolidation
        """
        if not nodes:
            return None
        
        best_node = None
        max_available_gpus = -1
        
        for node in nodes:
            gpu_info = scheduler.get_node_gpu_capacity(node)
            available = gpu_info['allocatable']
            
            if available > max_available_gpus:
                max_available_gpus = available
                best_node = node
        
        return best_node

