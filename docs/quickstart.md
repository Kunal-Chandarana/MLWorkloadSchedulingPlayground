# Quick Start Guide

Get up and running with the GPU Scheduler Playground in 10 minutes!

## Prerequisites

Install these tools before starting:

### macOS

```bash
# Install Docker Desktop from docker.com, or:
brew install --cask docker

# Install Kubernetes tools
brew install kind kubectl

# Verify installations
docker --version
kind --version
kubectl version --client
```

### Linux

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

## 5-Minute Setup

### Step 1: Create the Cluster

```bash
cd MLWorkloadSchedulingPlayground
chmod +x scripts/*.sh
./scripts/setup-cluster.sh
```

Expected output:
```
Creating Kubernetes cluster with kind...
✓ Cluster created successfully
✓ GPU device plugin deployed
✓ 3 nodes with 2, 4, 2 GPUs respectively
```

### Step 2: Deploy the Scheduler

```bash
./scripts/deploy-scheduler.sh
```

Expected output:
```
Building scheduler Docker image...
Loading images into cluster...
✓ Scheduler deployed successfully
```

### Step 3: Submit Your First Job

```bash
kubectl apply -f examples/pytorch-training.yaml
```

### Step 4: Watch It Run

```bash
# Terminal 1: Watch scheduler logs
./scripts/view-logs.sh

# Terminal 2: Check job status
./scripts/job-status.sh
```

## Your First Experiment

Try the multi-job batch to see scheduling in action:

```bash
# Submit multiple jobs
kubectl apply -f examples/multi-job-batch.yaml

# Watch scheduler assign them to nodes
./scripts/view-logs.sh
```

You'll see output like:
```
✓ Scheduled pod default/job-high-priority-1 to node gpu-node-1 (GPUs: 1)
✓ Scheduled pod default/job-medium-priority-1 to node gpu-node-2 (GPUs: 1)
✓ Scheduled pod default/job-low-priority-1 to node gpu-node-3 (GPUs: 1)
```

## Using the CLI Tool

```bash
# Make CLI executable
chmod +x cli/gpusched.py

# List all jobs
./cli/gpusched.py list

# Check cluster status
./cli/gpusched.py status

# Submit a job
./cli/gpusched.py submit --file examples/pytorch-training.yaml

# View logs
./cli/gpusched.py logs --follow
```

## Next Steps

### Try Different Scheduling Policies

Edit the scheduler config:

```bash
kubectl edit configmap scheduler-config -n scheduler-system
```

Change `policy: "fifo"` to:
- `priority` - High priority jobs first
- `fair_share` - Fair distribution across teams
- `gang` - All-or-nothing for distributed jobs

Then restart:

```bash
kubectl rollout restart deployment/gpu-scheduler -n scheduler-system
```

### Run Experiments

```bash
# Compare scheduling policies
python experiments/compare_policies.py

# Test gang scheduling
python experiments/gang_scheduling.py

# Multi-tenant simulation
python experiments/multi_tenant.py
```

### Monitor Metrics

```bash
# Start metrics server
./scripts/start-dashboard.sh

# In another terminal, fetch metrics
curl http://localhost:8080/metrics
```

## Common Commands

```bash
# View all jobs
kubectl get pods --all-namespaces -o wide

# Delete a job
kubectl delete pod <pod-name>

# Delete all jobs
kubectl delete pods --selector schedulerName=gpu-scheduler

# Restart scheduler
kubectl rollout restart deployment/gpu-scheduler -n scheduler-system

# View GPU allocation
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPUs:.status.capacity.'nvidia\.com/gpu'
```

## Troubleshooting

### Scheduler Not Starting

```bash
# Check scheduler pod
kubectl get pods -n scheduler-system

# View logs
kubectl logs -n scheduler-system -l app=gpu-scheduler

# Common fix: Rebuild and reload image
docker build -t gpu-scheduler:latest ./scheduler/
kind load docker-image gpu-scheduler:latest --name gpu-scheduler-cluster
kubectl rollout restart deployment/gpu-scheduler -n scheduler-system
```

### Jobs Stuck in Pending

```bash
# Check GPU availability
./cli/gpusched.py status

# View scheduler decision
./scripts/view-logs.sh

# Check job requirements
kubectl describe pod <pod-name>
```

### Cluster Issues

```bash
# Restart cluster
kind delete cluster --name gpu-scheduler-cluster
./scripts/setup-cluster.sh
./scripts/deploy-scheduler.sh
```

## Cleanup

When done experimenting:

```bash
./scripts/cleanup.sh
```

This deletes the cluster and all Docker images.

## What's Next?

- Read [GPU Scheduling Patterns](gpu-scheduling-patterns.md)
- Learn about [Kubernetes Scheduler](kubernetes-scheduler.md)
- Explore [ML Workload Characteristics](ml-workloads.md)
- Build your own scheduling policy!

Happy learning! 🚀

