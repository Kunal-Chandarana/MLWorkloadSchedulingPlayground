#!/usr/bin/env python3
"""
GPU Scheduler CLI Tool

Command-line interface for managing GPU training jobs and monitoring cluster status.
"""

import sys
import argparse
import subprocess
import json
from typing import List, Dict
from datetime import datetime


class GPUSchedulerCLI:
    """CLI for GPU scheduler operations"""
    
    def __init__(self):
        self.scheduler_name = "gpu-scheduler"
    
    def run_kubectl(self, args: List[str]) -> str:
        """Run kubectl command and return output"""
        result = subprocess.run(
            ['kubectl'] + args,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Error: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        return result.stdout
    
    def list_jobs(self, args):
        """List all training jobs"""
        output = self.run_kubectl([
            'get', 'pods', '--all-namespaces',
            '--field-selector', f'spec.schedulerName={self.scheduler_name}',
            '-o', 'json'
        ])
        
        data = json.loads(output)
        
        print(f"{'NAME':<30} {'NAMESPACE':<15} {'STATUS':<12} {'NODE':<20} {'GPUs':<5}")
        print("-" * 85)
        
        for pod in data['items']:
            name = pod['metadata']['name']
            namespace = pod['metadata']['namespace']
            status = pod['status']['phase']
            node = pod['spec'].get('nodeName', 'N/A')
            
            # Get GPU count
            gpus = 0
            for container in pod['spec']['containers']:
                if 'resources' in container and 'requests' in container['resources']:
                    gpus += int(container['resources']['requests'].get('nvidia.com/gpu', 0))
            
            print(f"{name:<30} {namespace:<15} {status:<12} {node:<20} {gpus:<5}")
    
    def submit_job(self, args):
        """Submit a training job"""
        if not args.file:
            print("Error: --file required", file=sys.stderr)
            sys.exit(1)
        
        print(f"Submitting job from {args.file}...")
        self.run_kubectl(['apply', '-f', args.file])
        print("Job submitted successfully!")
    
    def delete_job(self, args):
        """Delete a training job"""
        if not args.name:
            print("Error: --name required", file=sys.stderr)
            sys.exit(1)
        
        namespace = args.namespace or 'default'
        print(f"Deleting job {args.name} from namespace {namespace}...")
        self.run_kubectl(['delete', 'pod', args.name, '-n', namespace])
        print("Job deleted successfully!")
    
    def cluster_status(self, args):
        """Show cluster status"""
        print("=== GPU Cluster Status ===\n")
        
        # Get nodes
        output = self.run_kubectl(['get', 'nodes', '-o', 'json'])
        nodes_data = json.loads(output)
        
        print(f"{'NODE':<30} {'TOTAL GPUs':<12} {'AVAILABLE':<12} {'STATUS':<10}")
        print("-" * 65)
        
        total_gpus = 0
        total_available = 0
        
        for node in nodes_data['items']:
            name = node['metadata']['name']
            capacity = int(node['status'].get('capacity', {}).get('nvidia.com/gpu', 0))
            allocatable = int(node['status'].get('allocatable', {}).get('nvidia.com/gpu', 0))
            
            status = "Ready"
            for condition in node['status']['conditions']:
                if condition['type'] == 'Ready':
                    status = condition['status']
                    break
            
            total_gpus += capacity
            total_available += allocatable
            
            print(f"{name:<30} {capacity:<12} {allocatable:<12} {status:<10}")
        
        print("-" * 65)
        print(f"{'TOTAL':<30} {total_gpus:<12} {total_available:<12}")
        
        # Show pending jobs
        print("\n=== Pending Jobs ===\n")
        output = self.run_kubectl([
            'get', 'pods', '--all-namespaces',
            '--field-selector', f'spec.schedulerName={self.scheduler_name},status.phase=Pending',
            '-o', 'json'
        ])
        
        pending_data = json.loads(output)
        if pending_data['items']:
            print(f"Found {len(pending_data['items'])} pending jobs:")
            for pod in pending_data['items']:
                print(f"  - {pod['metadata']['name']} (namespace: {pod['metadata']['namespace']})")
        else:
            print("No pending jobs")
    
    def scheduler_logs(self, args):
        """Show scheduler logs"""
        tail = args.tail or 50
        follow = ['-f'] if args.follow else []
        
        cmd = [
            'logs', '-n', 'scheduler-system',
            '-l', 'app=gpu-scheduler',
            '--tail', str(tail)
        ] + follow
        
        self.run_kubectl(cmd)
    
    def metrics(self, args):
        """Show scheduler metrics"""
        print("Fetching metrics from scheduler...")
        
        # Port-forward and fetch metrics
        try:
            result = subprocess.run(
                ['kubectl', 'get', 'svc', '-n', 'scheduler-system',
                 'gpu-scheduler-metrics', '-o', 'json'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("\nMetrics endpoint: kubectl port-forward -n scheduler-system svc/gpu-scheduler-metrics 8080:8080")
                print("Then access: http://localhost:8080/metrics")
            else:
                print("Scheduler metrics service not found")
        
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='GPU Scheduler CLI - Manage GPU training jobs'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List jobs
    list_parser = subparsers.add_parser('list', help='List all training jobs')
    list_parser.set_defaults(func=lambda cli, args: cli.list_jobs(args))
    
    # Submit job
    submit_parser = subparsers.add_parser('submit', help='Submit a training job')
    submit_parser.add_argument('--file', '-f', required=True, help='Job YAML file')
    submit_parser.set_defaults(func=lambda cli, args: cli.submit_job(args))
    
    # Delete job
    delete_parser = subparsers.add_parser('delete', help='Delete a training job')
    delete_parser.add_argument('--name', '-n', required=True, help='Job name')
    delete_parser.add_argument('--namespace', default='default', help='Namespace')
    delete_parser.set_defaults(func=lambda cli, args: cli.delete_job(args))
    
    # Cluster status
    status_parser = subparsers.add_parser('status', help='Show cluster status')
    status_parser.set_defaults(func=lambda cli, args: cli.cluster_status(args))
    
    # Scheduler logs
    logs_parser = subparsers.add_parser('logs', help='Show scheduler logs')
    logs_parser.add_argument('--tail', type=int, default=50, help='Number of lines')
    logs_parser.add_argument('--follow', '-f', action='store_true', help='Follow logs')
    logs_parser.set_defaults(func=lambda cli, args: cli.scheduler_logs(args))
    
    # Metrics
    metrics_parser = subparsers.add_parser('metrics', help='Show scheduler metrics')
    metrics_parser.set_defaults(func=lambda cli, args: cli.metrics(args))
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = GPUSchedulerCLI()
    args.func(cli, args)


if __name__ == '__main__':
    main()

