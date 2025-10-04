# Kubernetes Scheduler Deep Dive

Understanding how Kubernetes scheduling works and how to build custom schedulers.

## Kubernetes Scheduling Basics

### The Default Scheduler

Kubernetes comes with a default scheduler (`kube-scheduler`) that:

1. **Watches** for unscheduled pods
2. **Filters** nodes that can run the pod
3. **Scores** filtered nodes
4. **Binds** pod to highest-scoring node

### Scheduling Cycle

```
┌─────────────────────────────────────────────────────┐
│                  Scheduling Queue                    │
│  [Pod1] [Pod2] [Pod3] ... (unscheduled pods)       │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│              Filtering (Predicates)                  │
│  • Node has enough CPU/Memory/GPU?                  │
│  • Pod fits with taints/tolerations?                │
│  • Node selector matches?                           │
│  • Port conflicts?                                  │
└─────────────────────────────────────────────────────┘
                        ↓
              [Node1] [Node3] [Node5]
                        ↓
┌─────────────────────────────────────────────────────┐
│                Scoring (Priorities)                  │
│  • Balance resource usage                           │
│  • Spread pods across zones                         │
│  • Prefer certain node types                        │
│  • Custom scoring functions                         │
└─────────────────────────────────────────────────────┘
                        ↓
                   Node3 (score: 95)
                        ↓
┌─────────────────────────────────────────────────────┐
│                    Binding                          │
│  Create binding object: Pod → Node                  │
└─────────────────────────────────────────────────────┘
```

## Custom Scheduler Implementation

### Approach 1: Standalone Scheduler

Our playground uses this approach - a completely separate scheduler:

**Pros:**
- ✓ Full control over logic
- ✓ Can use any language
- ✓ Independent of Kubernetes versions
- ✓ Easier to debug and test

**Cons:**
- ✗ More code to write
- ✗ Need to reimplement basics
- ✗ Maintain cluster state manually

**How it works:**

```python
from kubernetes import client, watch

def main():
    v1 = client.CoreV1Api()
    w = watch.Watch()
    
    # Watch for pods using our scheduler
    for event in w.stream(
        v1.list_pod_for_all_namespaces,
        field_selector="spec.schedulerName=gpu-scheduler"
    ):
        pod = event['object']
        
        if pod.spec.node_name:
            continue  # Already scheduled
        
        # Custom scheduling logic
        node = select_best_node(pod)
        
        if node:
            bind_pod_to_node(pod, node)
```

### Approach 2: Scheduler Framework

Extend kube-scheduler with plugins (Kubernetes 1.19+):

**Pros:**
- ✓ Reuse default scheduler infrastructure
- ✓ Only customize what you need
- ✓ Better integration with K8s

**Cons:**
- ✗ Must use Go
- ✗ Tied to K8s versions
- ✗ More complex setup

**Plugin points:**

```go
type Plugin interface {
    Name() string
}

type FilterPlugin interface {
    Filter(ctx context.Context, state *CycleState, 
           pod *v1.Pod, nodeInfo *NodeInfo) *Status
}

type ScorePlugin interface {
    Score(ctx context.Context, state *CycleState,
          pod *v1.Pod, nodeName string) (int64, *Status)
}
```

## Key Concepts

### 1. Binding

Creating the Pod ↔ Node association:

```python
def bind_pod_to_node(pod, node):
    binding = client.V1Binding(
        api_version="v1",
        kind="Binding",
        metadata=client.V1ObjectMeta(
            name=pod.metadata.name,
            namespace=pod.metadata.namespace
        ),
        target=client.V1ObjectReference(
            kind="Node",
            name=node.metadata.name
        )
    )
    
    v1.create_namespaced_binding(
        namespace=pod.metadata.namespace,
        body=binding
    )
```

### 2. Resource Requests

Pods specify resource requirements:

```yaml
resources:
  requests:
    cpu: "2"
    memory: "4Gi"
    nvidia.com/gpu: "1"
  limits:
    cpu: "4"
    memory: "8Gi"
    nvidia.com/gpu: "1"
```

Scheduler must check:
```python
def can_fit(pod, node):
    for resource in ['cpu', 'memory', 'nvidia.com/gpu']:
        requested = pod.resources.requests.get(resource, 0)
        available = node.status.allocatable.get(resource, 0)
        
        if requested > available:
            return False
    
    return True
```

### 3. Node Selection

Multiple strategies:

```python
# Strategy 1: First Fit
def first_fit(pod, nodes):
    for node in nodes:
        if can_fit(pod, node):
            return node
    return None

# Strategy 2: Best Fit (minimize waste)
def best_fit(pod, nodes):
    best = None
    min_waste = float('inf')
    
    for node in nodes:
        if can_fit(pod, node):
            waste = calculate_waste(pod, node)
            if waste < min_waste:
                min_waste = waste
                best = node
    
    return best

# Strategy 3: Spread (balance across nodes)
def spread(pod, nodes):
    return min(nodes, key=lambda n: n.pod_count)
```

### 4. Pod Affinity/Anti-Affinity

Schedule pods near or away from other pods:

```yaml
affinity:
  podAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchLabels:
          app: cache
      topologyKey: kubernetes.io/hostname
```

Implementation:
```python
def check_affinity(pod, node, all_pods):
    for rule in pod.affinity.pod_affinity.rules:
        matching_pods = find_pods_with_labels(
            rule.label_selector, all_pods
        )
        
        if not any(p.node == node for p in matching_pods):
            return False  # Affinity not satisfied
    
    return True
```

## Advanced Techniques

### Scheduler Extenders

Call external HTTP services for decisions:

```python
# External service
@app.route('/filter', methods=['POST'])
def filter_nodes():
    data = request.json
    pod = data['pod']
    nodes = data['nodes']
    
    # Custom filtering logic
    filtered = [n for n in nodes if custom_check(pod, n)]
    
    return jsonify({'nodes': filtered})
```

### Two-Level Scheduling

1. **Cluster scheduler**: Assigns resources to frameworks
2. **Framework scheduler**: Schedules tasks within resources

Example: Kubernetes + YARN/Mesos

### Predictive Scheduling

Use ML to predict job duration and schedule accordingly:

```python
def predict_duration(pod):
    features = extract_features(pod)  # GPU count, image, etc.
    duration = model.predict(features)
    return duration

def schedule_with_prediction(pods, nodes):
    # Sort by predicted duration
    pods = sorted(pods, key=predict_duration)
    
    # Schedule shortest jobs first
    for pod in pods:
        node = select_node(pod, nodes)
        schedule(pod, node)
```

## Debugging Schedulers

### 1. Events

Check scheduling events:

```bash
kubectl get events --sort-by='.lastTimestamp' | grep Scheduled
```

Create events from your scheduler:

```python
def send_event(pod, reason, message):
    event = client.CoreV1Event(
        metadata=client.V1ObjectMeta(
            name=f"{pod.name}.{int(time.time())}",
            namespace=pod.namespace
        ),
        involved_object=client.V1ObjectReference(
            kind="Pod",
            name=pod.name,
            namespace=pod.namespace
        ),
        reason=reason,
        message=message,
        type="Normal" if "Success" in reason else "Warning",
        source=client.V1EventSource(component="my-scheduler")
    )
    
    v1.create_namespaced_event(pod.namespace, event)
```

### 2. Metrics

Expose Prometheus metrics:

```python
from prometheus_client import Counter, Histogram

pods_scheduled = Counter(
    'scheduler_pods_scheduled_total',
    'Total number of pods scheduled'
)

scheduling_latency = Histogram(
    'scheduler_latency_seconds',
    'Time to schedule a pod'
)

# In your scheduler
with scheduling_latency.time():
    node = select_node(pod)
    bind_pod_to_node(pod, node)
    pods_scheduled.inc()
```

### 3. Logging

Structure your logs:

```python
logger.info(
    "Scheduled pod",
    extra={
        "pod": pod.name,
        "namespace": pod.namespace,
        "node": node.name,
        "gpus": gpu_count,
        "latency_ms": latency
    }
)
```

## Performance Considerations

### Scheduling Throughput

Default kube-scheduler: ~1000 pods/second

Optimize:
- Cache node information
- Batch scheduling decisions
- Parallelize filtering
- Use informers instead of direct API calls

```python
# Use informers for efficiency
from kubernetes import client, config, informer

def create_informers():
    v1 = client.CoreV1Api()
    
    # Pod informer
    pod_informer = informer.Informer(
        v1.list_pod_for_all_namespaces,
        timeout=60
    )
    
    pod_informer.add_event_handler(
        lambda obj: handle_pod_event(obj)
    )
    
    pod_informer.start()
```

### Scalability

For large clusters (1000+ nodes):
- Partition nodes into groups
- Schedule locally first
- Use probabilistic algorithms
- Approximate instead of optimal

## Further Resources

- [Official Kubernetes Scheduler Docs](https://kubernetes.io/docs/concepts/scheduling-eviction/)
- [Scheduling Framework Design](https://github.com/kubernetes/enhancements/tree/master/keps/sig-scheduling/624-scheduling-framework)
- Paper: "Borg: Large-scale cluster management at Google"
- Paper: "Omega: flexible, scalable schedulers for large compute clusters"

