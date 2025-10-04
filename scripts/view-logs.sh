#!/bin/bash
# View scheduler logs in real-time

echo "Streaming scheduler logs (Ctrl+C to stop)..."
echo ""

kubectl logs -n scheduler-system -l app=gpu-scheduler --follow --tail=50

