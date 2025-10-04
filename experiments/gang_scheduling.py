#!/usr/bin/env python3
"""
Gang Scheduling Experiment

Test gang scheduling with distributed training jobs that require
all pods to be scheduled together.
"""

import subprocess
import time
import json
from typing import List


def run_kubectl(args: List[str]) -> str:
    """Run kubectl command"""
    result = subprocess.run(
        ['kubectl'] + args,
        capture_output=True,
        text=True
    )
    return result.stdout


def setup_gang_scheduler():
    """Configure scheduler for gang scheduling"""
    print("Configuring scheduler for gang scheduling...")
    
    # Update to gang policy
    config = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: scheduler-config
  namespace: scheduler-system
data:
  config.yaml: |
    scheduler:
      name: "gpu-scheduler"
      policy: "gang"
      preemption_enabled: false
      checkpoint_interval: 300
    monitoring:
      enabled: true
      metrics_port: 8080
    policies:
      gang:
        timeout: 300
"""
    
    with open('/tmp/gang-config.yaml', 'w') as f:
        f.write(config)
    
    subprocess.run(['kubectl', 'apply', '-f', '/tmp/gang-config.yaml'])
    
    # Restart scheduler
    subprocess.run([
        'kubectl', 'rollout', 'restart', 'deployment/gpu-scheduler',
        '-n', 'scheduler-system'
    ])
    subprocess.run([
        'kubectl', 'rollout', 'status', 'deployment/gpu-scheduler',
        '-n', 'scheduler-system', '--timeout=60s'
    ])
    
    time.sleep(5)
    print("Gang scheduling enabled!")


def submit_distributed_job():
    """Submit distributed training job"""
    print("\nSubmitting distributed training job (requires 3 pods with 2 GPUs each)...")
    subprocess.run(['kubectl', 'apply', '-f', 'examples/distributed-training.yaml'])
    print("Job submitted!")


def monitor_gang_scheduling():
    """Monitor gang scheduling behavior"""
    print("\nMonitoring gang scheduling...")
    print("Waiting for all gang members to be scheduled together...\n")
    
    gang_name = "pytorch-distributed-gang"
    
    for i in range(30):  # Monitor for 30 seconds
        output = run_kubectl([
            'get', 'pods', '--all-namespaces',
            '-l', f'gang.scheduling.k8s.io/name={gang_name}',
            '-o', 'json'
        ])
        
        data = json.loads(output)
        
        if not data['items']:
            time.sleep(1)
            continue
        
        total = len(data['items'])
        scheduled = sum(1 for p in data['items'] if p['spec'].get('nodeName'))
        pending = total - scheduled
        
        print(f"[{i+1}s] Gang status: {scheduled}/{total} scheduled, {pending} pending")
        
        if scheduled == total:
            print("\n✓ All gang members scheduled successfully!")
            print("\nPod placement:")
            for pod in data['items']:
                name = pod['metadata']['name']
                node = pod['spec'].get('nodeName', 'N/A')
                print(f"  {name} -> {node}")
            break
        
        time.sleep(1)
    else:
        print("\n⚠ Gang scheduling timeout - not all members scheduled")
        print("This is expected if there aren't enough GPU resources")


def cleanup():
    """Cleanup resources"""
    print("\nCleaning up...")
    subprocess.run([
        'kubectl', 'delete', '-f', 'examples/distributed-training.yaml'
    ])


def main():
    """Main entry point"""
    print("=" * 60)
    print("GANG SCHEDULING EXPERIMENT")
    print("=" * 60)
    print("\nThis experiment tests all-or-nothing scheduling for")
    print("distributed training jobs requiring multiple GPUs.")
    print()
    
    try:
        setup_gang_scheduler()
        submit_distributed_job()
        monitor_gang_scheduling()
    except KeyboardInterrupt:
        print("\n\nExperiment interrupted")
    finally:
        cleanup()


if __name__ == '__main__':
    main()

