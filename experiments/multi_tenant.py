#!/usr/bin/env python3
"""
Multi-Tenant Workload Simulation

Simulate a multi-tenant cluster with different teams submitting
jobs and competing for GPU resources.
"""

import subprocess
import time
import json
import random
from typing import List, Dict


JOB_TEMPLATE = """
apiVersion: v1
kind: Pod
metadata:
  name: {name}
  labels:
    user: {team}
    priority: {priority}
    experiment: multi-tenant
spec:
  schedulerName: gpu-scheduler
  restartPolicy: Never
  containers:
  - name: training
    image: pytorch-training:latest
    imagePullPolicy: IfNotPresent
    command: ["python", "simple-training.py"]
    args:
      - "--duration={duration}"
      - "--model-size={model_size}"
      - "--job-name={name}"
    resources:
      requests:
        nvidia.com/gpu: {gpus}
      limits:
        nvidia.com/gpu: {gpus}
"""


def generate_jobs(num_jobs: int = 15) -> List[Dict]:
    """Generate random training jobs for different teams"""
    teams = ['team-a', 'team-b', 'team-c']
    priorities = ['high', 'medium', 'low']
    model_sizes = ['small', 'medium', 'large']
    
    jobs = []
    for i in range(num_jobs):
        team = random.choice(teams)
        priority = random.choice(priorities)
        
        job = {
            'name': f'multi-tenant-job-{i}',
            'team': team,
            'priority': priority,
            'duration': random.randint(60, 180),
            'model_size': random.choice(model_sizes),
            'gpus': random.choice([1, 2])
        }
        jobs.append(job)
    
    return jobs


def submit_jobs(jobs: List[Dict]):
    """Submit all jobs to the cluster"""
    print(f"\nSubmitting {len(jobs)} jobs from different teams...")
    
    for i, job in enumerate(jobs):
        yaml_content = JOB_TEMPLATE.format(**job)
        
        with open(f'/tmp/job-{i}.yaml', 'w') as f:
            f.write(yaml_content)
        
        subprocess.run(['kubectl', 'apply', '-f', f'/tmp/job-{i}.yaml'],
                      capture_output=True)
        
        # Small delay between submissions
        time.sleep(0.5)
    
    print("All jobs submitted!")


def monitor_fairness():
    """Monitor resource allocation fairness across teams"""
    print("\nMonitoring resource allocation across teams...\n")
    
    for i in range(60):  # Monitor for 60 seconds
        time.sleep(1)
        
        output = subprocess.run(
            ['kubectl', 'get', 'pods', '-l', 'experiment=multi-tenant',
             '-o', 'json'],
            capture_output=True,
            text=True
        )
        
        data = json.loads(output.stdout)
        
        # Calculate per-team statistics
        team_stats = {}
        
        for pod in data['items']:
            team = pod['metadata']['labels'].get('user', 'unknown')
            phase = pod['status']['phase']
            
            if team not in team_stats:
                team_stats[team] = {'running': 0, 'pending': 0, 'gpus': 0}
            
            if phase == 'Running':
                team_stats[team]['running'] += 1
                # Count GPUs
                for container in pod['spec']['containers']:
                    if 'resources' in container and 'requests' in container['resources']:
                        gpus = int(container['resources']['requests'].get('nvidia.com/gpu', 0))
                        team_stats[team]['gpus'] += gpus
            elif phase == 'Pending':
                team_stats[team]['pending'] += 1
        
        # Display stats
        if i % 5 == 0:  # Print every 5 seconds
            print(f"\n[{i}s] Team Resource Allocation:")
            print(f"{'TEAM':<15} {'RUNNING':<10} {'PENDING':<10} {'GPUs':<10}")
            print("-" * 45)
            
            for team in sorted(team_stats.keys()):
                stats = team_stats[team]
                print(f"{team:<15} {stats['running']:<10} {stats['pending']:<10} {stats['gpus']:<10}")


def analyze_results():
    """Analyze fairness of final allocation"""
    print("\n\nAnalyzing fairness...")
    
    output = subprocess.run(
        ['kubectl', 'get', 'pods', '-l', 'experiment=multi-tenant',
         '-o', 'json'],
        capture_output=True,
        text=True
    )
    
    data = json.loads(output.stdout)
    
    team_gpus = {}
    total_jobs = {}
    
    for pod in data['items']:
        team = pod['metadata']['labels'].get('user', 'unknown')
        
        if team not in team_gpus:
            team_gpus[team] = 0
            total_jobs[team] = 0
        
        total_jobs[team] += 1
        
        if pod['status']['phase'] == 'Running':
            for container in pod['spec']['containers']:
                if 'resources' in container and 'requests' in container['resources']:
                    gpus = int(container['resources']['requests'].get('nvidia.com/gpu', 0))
                    team_gpus[team] += gpus
    
    print("\n=== Final Resource Allocation ===")
    print(f"{'TEAM':<15} {'TOTAL JOBS':<12} {'GPUs ALLOCATED':<15} {'JOBS RUNNING':<15}")
    print("-" * 60)
    
    for team in sorted(team_gpus.keys()):
        running = sum(1 for p in data['items'] 
                     if p['metadata']['labels'].get('user') == team 
                     and p['status']['phase'] == 'Running')
        print(f"{team:<15} {total_jobs[team]:<12} {team_gpus[team]:<15} {running:<15}")


def cleanup():
    """Cleanup all experiment jobs"""
    print("\n\nCleaning up experiment jobs...")
    subprocess.run([
        'kubectl', 'delete', 'pods', '-l', 'experiment=multi-tenant'
    ])


def main():
    """Main entry point"""
    print("=" * 60)
    print("MULTI-TENANT WORKLOAD SIMULATION")
    print("=" * 60)
    print("\nThis experiment simulates multiple teams competing for")
    print("GPU resources with fair-share scheduling.")
    print()
    
    try:
        # Generate and submit jobs
        jobs = generate_jobs(num_jobs=15)
        
        print("Job distribution:")
        team_counts = {}
        for job in jobs:
            team = job['team']
            team_counts[team] = team_counts.get(team, 0) + 1
        
        for team, count in sorted(team_counts.items()):
            print(f"  {team}: {count} jobs")
        
        submit_jobs(jobs)
        
        # Monitor fairness
        monitor_fairness()
        
        # Analyze results
        analyze_results()
        
    except KeyboardInterrupt:
        print("\n\nExperiment interrupted")
    finally:
        cleanup()


if __name__ == '__main__':
    main()

