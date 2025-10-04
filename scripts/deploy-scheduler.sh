#!/bin/bash
# Build and deploy the custom GPU scheduler

set -e

echo "==================================="
echo "Deploying GPU Scheduler"
echo "==================================="

# Check if cluster exists
if ! kind get clusters | grep -q "gpu-scheduler-cluster"; then
    echo "Error: Cluster not found. Run ./scripts/setup-cluster.sh first"
    exit 1
fi

# Build scheduler Docker image
echo ""
echo "Building scheduler Docker image..."
docker build -t gpu-scheduler:latest ./scheduler/

# Load image into kind cluster
echo ""
echo "Loading image into kind cluster..."
kind load docker-image gpu-scheduler:latest --name gpu-scheduler-cluster

# Build ML job images
echo ""
echo "Building PyTorch training image..."
docker build -t pytorch-training:latest ./ml-jobs/pytorch/

echo ""
echo "Building TensorFlow training image..."
docker build -t tensorflow-training:latest ./ml-jobs/tensorflow/

# Load ML images into cluster
echo ""
echo "Loading ML images into kind cluster..."
kind load docker-image pytorch-training:latest --name gpu-scheduler-cluster
kind load docker-image tensorflow-training:latest --name gpu-scheduler-cluster

# Deploy scheduler
echo ""
echo "Deploying scheduler to Kubernetes..."
kubectl apply -f k8s/scheduler/deployment.yaml

# Wait for scheduler to be ready
echo ""
echo "Waiting for scheduler to be ready..."
kubectl wait --for=condition=Available deployment/gpu-scheduler \
    -n scheduler-system --timeout=120s

# Display status
echo ""
echo "==================================="
echo "Scheduler Deployed Successfully!"
echo "==================================="
echo ""
echo "Scheduler pods:"
kubectl get pods -n scheduler-system

echo ""
echo "Scheduler logs:"
kubectl logs -n scheduler-system -l app=gpu-scheduler --tail=20

echo ""
echo "Next steps:"
echo "  1. Submit a training job: kubectl apply -f examples/pytorch-training.yaml"
echo "  2. View scheduler logs: ./scripts/view-logs.sh"
echo "  3. Check job status: ./scripts/job-status.sh"

