#!/bin/bash
# Run DiaBay backend tests

set -e

echo "==================================="
echo "DiaBay Backend Test Suite"
echo "==================================="

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install test dependencies if not already installed
echo "Checking test dependencies..."
pip install -q -r requirements-test.txt

# Run tests
echo ""
echo "Running tests..."
echo ""

# Run with coverage if pytest-cov is available
if python -c "import pytest_cov" 2>/dev/null; then
    pytest tests/ --cov=. --cov-report=term-missing --cov-report=html
else
    pytest tests/
fi

echo ""
echo "==================================="
echo "Tests completed!"
echo "==================================="
