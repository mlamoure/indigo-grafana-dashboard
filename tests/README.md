# Test Suite for Indigo Grafana Dashboard Plugin

Comprehensive test suite for the modernized v2025.0.0 plugin.

## Test Structure

```
tests/
├── conftest.py                  # Pytest fixtures and mocks
├── test_influx_connection.py    # InfluxDB connection tests
├── test_json_adaptor.py         # JSON conversion tests
├── test_filters.py              # Data filtering tests
└── test_plugin_config.py        # Configuration and state tests
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_influx_connection.py
```

### Run with Coverage Report

```bash
pytest --cov --cov-report=html
```

Coverage report will be generated in `htmlcov/index.html`.

### Run in Parallel

```bash
pytest -n auto
```

### Run Only Fast Tests

```bash
pytest -m "not slow"
```

## Test Categories

### Unit Tests (`-m unit`)
- Test individual functions and classes in isolation
- Use mocks for external dependencies
- Fast execution

### Integration Tests (`-m integration`)
- Test interaction between components
- May require external services (mocked)
- Slower execution

### Connection Tests (`-m connection`)
- Test InfluxDB connection handling
- Retry logic
- Error conditions

## Coverage Goals

- **Target**: 80% code coverage
- **Critical paths**: 100% coverage
  - Connection handling
  - Data filtering
  - Configuration validation

## Test Fixtures

See `conftest.py` for available fixtures:

- `mock_indigo`: Mock Indigo module
- `mock_influxdb_client`: Mock InfluxDB client
- `plugin_config`: Standard plugin configuration
- `mock_device`: Mock Indigo device
- `mock_variable`: Mock Indigo variable

## Writing New Tests

1. Create test file: `test_<module>.py`
2. Use descriptive test names: `test_<what>_<condition>_<expected>`
3. Add docstrings explaining test purpose
4. Use appropriate fixtures from `conftest.py`
5. Add markers for test categorization

Example:

```python
@pytest.mark.unit
def test_connection_success(mock_influxdb_client):
    """Test successful connection to InfluxDB."""
    # Test implementation
```

## Continuous Integration

Tests run automatically on:
- Git commits (pre-commit hook)
- Pull requests
- Release builds

## Troubleshooting

### Import Errors

If you encounter import errors, ensure the plugin directory is in your Python path:

```bash
export PYTHONPATH="${PYTHONPATH}:${PWD}/Grafana Home Dashboard.indigoPlugin/Contents/Server Plugin"
```

### Mock Issues

If mocks aren't working, verify the import path matches the actual module structure.

### Coverage Not Generated

Ensure pytest-cov is installed:

```bash
pip install pytest-cov
```
