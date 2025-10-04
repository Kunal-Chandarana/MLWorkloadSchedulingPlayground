"""
Metrics collection and exposition for the scheduler
"""

import time
import logging
from typing import Dict, Any
from datetime import datetime
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from kubernetes import client

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect and expose scheduler metrics"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.metrics: Dict[str, Any] = {
            'pods_scheduled': 0,
            'scheduling_failures': 0,
            'scheduling_latency_ms': [],
            'gpu_utilization': {},
            'queue_length': 0,
            'failure_reasons': {}
        }
        self.server = None
    
    def record_pod_scheduled(self, pod: client.V1Pod, node: client.V1Node):
        """Record successful pod scheduling"""
        self.metrics['pods_scheduled'] += 1
        
        # Calculate latency if creation timestamp available
        if pod.metadata.creation_timestamp:
            latency = (datetime.now(pod.metadata.creation_timestamp.tzinfo) - 
                      pod.metadata.creation_timestamp).total_seconds() * 1000
            self.metrics['scheduling_latency_ms'].append(latency)
            
            # Keep only last 1000 measurements
            if len(self.metrics['scheduling_latency_ms']) > 1000:
                self.metrics['scheduling_latency_ms'] = \
                    self.metrics['scheduling_latency_ms'][-1000:]
    
    def record_scheduling_failure(self, pod: client.V1Pod, reason: str):
        """Record scheduling failure"""
        self.metrics['scheduling_failures'] += 1
        
        if reason not in self.metrics['failure_reasons']:
            self.metrics['failure_reasons'][reason] = 0
        self.metrics['failure_reasons'][reason] += 1
    
    def update_queue_length(self, length: int):
        """Update pending queue length"""
        self.metrics['queue_length'] = length
    
    def update_gpu_utilization(self, node_name: str, utilization: float):
        """Update GPU utilization for a node"""
        self.metrics['gpu_utilization'][node_name] = utilization
    
    def get_metrics_text(self) -> str:
        """Generate Prometheus-formatted metrics"""
        lines = []
        
        # Pods scheduled
        lines.append("# HELP scheduler_pods_scheduled_total Total number of pods scheduled")
        lines.append("# TYPE scheduler_pods_scheduled_total counter")
        lines.append(f"scheduler_pods_scheduled_total {self.metrics['pods_scheduled']}")
        lines.append("")
        
        # Scheduling failures
        lines.append("# HELP scheduler_failures_total Total number of scheduling failures")
        lines.append("# TYPE scheduler_failures_total counter")
        lines.append(f"scheduler_failures_total {self.metrics['scheduling_failures']}")
        lines.append("")
        
        # Failure reasons
        lines.append("# HELP scheduler_failures_by_reason Scheduling failures by reason")
        lines.append("# TYPE scheduler_failures_by_reason counter")
        for reason, count in self.metrics['failure_reasons'].items():
            lines.append(f'scheduler_failures_by_reason{{reason="{reason}"}} {count}')
        lines.append("")
        
        # Scheduling latency
        if self.metrics['scheduling_latency_ms']:
            latencies = self.metrics['scheduling_latency_ms']
            avg_latency = sum(latencies) / len(latencies)
            lines.append("# HELP scheduler_latency_ms Average scheduling latency in milliseconds")
            lines.append("# TYPE scheduler_latency_ms gauge")
            lines.append(f"scheduler_latency_ms {avg_latency:.2f}")
            lines.append("")
        
        # Queue length
        lines.append("# HELP scheduler_queue_length Current pending queue length")
        lines.append("# TYPE scheduler_queue_length gauge")
        lines.append(f"scheduler_queue_length {self.metrics['queue_length']}")
        lines.append("")
        
        # GPU utilization
        lines.append("# HELP scheduler_gpu_utilization GPU utilization by node")
        lines.append("# TYPE scheduler_gpu_utilization gauge")
        for node, util in self.metrics['gpu_utilization'].items():
            lines.append(f'scheduler_gpu_utilization{{node="{node}"}} {util:.2f}')
        lines.append("")
        
        return "\n".join(lines)
    
    def start(self):
        """Start metrics HTTP server"""
        collector = self
        
        class MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/metrics':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(collector.get_metrics_text().encode('utf-8'))
                elif self.path == '/health':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'OK')
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                # Suppress request logs
                pass
        
        def run_server():
            try:
                self.server = HTTPServer(('0.0.0.0', self.port), MetricsHandler)
                logger.info(f"Metrics server started on port {self.port}")
                self.server.serve_forever()
            except Exception as e:
                logger.error(f"Metrics server error: {e}")
        
        thread = Thread(target=run_server, daemon=True)
        thread.start()

