"""
Fair-share scheduling policy

Distributes GPU resources fairly among users/teams based on configured weights.
"""

from typing import List, Optional, Dict
from collections import defaultdict
import logging
from kubernetes import client

from .base import SchedulingPolicy

logger = logging.getLogger(__name__)


class FairSharePolicy(SchedulingPolicy):
    """Fair-share scheduling for multi-tenant clusters"""
    
    def __init__(self, config):
        super().__init__(config)
        self.usage_cache: Dict[str, int] = defaultdict(int)
        self.last_update = 0
    
    def select_node(self, pod: client.V1Pod, 
                   nodes: List[client.V1Node],
                   scheduler) -> Optional[client.V1Node]:
        """
        Select node while considering fair-share among users
        
        Strategy:
        1. Calculate current resource usage per user
        2. Give preference to users who are under their fair share
        3. Among suitable nodes, select the one that best balances usage
        """
        if not nodes:
            return None
        
        # Get pod owner
        owner = self.get_pod_owner(pod)
        
        # Update usage statistics
        self._update_usage(scheduler)
        
        # Calculate fair share metrics
        total_usage = sum(self.usage_cache.values())
        owner_usage = self.usage_cache[owner]
        
        # Get owner weight (default to 1.0)
        weights = self.config.fair_share_weights
        owner_weight = weights.get(owner, 1.0)
        total_weight = sum(weights.values()) or 1.0
        
        # Calculate if owner is under/over their fair share
        fair_share = (owner_weight / total_weight) * total_usage if total_usage > 0 else 0
        usage_ratio = owner_usage / fair_share if fair_share > 0 else 0
        
        logger.debug(
            f"Fair-share for {owner}: usage={owner_usage}, "
            f"fair_share={fair_share:.1f}, ratio={usage_ratio:.2f}"
        )
        
        # Select node with most available GPUs
        # (in a real implementation, you might consider the usage ratio for throttling)
        best_node = None
        max_available = -1
        
        for node in nodes:
            gpu_info = scheduler.get_node_gpu_capacity(node)
            available = gpu_info['allocatable']
            
            if available > max_available:
                max_available = available
                best_node = node
        
        # Log if user is over their fair share
        if usage_ratio > 1.2:  # 20% over fair share
            logger.warning(
                f"User {owner} is over fair share ({usage_ratio:.1f}x), "
                f"but scheduling anyway (implement throttling if desired)"
            )
        
        return best_node
    
    def _update_usage(self, scheduler):
        """Update resource usage statistics for all users"""
        import time
        
        # Update cache every 30 seconds
        current_time = time.time()
        if current_time - self.last_update < 30:
            return
        
        self.last_update = current_time
        self.usage_cache.clear()
        
        try:
            # Get all pods in the cluster
            pods = scheduler.v1.list_pod_for_all_namespaces()
            
            for pod in pods.items:
                # Only count running or pending pods
                if pod.status.phase not in ['Running', 'Pending']:
                    continue
                
                owner = self.get_pod_owner(pod)
                gpu_count = scheduler.get_gpu_resource(pod)
                self.usage_cache[owner] += gpu_count
        
        except Exception as e:
            logger.error(f"Error updating usage statistics: {e}")

