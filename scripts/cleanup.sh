#!/bin/bash
# Clean up all resources

set -e

echo "==================================="
echo "Cleanup GPU Scheduler Playground"
echo "==================================="

read -p "This will delete the entire cluster. Are you sure? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 1
fi

echo ""
echo "Deleting kind cluster..."
kind delete cluster --name gpu-scheduler-cluster

echo ""
echo "Removing Docker images..."
docker rmi gpu-scheduler:latest || true
docker rmi pytorch-training:latest || true
docker rmi tensorflow-training:latest || true

echo ""
echo "==================================="
echo "Cleanup Complete!"
echo "==================================="

