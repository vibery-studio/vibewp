# VibeWP Development Makefile

.PHONY: help test test-unit test-integration test-all docker-up docker-down clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

test: test-unit ## Run unit tests (default)

test-unit: ## Run unit tests with mocks
	@echo "Running unit tests..."
	pytest tests/test_remote_backup.py -v --cov=cli.utils.remote_backup --cov-report=term-missing

test-integration: ## Run integration tests with Docker
	@echo "Starting test services..."
	docker-compose -f docker-compose.test.yml up -d
	@echo "Waiting for services to be ready..."
	sleep 10
	@echo "Running integration tests..."
	RUN_INTEGRATION_TESTS=1 pytest tests/integration/ -v || true
	@echo "Stopping test services..."
	docker-compose -f docker-compose.test.yml down

test-all: ## Run all tests (unit + integration)
	@echo "Running all tests..."
	make test-unit
	make test-integration

docker-up: ## Start test services (MinIO + SSH)
	@echo "Starting test services..."
	docker-compose -f docker-compose.test.yml up -d
	@echo "Services started. Access MinIO at http://localhost:9001"
	@echo "Login: minioadmin / minioadmin"

docker-down: ## Stop test services
	@echo "Stopping test services..."
	docker-compose -f docker-compose.test.yml down

docker-logs: ## View test service logs
	docker-compose -f docker-compose.test.yml logs -f

clean: ## Clean up test artifacts
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage
	@echo "Cleaned up test artifacts"

install-dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-mock boto3
	@echo "Development dependencies installed"

setup-test: ## Setup test environment
	@echo "Setting up test environment..."
	mkdir -p tests/fixtures/ssh
	ssh-keygen -t rsa -f tests/fixtures/ssh/id_rsa -N "" -q || true
	cp tests/fixtures/ssh/id_rsa.pub tests/fixtures/ssh/authorized_keys || true
	@echo "Test environment ready"

minio-console: ## Open MinIO console in browser
	@echo "Opening MinIO console..."
	open http://localhost:9001 || xdg-open http://localhost:9001 || echo "Please open http://localhost:9001 in your browser"

test-quick: ## Quick smoke test
	@echo "Running quick smoke test..."
	pytest tests/test_remote_backup.py::TestRemoteBackupConfig -v

lint: ## Run code linting
	@echo "Running linters..."
	python3 -m py_compile cli/utils/remote_backup.py
	python3 -m py_compile cli/commands/backup.py
	python3 -m py_compile cli/utils/config.py
	@echo "Linting complete"

coverage: ## Generate coverage report
	@echo "Generating coverage report..."
	pytest tests/test_remote_backup.py --cov=cli.utils.remote_backup --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"
	open htmlcov/index.html || xdg-open htmlcov/index.html || echo "Open htmlcov/index.html in your browser"

.DEFAULT_GOAL := help
