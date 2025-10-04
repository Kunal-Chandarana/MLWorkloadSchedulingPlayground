"""
Scheduler configuration management
"""

import os
import yaml
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class SchedulerConfig:
    """Configuration for the GPU scheduler"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Load configuration from file or environment"""
        self.config_data = self._load_config(config_path)
        
        # Scheduler settings
        self.scheduler_name = self._get("scheduler.name", "gpu-scheduler")
        self.policy = self._get("scheduler.policy", "fifo")
        self.preemption_enabled = self._get("scheduler.preemption_enabled", False)
        self.checkpoint_interval = self._get("scheduler.checkpoint_interval", 300)
        
        # Metrics settings
        self.metrics_enabled = self._get("monitoring.enabled", True)
        self.metrics_port = self._get("monitoring.metrics_port", 8080)
        
        # Policy-specific settings
        self.priority_classes = self._get("policies.priority.classes", {})
        self.fair_share_weights = self._get("policies.fair_share.weights", {})
        self.gang_scheduling_timeout = self._get("policies.gang.timeout", 300)
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _get(self, key: str, default: Any = None) -> Any:
        """Get nested configuration value"""
        # Check environment variable first
        env_key = f"SCHEDULER_{key.upper().replace('.', '_')}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value
        
        # Get from config file
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

