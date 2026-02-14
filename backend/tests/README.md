# DiaBay Backend Tests

This directory contains tests for the DiaBay backend API and core functionality.

## Test Structure

```
tests/
├── __init__.py
├── test_api_endpoints.py   # Tests for FastAPI endpoints
├── test_duplicates.py       # Tests for duplicate detection
└── README.md               # This file
```

## Running Tests

### Quick Start

```bash
# From backend directory
./run_tests.sh
```

### Manual Testing

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api_endpoints.py

# Run specific test class
pytest tests/test_api_endpoints.py::TestHealthEndpoint

# Run specific test function
pytest tests/test_api_endpoints.py::TestHealthEndpoint::test_health_check

# Run with coverage
pytest --cov=. --cov-report=term-missing
```

## Test Categories

### Unit Tests
- `test_duplicates.py`: Tests for `PerceptualHasher` and `DuplicateDetector` classes
- Isolated tests that don't require external dependencies

### Integration Tests
- `test_api_endpoints.py`: Tests for FastAPI endpoints
- Tests that interact with the database and API

## Writing New Tests

### Test File Naming
- Test files must start with `test_`
- Example: `test_new_feature.py`

### Test Class Naming
- Test classes must start with `Test`
- Example: `class TestNewFeature:`

### Test Function Naming
- Test functions must start with `test_`
- Example: `def test_feature_works():`

### Example Test

```python
import pytest

class TestMyFeature:
    """Tests for my new feature"""

    def test_basic_functionality(self):
        """Test basic functionality works"""
        result = my_function(input_data)
        assert result == expected_output

    def test_error_handling(self):
        """Test error handling"""
        with pytest.raises(ValueError):
            my_function(invalid_input)

    @pytest.mark.asyncio
    async def test_async_function(self):
        """Test async function"""
        result = await async_function()
        assert result is not None
```

## Fixtures

### Available Fixtures
- `test_db`: Async test database session
- `client`: TestClient for FastAPI
- `temp_dirs`: Temporary directories for file testing
- `temp_output_dir`: Temporary output directory with test images

### Using Fixtures

```python
def test_with_database(test_db):
    """Test that uses database fixture"""
    # test_db is automatically provided by pytest

def test_with_temp_files(temp_dirs):
    """Test that uses temporary directories"""
    output_dir = temp_dirs['output']
    # Use output_dir for testing
```

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements-test.txt
    pytest tests/ --cov=.
```

## Coverage Reports

After running tests with coverage:
```bash
pytest --cov=. --cov-report=html
```

Open `htmlcov/index.html` in a browser to view detailed coverage report.

## Troubleshooting

### Import Errors
If you see import errors, make sure you're running tests from the backend directory:
```bash
cd diabay/backend
pytest
```

### Async Test Failures
Make sure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```

### Database Errors
Tests use an in-memory SQLite database that's created fresh for each test.
If you see database errors, check that aiosqlite is installed:
```bash
pip install aiosqlite
```
