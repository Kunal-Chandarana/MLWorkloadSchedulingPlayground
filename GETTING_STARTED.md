# Getting Started with GPU Workload Scheduling

Welcome! This guide will help you understand the playground and start learning about ML workload scheduling.

## 🎯 What You'll Learn

By working through this playground, you'll understand:

1. **How Kubernetes schedulers work** - The core concepts and architecture
2. **GPU scheduling challenges** - Why GPUs are different from CPUs
3. **Scheduling algorithms** - FIFO, Priority, Fair-Share, Gang Scheduling
4. **Real-world patterns** - How companies like Google, Meta, and OpenAI schedule ML workloads
5. **Hands-on implementation** - Build and test your own scheduling policies

## 📚 Learning Path

### Phase 1: Setup & Basics (30 minutes)

**Goal:** Get everything running and understand the basic flow.

1. **Setup the environment**
   ```bash
   ./scripts/setup-cluster.sh
   ./scripts/deploy-scheduler.sh
   ```

2. **Submit your first job**
   ```bash
   kubectl apply -f examples/pytorch-training.yaml
   ```

3. **Watch it run**
   ```bash
   # Terminal 1: Scheduler logs
   ./scripts/view-logs.sh
   
   # Terminal 2: Job status
   watch -n 2 ./scripts/job-status.sh
   ```

4. **Questions to explore:**
   - How does the scheduler find the pod?
   - What criteria does it use to select a node?
   - How long does scheduling take?

**Resources:**
- Read: [Quick Start Guide](docs/quickstart.md)
- Code: Look at `scheduler/scheduler.py` - the main loop

### Phase 2: Scheduling Policies (1-2 hours)

**Goal:** Understand different scheduling algorithms.

1. **Try FIFO scheduling**
   ```bash
   # Default policy - submit multiple jobs
   kubectl apply -f examples/multi-job-batch.yaml
   ./scripts/view-logs.sh
   ```
   
   Observe: Jobs are scheduled in order of arrival.

2. **Switch to Priority scheduling**
   ```bash
   kubectl edit configmap scheduler-config -n scheduler-system
   # Change: policy: "priority"
   kubectl rollout restart deployment/gpu-scheduler -n scheduler-system
   
   # Submit the same jobs
   kubectl apply -f examples/multi-job-batch.yaml
   ```
   
   Observe: High-priority jobs are scheduled first.

3. **Try Fair-Share**
   ```bash
   # Edit config: policy: "fair_share"
   # Submit jobs from different teams
   kubectl apply -f examples/multi-job-batch.yaml
   ```
   
   Observe: Resources are distributed across teams.

4. **Questions to explore:**
   - Which policy minimizes wait time?
   - Which maximizes fairness?
   - What are the trade-offs?

**Resources:**
- Read: [GPU Scheduling Patterns](docs/gpu-scheduling-patterns.md)
- Code: Look at files in `scheduler/policies/`

### Phase 3: Advanced Concepts (2-3 hours)

**Goal:** Handle complex scheduling scenarios.

1. **Gang Scheduling Experiment**
   ```bash
   python experiments/gang_scheduling.py
   ```
   
   This shows all-or-nothing scheduling for distributed training.
   
   Questions:
   - Why do all pods need to be scheduled together?
   - What happens if resources are insufficient?
   - How does timeout work?

2. **Multi-Tenant Simulation**
   ```bash
   python experiments/multi_tenant.py
   ```
   
   Simulates multiple teams competing for resources.
   
   Questions:
   - How are resources distributed?
   - Can you spot any unfairness?
   - What happens when one team submits many jobs?

3. **Policy Comparison**
   ```bash
   python experiments/compare_policies.py
   ```
   
   Compares different policies on the same workload.

**Resources:**
- Read: [Kubernetes Scheduler Deep Dive](docs/kubernetes-scheduler.md)
- Code: `scheduler/policies/gang_scheduling.py`

### Phase 4: Build Your Own (3-5 hours)

**Goal:** Implement a custom scheduling policy.

1. **Create a new policy file**
   ```bash
   cp scheduler/policies/fifo.py scheduler/policies/custom.py
   ```

2. **Implement your logic**
   
   Example ideas:
   - **GPU-aware**: Consider GPU memory, not just count
   - **Locality-aware**: Prefer nodes with fast interconnects
   - **Cost-optimized**: Prefer cheaper GPU types
   - **ML-based**: Use a trained model to predict best placement

3. **Register your policy**
   
   Edit `scheduler/policies/__init__.py`:
   ```python
   from .custom import CustomPolicy
   
   __all__ = [..., 'CustomPolicy']
   ```
   
   Edit `scheduler/scheduler.py`:
   ```python
   policies = {
       'custom': CustomPolicy,
       ...
   }
   ```

4. **Test it**
   ```bash
   # Rebuild scheduler
   docker build -t gpu-scheduler:latest ./scheduler/
   kind load docker-image gpu-scheduler:latest --name gpu-scheduler-cluster
   
   # Update config
   kubectl edit configmap scheduler-config -n scheduler-system
   # Set: policy: "custom"
   
   kubectl rollout restart deployment/gpu-scheduler -n scheduler-system
   
   # Submit test workload
   kubectl apply -f examples/multi-job-batch.yaml
   ```

**Resources:**
- Code: `scheduler/policies/base.py` - Base class to extend
- Example: All files in `scheduler/policies/`

## 🛠️ Development Workflow

### Making Changes

1. **Edit code locally**
   ```bash
   vim scheduler/scheduler.py
   ```

2. **Rebuild Docker image**
   ```bash
   docker build -t gpu-scheduler:latest ./scheduler/
   ```

3. **Load into cluster**
   ```bash
   kind load docker-image gpu-scheduler:latest --name gpu-scheduler-cluster
   ```

4. **Restart scheduler**
   ```bash
   kubectl rollout restart deployment/gpu-scheduler -n scheduler-system
   ```

5. **Test**
   ```bash
   ./scripts/view-logs.sh
   ```

### Debugging Tips

**Scheduler not starting?**
```bash
kubectl get pods -n scheduler-system
kubectl logs -n scheduler-system -l app=gpu-scheduler
kubectl describe pod -n scheduler-system -l app=gpu-scheduler
```

**Jobs stuck in Pending?**
```bash
kubectl describe pod <pod-name>
./cli/gpusched.py status
./scripts/view-logs.sh
```

**Want to see detailed decisions?**

Add logging in your policy:
```python
import logging
logger = logging.getLogger(__name__)

def select_node(self, pod, nodes, scheduler):
    logger.info(f"Selecting node for {pod.metadata.name}")
    logger.debug(f"Available nodes: {[n.metadata.name for n in nodes]}")
    # ... your logic
    logger.info(f"Selected: {selected_node.metadata.name}")
    return selected_node
```

## 🎓 Deep Dive Topics

Once comfortable with basics, explore these advanced topics:

### 1. Preemption
- Implement priority-based preemption
- Add checkpointing for interrupted jobs
- Handle graceful termination

### 2. Bin Packing
- Minimize GPU fragmentation
- Implement best-fit, worst-fit algorithms
- Compare utilization vs scheduling speed

### 3. Predictive Scheduling
- Estimate job duration from historical data
- Use predictions to optimize schedules
- Handle inaccurate predictions

### 4. Multi-Resource Scheduling
- Consider CPU, memory, GPU together
- Implement dominant resource fairness (DRF)
- Handle heterogeneous resources

### 5. Autoscaling
- Scale cluster based on queue length
- Add/remove nodes dynamically
- Cost-aware scaling decisions

## 📖 Recommended Reading

### Academic Papers
- **Borg** - Google's cluster manager (OSDI 2015)
- **Gandiva** - Introspective cluster scheduling for DL (OSDI 2018)
- **Tiresias** - GPU cluster manager for DL (NSDI 2019)
- **Pollux** - Adaptive scheduling for DL training (OSDI 2021)

### Blog Posts
- [How Meta Schedules Billions of Training Jobs](https://engineering.fb.com/2023/03/20/production-engineering/training-infrastructure-pytorch-meta/)
- [Google Cloud TPU Scheduling](https://cloud.google.com/blog/products/ai-machine-learning/tpu-architecture-and-software)

### Books
- "Site Reliability Engineering" - Chapter on Resource Management
- "Kubernetes Patterns" - Scheduling chapter

## 🤝 Next Steps

### Extend the Playground

Ideas for enhancement:
1. Add web UI for visualization
2. Implement metrics dashboard with Grafana
3. Add support for more ML frameworks (JAX, MXNet)
4. Simulate GPU memory constraints
5. Add cost tracking and optimization
6. Implement job preemption with checkpointing
7. Add support for multi-GPU node topologies
8. Create a job submission portal

### Real-World Integration

Apply what you learned:
1. Deploy on a real GPU cluster (on-prem or cloud)
2. Integrate with MLflow for experiment tracking
3. Add job queueing with Redis
4. Implement authentication and multi-tenancy
5. Build production monitoring and alerting

### Share Your Learning

Contribute back:
1. Implement a new scheduling policy
2. Add more experiments
3. Improve documentation
4. Create tutorial videos
5. Write blog posts about your findings

## 💡 Project Ideas

Use this playground as a foundation for projects:

1. **Benchmark Suite**: Compare schedulers on realistic ML workloads
2. **ML-Based Scheduler**: Train a model to learn optimal scheduling
3. **Cost Optimizer**: Minimize cloud GPU costs while meeting SLAs
4. **Simulator**: Large-scale scheduling simulation tool
5. **Scheduler Visualizer**: Real-time visualization of scheduling decisions

## 🚀 You're Ready!

You now have a comprehensive playground for learning GPU workload scheduling. Start with Phase 1, experiment, break things, and most importantly - have fun learning!

Questions? Check the docs in the `docs/` directory or examine the code - it's all well-commented.

Happy scheduling! 🎉

