# GPU Scheduling Patterns

Understanding common patterns and challenges in GPU workload scheduling.

## Why GPU Scheduling is Hard

Unlike CPU scheduling, GPU scheduling faces unique challenges:

### 1. **Discrete Resource Units**
- CPUs can be shared (fractional cores)
- GPUs are typically allocated whole (1, 2, 4, 8 GPUs)
- Creates fragmentation and bin-packing challenges

### 2. **High Cost**
- GPUs are expensive ($10k - $30k each)
- Idle GPU time is wasted money
- Maximizing utilization is critical

### 3. **Varied Workload Patterns**
- Training jobs: Long-running, predictable
- Inference: Short, bursty, latency-sensitive
- Hyperparameter tuning: Many short jobs
- Distributed training: Gang scheduling required

### 4. **Multi-Tenancy**
- Multiple teams sharing cluster
- Fair resource distribution needed
- Priority and quotas required

## Common Scheduling Patterns

### Pattern 1: FIFO (First-In-First-Out)

**When to use:**
- Single user/team
- Similar job priorities
- Simple, predictable behavior

**Pros:**
- ✓ Simple to implement
- ✓ No starvation (eventually runs)
- ✓ Predictable wait times

**Cons:**
- ✗ No priority support
- ✗ Large jobs block small ones
- ✗ Poor for mixed workloads

**Implementation:**
```python
def select_node(pod, nodes):
    # Find node with most available GPUs
    return max(nodes, key=lambda n: n.available_gpus)
```

### Pattern 2: Priority Scheduling

**When to use:**
- Production workloads mix with research
- SLA requirements for certain jobs
- Emergency job submission needed

**Pros:**
- ✓ High-priority jobs run first
- ✓ Supports business requirements
- ✓ Can preempt low-priority work

**Cons:**
- ✗ Low-priority jobs can starve
- ✗ Requires priority assignment policy
- ✗ Preemption complexity

**Implementation:**
```python
def select_node(pod, nodes):
    priority = get_priority(pod)
    
    # Try to find available resources
    for node in sorted(nodes, key=available_gpus, reverse=True):
        if node.can_fit(pod):
            return node
    
    # If high priority, try preemption
    if priority > threshold and preemption_enabled:
        return find_preemptible_node(pod, nodes)
    
    return None
```

### Pattern 3: Fair-Share Scheduling

**When to use:**
- Multi-tenant clusters
- Multiple teams with quotas
- Long-term fairness goals

**Pros:**
- ✓ Prevents resource hogging
- ✓ Configurable weights per user/team
- ✓ Good for shared clusters

**Cons:**
- ✗ Complex fairness calculations
- ✗ May reduce overall utilization
- ✗ Needs usage tracking

**Implementation:**
```python
def select_node(pod, nodes):
    user = get_user(pod)
    current_usage = get_user_usage(user)
    fair_share = calculate_fair_share(user)
    
    # Prioritize under-allocated users
    if current_usage < fair_share:
        return select_best_node(pod, nodes)
    else:
        # Throttle over-allocated users
        return select_node_or_wait(pod, nodes)
```

### Pattern 4: Gang Scheduling

**When to use:**
- Distributed training (MPI, PyTorch DDP)
- Jobs requiring multiple GPUs across nodes
- All-or-nothing resource requirements

**Pros:**
- ✓ Prevents partial scheduling
- ✓ No deadlocks from partial allocation
- ✓ Essential for distributed training

**Cons:**
- ✗ Harder to achieve high utilization
- ✗ Increases scheduling latency
- ✗ Can waste resources waiting

**Implementation:**
```python
def schedule_gang(gang_pods, nodes):
    total_gpus_needed = sum(p.gpu_count for p in gang_pods)
    
    if total_available_gpus(nodes) < total_gpus_needed:
        return None  # Wait for resources
    
    # Try to place all pods
    placement = {}
    for pod in gang_pods:
        node = find_fit(pod, nodes)
        if not node:
            return None  # Can't fit all, don't schedule any
        placement[pod] = node
        reserve_resources(node, pod)
    
    return placement
```

## Advanced Patterns

### Backfilling

Fill gaps with small jobs while waiting for large jobs:

```python
def schedule_with_backfill(queue, nodes):
    # Sort by priority/arrival
    primary_job = queue[0]
    
    if not can_schedule(primary_job, nodes):
        # Try to fit smaller jobs that won't delay primary
        for job in queue[1:]:
            if can_fit_without_delaying(job, primary_job, nodes):
                schedule_job(job)
```

### Bin Packing

Minimize fragmentation by packing jobs efficiently:

```python
def select_node_best_fit(pod, nodes):
    gpu_needed = pod.gpu_count
    
    # Find node with least waste
    best_node = None
    min_waste = float('inf')
    
    for node in nodes:
        if node.available_gpus >= gpu_needed:
            waste = node.available_gpus - gpu_needed
            if waste < min_waste:
                min_waste = waste
                best_node = node
    
    return best_node
```

### Time Slicing

Share GPUs among multiple jobs (requires GPU support):

```python
# Allocate GPU time slices
def schedule_time_sliced(jobs, gpus):
    for gpu in gpus:
        time_per_job = 1.0 / len(jobs)
        for job in jobs:
            assign_time_slice(job, gpu, time_per_job)
```

### Topology-Aware Scheduling

Consider GPU interconnects (NVLink, PCIe topology):

```python
def select_nodes_topology_aware(pods, nodes):
    if requires_high_bandwidth(pods):
        # Prefer nodes with NVLink
        nodes = filter(lambda n: n.has_nvlink, nodes)
    
    # Minimize inter-node communication
    return select_colocated_nodes(pods, nodes)
```

## Scheduling Objectives

Different objectives lead to different algorithms:

### 1. Maximize Utilization
- Pack jobs tightly
- Minimize fragmentation
- Use backfilling

### 2. Minimize Wait Time
- FIFO or priority
- Fast placement decisions
- Preemption for high-priority

### 3. Maximize Fairness
- Fair-share algorithms
- Track long-term usage
- Adjust allocations dynamically

### 4. Minimize Completion Time
- Shortest Job First (SJF)
- Requires job duration estimates
- Risk of starvation for long jobs

## Real-World Considerations

### Job Characteristics

Different ML workloads need different handling:

| Workload Type | Duration | GPU Count | Priority | Pattern |
|--------------|----------|-----------|----------|---------|
| Training | Hours-Days | 1-8 | Medium | Gang |
| Hyperparameter Tuning | Minutes-Hours | 1-2 | Low | FIFO |
| Inference | Milliseconds | 1 | High | Priority |
| Research | Variable | 1-4 | Medium | Fair-Share |

### Cluster Sizing

```
Utilization = (GPU hours used) / (GPU hours available)

Target: 70-85% utilization
- Below 70%: Overprovisioned
- Above 85%: Long wait times
```

### Queue Management

```python
class JobQueue:
    def __init__(self):
        self.high_priority = []
        self.medium_priority = []
        self.low_priority = []
    
    def get_next_job(self):
        if self.high_priority:
            return self.high_priority.pop(0)
        elif self.medium_priority:
            return self.medium_priority.pop(0)
        else:
            return self.low_priority.pop(0)
```

## Further Reading

- [Kubernetes Scheduler](kubernetes-scheduler.md)
- [ML Workload Characteristics](ml-workloads.md)
- Academic: "Gandiva: Introspective Cluster Scheduling for Deep Learning"
- Academic: "Tiresias: A GPU Cluster Manager for Distributed Deep Learning"

