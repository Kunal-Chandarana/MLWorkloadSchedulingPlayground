#!/bin/bash
# Display status of all training jobs

echo "==================================="
echo "Training Job Status"
echo "==================================="
echo ""

echo "All pods using gpu-scheduler:"
kubectl get pods --all-namespaces --field-selector spec.schedulerName=gpu-scheduler -o wide

echo ""
echo "GPU allocation per node:"
kubectl get nodes -o custom-columns=\
NAME:.metadata.name,\
TOTAL_GPU:.status.capacity.'nvidia\.com/gpu',\
ALLOCATABLE_GPU:.status.allocatable.'nvidia\.com/gpu'

echo ""
echo "Recent events:"
kubectl get events --all-namespaces --sort-by='.lastTimestamp' | grep -i "scheduled\|gpu" | tail -10

