# ML Workload Scheduling Playground Makefile

.PHONY: help setup deploy clean status logs metrics submit-test experiments

# Default target
help:
	@echo "ML Workload Scheduling Playground"
	@echo "=================================="
	@echo ""
	@echo "Available targets:"
	@echo "  setup          - Create cluster and install GPU device plugin"
	@echo "  deploy         - Build and deploy the scheduler"
	@echo "  status         - Show cluster and job status"
	@echo "  logs           - Stream scheduler logs"
	@echo "  metrics        - Access metrics endpoint"
	@echo "  submit-test    - Submit test jobs"
	@echo "  experiments    - Run all experiments"
	@echo "  clean          - Delete cluster and cleanup"
	@echo ""
	@echo "Quick start:"
	@echo "  make setup deploy submit-test"

# Setup cluster
setup:
	@echo "Setting up Kubernetes cluster..."
	./scripts/setup-cluster.sh

# Build and deploy scheduler
deploy:
	@echo "Building and deploying scheduler..."
	./scripts/deploy-scheduler.sh

# Show status
status:
	@echo "Cluster Status:"
	@echo "==============="
	./scripts/job-status.sh

# Stream logs
logs:
	@echo "Streaming scheduler logs (Ctrl+C to stop)..."
	./scripts/view-logs.sh

# Port-forward metrics
metrics:
	@echo "Starting metrics dashboard..."
	@echo "Access at: http://localhost:8080/metrics"
	./scripts/start-dashboard.sh

# Submit test jobs
submit-test:
	@echo "Submitting test jobs..."
	kubectl apply -f examples/pytorch-training.yaml
	@echo "Job submitted! Run 'make status' to check progress"

# Submit all test jobs
submit-all:
	@echo "Submitting all test jobs..."
	kubectl apply -f examples/
	@echo "Jobs submitted! Run 'make logs' to watch scheduling"

# Run experiments
experiments:
	@echo "Running experiments..."
	@echo ""
	@echo "1. Policy Comparison"
	python experiments/compare_policies.py
	@echo ""
	@echo "2. Gang Scheduling"
	python experiments/gang_scheduling.py
	@echo ""
	@echo "3. Multi-Tenant Simulation"
	python experiments/multi_tenant.py

# Rebuild scheduler
rebuild:
	@echo "Rebuilding scheduler..."
	docker build -t gpu-scheduler:latest ./scheduler/
	kind load docker-image gpu-scheduler:latest --name gpu-scheduler-cluster
	kubectl rollout restart deployment/gpu-scheduler -n scheduler-system
	@echo "Scheduler rebuilt and restarted!"

# Delete jobs
delete-jobs:
	@echo "Deleting all jobs..."
	kubectl delete pods --all-namespaces --selector schedulerName=gpu-scheduler

# Cleanup everything
clean:
	@echo "Cleaning up..."
	./scripts/cleanup.sh

# Full reset
reset: clean setup deploy
	@echo "Full reset complete!"

# Watch jobs
watch:
	watch -n 2 kubectl get pods --all-namespaces -o wide

# CLI status
cli-status:
	./cli/gpusched.py status

# CLI list
cli-list:
	./cli/gpusched.py list

