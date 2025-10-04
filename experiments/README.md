# Scheduling Experiments

This directory contains pre-built experiments to explore different scheduling behaviors.

## Available Experiments

### 1. Policy Comparison (`compare_policies.py`)

Compares FIFO, Priority, and Fair-Share scheduling policies.

```bash
python experiments/compare_policies.py
```

**What it does:**
- Submits the same workload under different policies
- Measures scheduling latency and node distribution
- Shows how each policy handles resource allocation

**Learn:**
- How FIFO schedules in arrival order
- How priority scheduling prioritizes high-priority jobs
- How fair-share distributes resources across teams

### 2. Gang Scheduling (`gang_scheduling.py`)

Tests all-or-nothing scheduling for distributed training.

```bash
python experiments/gang_scheduling.py
```

**What it does:**
- Submits a distributed training job requiring 3 pods with 2 GPUs each
- Demonstrates that all pods are scheduled together or none at all
- Shows how gang scheduling prevents resource deadlocks

**Learn:**
- Why gang scheduling is critical for distributed training
- How to prevent resource fragmentation
- Timeout handling for unfulfillable requests

### 3. Multi-Tenant Simulation (`multi_tenant.py`)

Simulates multiple teams competing for GPU resources.

```bash
python experiments/multi_tenant.py
```

**What it does:**
- Submits 15+ jobs from 3 different teams
- Monitors resource allocation fairness over time
- Analyzes final GPU distribution across teams

**Learn:**
- How fair-share weights affect resource allocation
- Resource starvation prevention
- Multi-tenancy challenges in GPU clusters

## Running Experiments

### Prerequisites

1. Cluster must be running:
   ```bash
   ./scripts/setup-cluster.sh
   ```

2. Scheduler must be deployed:
   ```bash
   ./scripts/deploy-scheduler.sh
   ```

3. Python 3.9+ with no additional dependencies

### Experiment Workflow

Each experiment follows this pattern:

1. **Setup**: Configure scheduler for specific policy
2. **Submit**: Create workload (pods/jobs)
3. **Monitor**: Track scheduling decisions
4. **Analyze**: Collect and display metrics
5. **Cleanup**: Remove all test resources

### Viewing Scheduler Logs

While running experiments, view scheduler logs in another terminal:

```bash
./scripts/view-logs.sh
```

## Customizing Experiments

### Modify Workload

Edit experiment scripts to change:
- Number of jobs
- GPU requirements per job
- Job duration
- Team distribution

### Test Different Policies

Manually switch policies:

```bash
kubectl edit configmap scheduler-config -n scheduler-system
# Change policy: "fifo" to "priority", "fair_share", or "gang"

kubectl rollout restart deployment/gpu-scheduler -n scheduler-system
```

## Understanding Results

### Key Metrics

- **Scheduling Latency**: Time from job submission to placement
- **GPU Utilization**: % of GPU capacity used
- **Fairness**: Resource distribution across users/teams
- **Queue Length**: Number of pending jobs
- **Fragmentation**: Wasted GPU resources

### Good Scheduling Characteristics

✓ Low latency for high-priority jobs  
✓ High GPU utilization (>80%)  
✓ Fair distribution (within configured weights)  
✓ No starvation (all jobs eventually run)  
✓ Minimal fragmentation  

## Troubleshooting

### "No GPU resources available"

- Check node GPU capacity: `kubectl get nodes -o custom-columns=NAME:.metadata.name,GPUs:.status.capacity.'nvidia\.com/gpu'`
- Reduce GPU requests in experiments
- Add more nodes to kind config

### Pods stuck in Pending

- Check scheduler logs: `./scripts/view-logs.sh`
- Verify scheduler is running: `kubectl get pods -n scheduler-system`
- Check for resource constraints: `./cli/gpusched.py status`

### Experiments timeout

- Increase monitoring duration in script
- Check if scheduler crashed: `kubectl get pods -n scheduler-system`
- Verify Docker images loaded: `kind load docker-image --help`

## Next Steps

After running these experiments:

1. Create your own scheduling policy in `scheduler/policies/`
2. Implement custom scoring functions
3. Add preemption logic
4. Integrate with real GPU workloads
5. Build a web UI for visualization

Happy experimenting! 🚀

