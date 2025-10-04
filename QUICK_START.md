# 🚀 Quick Start - 5 Minutes to Your First Scheduled Job

## Prerequisites Check

```bash
# Verify you have these installed:
docker --version    # Should show Docker version
kind --version      # Should show kind version  
kubectl version     # Should show kubectl version
```

Not installed? See [Installation Guide](docs/quickstart.md#prerequisites)

## Step 1: Setup (2 minutes)

```bash
cd MLWorkloadSchedulingPlayground

# Create cluster with simulated GPUs
make setup
```

**Expected output:**
```
✓ Creating Kubernetes cluster...
✓ Deploying GPU device plugin...
✓ Cluster ready with 3 GPU nodes (2, 4, 2 GPUs)
```

## Step 2: Deploy Scheduler (2 minutes)

```bash
# Build and deploy the custom scheduler
make deploy
```

**Expected output:**
```
✓ Building scheduler image...
✓ Loading into cluster...
✓ Scheduler deployed successfully!
```

## Step 3: Submit Your First Job (30 seconds)

```bash
# Submit a PyTorch training job
make submit-test
```

**Expected output:**
```
pod/pytorch-training-simple created
```

## Step 4: Watch It Work! (30 seconds)

Open two terminals:

**Terminal 1 - Scheduler Logs:**
```bash
make logs
```

You'll see:
```
[2024-10-04 10:30:45] New pod to schedule: default/pytorch-training-simple
[2024-10-04 10:30:45] ✓ Scheduled pod default/pytorch-training-simple 
                         to node gpu-node-1 (GPUs: 1)
```

**Terminal 2 - Job Status:**
```bash
make status
```

You'll see:
```
NAME                        STATUS    NODE         GPUs
pytorch-training-simple     Running   gpu-node-1   1
```

## 🎉 Success!

You just:
1. ✅ Created a Kubernetes cluster with simulated GPUs
2. ✅ Deployed a custom scheduler
3. ✅ Submitted an ML training job
4. ✅ Watched the scheduler assign it to a GPU node

## What Just Happened?

```
┌──────────────────┐
│  You submitted   │
│  pytorch-job     │
└────────┬─────────┘
         │
         ↓
┌─────────────────────────────────┐
│  Custom GPU Scheduler           │
│  1. Found unscheduled pod       │
│  2. Checked available GPU nodes │
│  3. Selected best node (FIFO)   │
│  4. Bound pod to node           │
└────────┬────────────────────────┘
         │
         ↓
┌──────────────────────┐
│  Pod Running on      │
│  gpu-node-1          │
│  Using 1 GPU         │
└──────────────────────┘
```

## Next Steps

### Try Different Scheduling Policies

**Switch to Priority Scheduling:**
```bash
kubectl edit configmap scheduler-config -n scheduler-system
# Change: policy: "priority"
kubectl rollout restart deployment/gpu-scheduler -n scheduler-system

# Submit jobs with different priorities
kubectl apply -f examples/multi-job-batch.yaml
make logs  # Watch high-priority jobs get scheduled first
```

**Switch to Fair-Share:**
```bash
# Edit config: policy: "fair_share"
kubectl apply -f examples/multi-job-batch.yaml
make logs  # Watch resources distributed across teams
```

### Submit Multiple Jobs

```bash
# Submit 4 jobs with different priorities
kubectl apply -f examples/multi-job-batch.yaml

# Watch the scheduling decisions
make logs
```

### Run Distributed Training

```bash
# Submit a multi-GPU distributed job (gang scheduling)
kubectl apply -f examples/distributed-training.yaml

# Watch all 3 pods get scheduled together
make logs
```

### Run Experiments

```bash
# Compare all scheduling policies
python experiments/compare_policies.py

# Test gang scheduling
python experiments/gang_scheduling.py

# Multi-tenant simulation
python experiments/multi_tenant.py
```

### Use the CLI

```bash
# Show cluster status
./cli/gpusched.py status

# List all jobs
./cli/gpusched.py list

# Submit a job
./cli/gpusched.py submit --file examples/pytorch-training.yaml

# View logs
./cli/gpusched.py logs --follow
```

## Common Commands

```bash
# View all jobs
kubectl get pods --all-namespaces -o wide

# Delete a specific job
kubectl delete pod pytorch-training-simple

# Delete all jobs
make delete-jobs

# Rebuild scheduler after code changes
make rebuild

# Full cleanup
make clean
```

## Troubleshooting

**Scheduler not starting?**
```bash
kubectl get pods -n scheduler-system
kubectl logs -n scheduler-system -l app=gpu-scheduler
```

**Jobs stuck in Pending?**
```bash
make status  # Check GPU availability
make logs    # Check scheduler decisions
kubectl describe pod <pod-name>  # Check pod details
```

**Want to start fresh?**
```bash
make clean   # Delete everything
make setup   # Recreate cluster
make deploy  # Redeploy scheduler
```

## Learning Path

Now that you have it running:

1. **Read the concepts** → `docs/gpu-scheduling-patterns.md`
2. **Understand the code** → Start with `scheduler/scheduler.py`
3. **Try experiments** → `experiments/README.md`
4. **Build your own policy** → `scheduler/policies/`
5. **Complete guide** → `GETTING_STARTED.md`

## Makefile Cheat Sheet

```bash
make help          # Show all commands
make setup         # Create cluster
make deploy        # Deploy scheduler
make status        # Show status
make logs          # Stream logs
make metrics       # Access metrics
make submit-test   # Submit test job
make submit-all    # Submit all examples
make experiments   # Run experiments
make rebuild       # Rebuild scheduler
make delete-jobs   # Delete all jobs
make clean         # Full cleanup
make reset         # Clean + setup + deploy
```

## What's Next?

Choose your adventure:

### 🎓 **Learn**: 
Read `GETTING_STARTED.md` for a structured learning path

### 🔬 **Experiment**: 
Run the experiments in `experiments/`

### 🛠️ **Build**: 
Create your own scheduling policy in `scheduler/policies/`

### 📚 **Deep Dive**: 
Study the detailed docs in `docs/`

---

**You're all set!** Have fun exploring GPU workload scheduling! 🎉

Questions? Check `PROJECT_SUMMARY.md` for the complete overview.

