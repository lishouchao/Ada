# Makefile for Ada

.PHONY: test coverage lint format clean install dev-install

# Default target
all: install

# Install in development mode
dev-install:
	pip install -e ".[dev]"

# Install production
install:
	pip install .

# Run tests
test:
	pytest tests/ -v

# Run tests with coverage
coverage:
	pytest tests/ --cov=ada --cov-report=html --cov-report=term

# Run specific test file
test-%:
	pytest tests/$*.py -v

# Run linting
lint:
	ruff check src/ ada/

# Run formatting
format:
	black src/ ada/ tests/

# Run type checking
typecheck:
	mypy src/ada

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build distribution
build: clean
	python -m build

# Run the application
run:
	python -m ada

# Run CLI
cli:
	ada chat

# Run GUI
gui:
	ada-gui

# Run daemon
daemon:
	ada daemon

# Generate documentation
docs:
	cd docs && make html

# Install pre-commit hooks
hooks:
	pre-commit install

# Run all checks
check: lint typecheck test
	echo "All checks passed!"
