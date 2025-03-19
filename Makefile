.PHONY: setup test lint format clean docker-setup docker-test

# Default target
help:
	@echo "Available commands:"
	@echo "  make setup          Install dependencies and setup development environment"
	@echo "  make test           Run tests"
	@echo "  make lint           Run linting checks"
	@echo "  make format         Format code using black and isort"
	@echo "  make clean          Remove build artifacts and temporary files"
	@echo "  make docker-setup   Build and setup Docker environment"
	@echo "  make docker-test    Run tests in Docker"

# Setup development environment
setup:
	@echo "Setting up development environment..."
	@if [ "$(OS)" = "Windows_NT" ]; then \
		scripts/setup_dev.bat; \
	else \
		bash scripts/setup_dev.sh; \
	fi

# Run tests
test:
	@echo "Running tests..."
	pytest -c config/ci/pytest.ini

# Run linting checks
lint:
	@echo "Running linting checks..."
	pre-commit run --all-files

# Format code
format:
	@echo "Formatting code..."
	black src tests scripts
	isort src tests scripts

# Clean build artifacts and temporary files
clean:
	@echo "Cleaning build artifacts and temporary files..."
	rm -rf build/
	rm -rf dist/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete

# Docker setup
docker-setup:
	@echo "Setting up Docker environment..."
	docker-compose build

# Run tests in Docker
docker-test:
	@echo "Running tests in Docker..."
	docker-compose run --rm test 