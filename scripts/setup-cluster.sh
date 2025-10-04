#!/bin/bash
# Setup local Kubernetes cluster with simulated GPUs

set -e

echo "==================================="
echo "GPU Scheduler Cluster Setup"
echo "==================================="

# Check prerequisites
command -v kind >/dev/null 2>&1 || {
    echo "Error: kind is not installed. Please install it first:"
    echo "  brew install kind"
    exit 1
}

command -v kubectl >/dev/null 2>&1 || {
    echo "Error: kubectl is not installed. Please install it first:"
    echo "  brew install kubectl"
    exit 1
}

command -v docker >/dev/null 2>&1 || {
    echo "Error: docker is not installed. Please install Docker Desktop first."
    exit 1
}

# Delete existing cluster if exists
if kind get clusters | grep -q "gpu-scheduler-cluster"; then
    echo "Deleting existing cluster..."
    kind delete cluster --name gpu-scheduler-cluster
fi

# Create cluster
echo ""
echo "Creating Kubernetes cluster with kind..."
kind create cluster --config k8s/cluster/kind-config.yaml

# Wait for cluster to be ready
echo ""
echo "Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=120s

# Apply GPU device plugin (simulates GPUs)
echo ""
echo "Deploying fake GPU device plugin..."
kubectl apply -f k8s/cluster/gpu-device-plugin.yaml

# Wait a bit for device plugin to advertise GPUs
echo "Waiting for GPU resources to be advertised..."
sleep 10

# Display cluster info
echo ""
echo "==================================="
echo "Cluster Setup Complete!"
echo "==================================="
echo ""
echo "Cluster nodes:"
kubectl get nodes -o wide

echo ""
echo "GPU resources per node:"
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPUs:.status.capacity.'nvidia\.com/gpu'

echo ""
echo "Next steps:"
echo "  1. Deploy the scheduler: ./scripts/deploy-scheduler.sh"
echo "  2. Submit a test job: kubectl apply -f examples/pytorch-training.yaml"
echo "  3. Watch scheduler logs: ./scripts/view-logs.sh"

