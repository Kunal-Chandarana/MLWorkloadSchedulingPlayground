# ML Workload Scheduling Playground

A comprehensive playground for learning and experimenting with machine learning workload scheduling on GPU clusters using Kubernetes.

## 🎯 What You'll Learn

- Custom Kubernetes scheduler implementation
- GPU resource management and allocation
- Different scheduling policies (FIFO, Priority, Fair-Share, Gang Scheduling)
- Multi-tenant cluster management
- Job preemption and checkpointing
- Performance metrics and monitoring
- Container orchestration for ML workloads

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Custom Scheduler (Python)                             │ │
│  │  - Watches for unscheduled pods                        │ │
│  │  - Applies scheduling policies                         │ │
│  │  - Binds pods to nodes                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   GPU Node 1 │  │   GPU Node 2 │  │   GPU Node 3 │      │
│  │   (2 GPUs)   │  │   (4 GPUs)   │  │   (2 GPUs)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  ML Training Jobs (PyTorch, TensorFlow, JAX)        │    │
│  │  - Single GPU jobs                                   │    │
│  │  - Multi-GPU distributed training                    │    │
│  │  - Batch inference workloads                         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

- **Docker Desktop** (or Docker Engine)
- **kubectl** (Kubernetes CLI)
- **kind** (Kubernetes in Docker) or **minikube**
- **Python 3.9+**
- **Helm** (optional, for monitoring stack)

## 🚀 Quick Start

### 1. Set Up the Cluster

```bash
# Create a local Kubernetes cluster with simulated GPU nodes
./scripts/setup-cluster.sh

# Verify cluster is running
kubectl get nodes
```

### 2. Deploy the Custom Scheduler

```bash
# Build and deploy the scheduler
./scripts/deploy-scheduler.sh

# Verify scheduler is running
kubectl get pods -n kube-system | grep gpu-scheduler
```

### 3. Submit Sample ML Jobs

```bash
# Submit a simple training job
kubectl apply -f examples/pytorch-training.yaml

# Submit a multi-GPU job
kubectl apply -f examples/distributed-training.yaml

# Check job status
./scripts/job-status.sh
```

### 4. Monitor and Visualize

```bash
# View scheduler logs
./scripts/view-logs.sh

# Access metrics dashboard
./scripts/start-dashboard.sh
```

## 📚 Project Structure

```
.
├── scheduler/                  # Custom scheduler implementation
│   ├── scheduler.py           # Main scheduler logic
│   ├── policies/              # Scheduling policies
│   │   ├── fifo.py
│   │   ├── priority.py
│   │   ├── fair_share.py
│   │   └── gang_scheduling.py
│   ├── metrics.py             # Metrics collection
│   └── config.py              # Configuration
├── ml-jobs/                   # Sample ML workload definitions
│   ├── pytorch/               # PyTorch examples
│   ├── tensorflow/            # TensorFlow examples
│   └── common/                # Shared utilities
├── k8s/                       # Kubernetes manifests
│   ├── cluster/               # Cluster setup
│   ├── scheduler/             # Scheduler deployment
│   └── monitoring/            # Prometheus, Grafana
├── scripts/                   # Automation scripts
├── cli/                       # CLI tools for job management
├── experiments/               # Example experiments
└── docs/                      # Detailed documentation
```

## 🎓 Learning Path

### Phase 1: Basics
1. Start the cluster and explore nodes
2. Submit single-GPU jobs
3. Understand FIFO scheduling
4. View scheduler logs and decisions

### Phase 2: Advanced Scheduling
1. Implement priority-based scheduling
2. Add fair-share policies
3. Handle gang scheduling (multi-GPU jobs)
4. Experiment with preemption

### Phase 3: Real-World Scenarios
1. Multi-tenant cluster simulation
2. Handle resource fragmentation
3. Optimize for different objectives (utilization, fairness, latency)
4. Compare scheduling policies

## 🧪 Example Experiments

Run pre-built experiments to see different scheduling behaviors:

```bash
# Compare FIFO vs Priority scheduling
python experiments/compare_policies.py

# Test gang scheduling with distributed training
python experiments/gang_scheduling.py

# Simulate multi-tenant workload
python experiments/multi_tenant.py

# Benchmark scheduler performance
python experiments/benchmark.py
```

## 📊 Key Metrics

The scheduler tracks and exposes:
- **GPU Utilization**: % of GPU time used
- **Job Wait Time**: Time from submission to start
- **Job Completion Time**: End-to-end duration
- **Queue Length**: Pending jobs
- **Fairness Metrics**: Resource distribution across users/teams
- **Fragmentation**: Wasted GPU resources

## 🔧 Configuration

Edit `scheduler/config.yaml` to customize:

```yaml
scheduler:
  policy: "fair_share"  # fifo, priority, fair_share, gang
  preemption_enabled: true
  checkpoint_interval: 300  # seconds
  
cluster:
  gpu_nodes: 3
  gpus_per_node: [2, 4, 2]
  
monitoring:
  prometheus_enabled: true
  metrics_port: 8080
```

## 🤝 Contributing

This is a learning playground! Feel free to:
- Add new scheduling policies
- Create more ML workload examples
- Improve monitoring and visualization
- Add documentation and tutorials

## 📖 Additional Resources

- [Kubernetes Scheduler Overview](docs/kubernetes-scheduler.md)
- [GPU Scheduling Patterns](docs/gpu-scheduling-patterns.md)
- [ML Workload Characteristics](docs/ml-workloads.md)
- [Troubleshooting Guide](docs/troubleshooting.md)

## 🏆 Challenges

Try these challenges to deepen your learning:
1. Implement a custom scoring function for node selection
2. Add support for GPU memory-aware scheduling
3. Build a web UI for job submission
4. Create a scheduler that learns from past jobs (ML-based)
5. Implement auto-scaling based on queue length

## 📝 License

MIT License - Feel free to use this for learning and experimentation!

---

**Happy Learning! 🚀🎓**
