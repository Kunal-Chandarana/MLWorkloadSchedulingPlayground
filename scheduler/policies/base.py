"""
Base class for scheduling policies
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from kubernetes import client


class SchedulingPolicy(ABC):
    """Abstract base class for scheduling policies"""
    
    def __init__(self, config):
        """Initialize policy with configuration"""
        self.config = config
    
    @abstractmethod
    def select_node(self, pod: client.V1Pod, 
                   nodes: List[client.V1Node],
                   scheduler) -> Optional[client.V1Node]:
        """
        Select the best node for the pod
        
        Args:
            pod: The pod to schedule
            nodes: List of suitable nodes
            scheduler: Reference to scheduler instance for accessing state
        
        Returns:
            Selected node or None if no suitable node
        """
        pass
    
    def get_pod_priority(self, pod: client.V1Pod) -> int:
        """Get priority of a pod (higher is more important)"""
        # Check for priority class
        if pod.spec.priority:
            return pod.spec.priority
        
        # Check annotations
        if pod.metadata.annotations:
            priority_str = pod.metadata.annotations.get('scheduler.alpha.kubernetes.io/priority', '0')
            try:
                return int(priority_str)
            except ValueError:
                pass
        
        return 0
    
    def get_pod_owner(self, pod: client.V1Pod) -> str:
        """Get the owner/user of the pod"""
        if pod.metadata.labels:
            return pod.metadata.labels.get('user', 'default')
        return 'default'

