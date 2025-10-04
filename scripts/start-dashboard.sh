#!/bin/bash
# Start metrics dashboard (port-forward to scheduler metrics)

echo "Starting metrics dashboard..."
echo ""
echo "Metrics available at: http://localhost:8080/metrics"
echo "Health check at: http://localhost:8080/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

kubectl port-forward -n scheduler-system svc/gpu-scheduler-metrics 8080:8080

