#!/usr/bin/env python3
"""
Compare different scheduling policies

This experiment submits multiple jobs and compares how different
scheduling policies handle them.
"""

import subprocess
import time
import json
from datetime import datetime
from typing import List, Dict


class PolicyComparison:
    """Compare scheduling policies"""
    
    def __init__(self):
        self.results = {}
    
    def run_kubectl(self, args: List[str]) -> str:
        """Run kubectl command"""
        result = subprocess.run(
            ['kubectl'] + args,
            capture_output=True,
            text=True
        )
        return result.stdout
    
    def update_scheduler_policy(self, policy: str):
        """Update scheduler configuration to use a different policy"""
        print(f"\n=== Switching to {policy.upper()} policy ===")
        
        # Update ConfigMap
        config_patch = f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: scheduler-config
  namespace: scheduler-system
data:
  config.yaml: |
    scheduler:
      name: "gpu-scheduler"
      policy: "{policy}"
      preemption_enabled: false
      checkpoint_interval: 300
    monitoring:
      enabled: true
      metrics_port: 8080
    policies:
      priority:
        classes:
          high: 1000
          medium: 500
          low: 100
      fair_share:
        weights:
          team-a: 2.0
          team-b: 1.5
          team-c: 1.0
          default: 1.0
      gang:
        timeout: 300
"""
        
        with open('/tmp/scheduler-config-patch.yaml', 'w') as f:
            f.write(config_patch)
        
        subprocess.run(['kubectl', 'apply', '-f', '/tmp/scheduler-config-patch.yaml'])
        
        # Restart scheduler
        print("Restarting scheduler...")
        subprocess.run([
            'kubectl', 'rollout', 'restart', 'deployment/gpu-scheduler',
            '-n', 'scheduler-system'
        ])
        
        # Wait for restart
        subprocess.run([
            'kubectl', 'rollout', 'status', 'deployment/gpu-scheduler',
            '-n', 'scheduler-system', '--timeout=60s'
        ])
        
        time.sleep(5)
        print(f"Scheduler now using {policy} policy")
    
    def submit_test_jobs(self):
        """Submit a batch of test jobs"""
        print("\nSubmitting test jobs...")
        subprocess.run(['kubectl', 'apply', '-f', 'examples/multi-job-batch.yaml'])
        print("Jobs submitted!")
    
    def cleanup_jobs(self):
        """Delete all test jobs"""
        print("\nCleaning up jobs...")
        subprocess.run([
            'kubectl', 'delete', 'pods',
            '--selector', 'schedulerName=gpu-scheduler',
            '--all-namespaces'
        ])
        time.sleep(10)
    
    def collect_metrics(self, policy: str) -> Dict:
        """Collect scheduling metrics"""
        print(f"\nCollecting metrics for {policy}...")
        
        # Wait for jobs to be scheduled
        time.sleep(15)
        
        # Get pod status
        output = self.run_kubectl([
            'get', 'pods', '--all-namespaces',
            '--field-selector', 'spec.schedulerName=gpu-scheduler',
            '-o', 'json'
        ])
        
        data = json.loads(output)
        
        metrics = {
            'policy': policy,
            'total_jobs': len(data['items']),
            'scheduled': 0,
            'pending': 0,
            'scheduling_times': [],
            'node_distribution': {}
        }
        
        for pod in data['items']:
            if pod['status']['phase'] == 'Pending':
                metrics['pending'] += 1
            else:
                metrics['scheduled'] += 1
                
                # Calculate scheduling time
                created = pod['metadata']['creationTimestamp']
                if pod['status'].get('conditions'):
                    for condition in pod['status']['conditions']:
                        if condition['type'] == 'PodScheduled' and condition['status'] == 'True':
                            scheduled_time = condition['lastTransitionTime']
                            # In real implementation, calculate time difference
                            break
                
                # Node distribution
                node = pod['spec'].get('nodeName', 'unscheduled')
                metrics['node_distribution'][node] = \
                    metrics['node_distribution'].get(node, 0) + 1
        
        return metrics
    
    def display_results(self):
        """Display comparison results"""
        print("\n" + "=" * 60)
        print("POLICY COMPARISON RESULTS")
        print("=" * 60)
        
        for policy, metrics in self.results.items():
            print(f"\n{policy.upper()} Policy:")
            print(f"  Total jobs: {metrics['total_jobs']}")
            print(f"  Scheduled: {metrics['scheduled']}")
            print(f"  Pending: {metrics['pending']}")
            print(f"  Node distribution: {metrics['node_distribution']}")
    
    def run_experiment(self):
        """Run the full comparison experiment"""
        print("=" * 60)
        print("SCHEDULING POLICY COMPARISON EXPERIMENT")
        print("=" * 60)
        
        policies = ['fifo', 'priority', 'fair_share']
        
        for policy in policies:
            try:
                # Switch policy
                self.update_scheduler_policy(policy)
                
                # Submit jobs
                self.submit_test_jobs()
                
                # Collect metrics
                metrics = self.collect_metrics(policy)
                self.results[policy] = metrics
                
                # Cleanup
                self.cleanup_jobs()
                
            except Exception as e:
                print(f"Error testing {policy}: {e}")
        
        # Display results
        self.display_results()


def main():
    """Main entry point"""
    experiment = PolicyComparison()
    experiment.run_experiment()


if __name__ == '__main__':
    main()

