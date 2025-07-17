# Tests Folder Structure

This directory contains all automated tests for the Events2go backend application. Below is an overview of the test files and their purposes:

- **conftest.py**: Shared fixtures and configuration for pytest, including database setup, test client, and utility fixtures.
- **test_async_examples.py**: Examples and reference patterns for writing async tests, including database, API, and concurrency tests.
- **test_database.py**: Tests for database connection, transactions, metadata, and performance.
- **test_integration.py**: Integration tests that verify the interaction between different components (API, DB, middleware, etc.).
- **test_main.py**: Tests for the main FastAPI application entrypoint and core routes.
- **test_models.py**: Tests for ORM models, their relationships, and model-specific logic.
- **utils.py**: Test utility functions and async helpers for use in other test files.
- **README.md**: This file. Describes the test suite and organization.
- **__init__.py**: Marks this directory as a Python package.

## How to Run Tests

Run all tests with:

```bash
pytest tests/
```

## Notes
- All test files use explicit `if`/`raise AssertionError` for assertions (no bare `assert`), to comply with security best practices.
- Fixtures are defined in `conftest.py` and are shared across all test modules.
- Utility functions for async testing are in `utils.py`.

---

# Testing Documentation

This directory contains comprehensive async tests for the FastAPI Events2go application.

## Overview

The test suite is designed with full async support and includes:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Database Tests**: Test database operations and models
- **API Tests**: Test HTTP endpoints and middleware
- **Performance Tests**: Test performance characteristics

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Test configuration and fixtures
├── utils.py                 # Test utilities and helpers
├── test_main.py             # Main application endpoint tests
├── test_database.py         # Database connection and operation tests
├── test_models.py           # Database model tests
├── test_integration.py      # Integration tests
├── test_async_examples.py   # Comprehensive async test examples
└── README.md               # This file
```

## Key Features

### Async Support
- Full async/await support throughout the test suite
- Proper async fixture management
- Concurrent test execution capabilities
- Async context managers for resource management

### Database Testing
- In-memory SQLite database for fast testing
- Automatic table creation and cleanup
- Transaction isolation between tests
- Async database session management

### API Testing
- Async HTTP client for endpoint testing
- Middleware testing support
- CORS and custom header validation
- Error handling verification

### Performance Testing
- Operation timing and benchmarking
- Concurrent operation testing
- Resource usage monitoring
- Performance assertion utilities

## Running Tests

### Quick Start
```bash
# Run all tests (excluding slow ones)
python test.py

# Run specific test categories
python test.py unit
python test.py integration
python test.py db

# Run all tests including slow ones
python test.py all
```

### Advanced Usage
```bash
# Using pytest directly
pytest tests/

# Run with coverage
pytest --cov=. --cov-report=html tests/

# Run specific test file
pytest tests/test_models.py

# Run specific test function
pytest tests/test_models.py::TestRoleModel::test_create_role

# Run tests with specific markers
pytest -m "unit and not slow"
pytest -m "integration or db"

# Run tests in parallel
pytest -n auto tests/

# Verbose output
pytest -v tests/
```

### Using the Advanced Test Runner
```bash
# Install dependencies and run tests
python run_tests.py --install-deps

# Run with coverage report
python run_tests.py --coverage

# Run tests in parallel
python run_tests.py --parallel

# Run specific test categories
python run_tests.py --unit --verbose
python run_tests.py --integration --slow
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.db`: Database-related tests
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.auth`: Authentication-related tests

## Fixtures

### Database Fixtures
- `test_engine`: Async database engine
- `test_session_factory`: Session factory for creating database sessions
- `test_db_session`: Individual database session for tests
- `test_db_transaction`: Database session with automatic rollback
- `clean_db`: Ensures clean database state

### Application Fixtures
- `test_app`: FastAPI application instance with test configuration
- `test_client`: Async HTTP client for API testing
- `test_settings`: Test-specific configuration settings

### Utility Fixtures
- `mock_user_data`: Sample user data for testing
- `mock_category_data`: Sample category data for testing
- `auth_headers`: Authentication headers for API tests
- `benchmark_settings`: Performance testing configuration

## Test Utilities

### AsyncDatabaseTestHelper
Provides async methods for database operations:
```python
db_helper = AsyncDatabaseTestHelper(test_db_session)
role = await db_helper.create_role(role_name="Test Role")
user = await db_helper.create_admin_user(role_id=role.role_id)
```

### AsyncAPITestHelper
Provides async methods for API testing:
```python
api_helper = AsyncAPITestHelper(test_client)
response = await api_helper.get("/health")
assert_response_success(response)
```

### AsyncTestUtils
General async testing utilities:
```python
# Wait for a condition
condition_met = await AsyncTestUtils.wait_for_condition(check_func, timeout=5.0)

# Run with timeout
result = await AsyncTestUtils.run_with_timeout(operation(), timeout=10.0)

# Run concurrent tasks
results = await AsyncTestUtils.run_concurrent_tasks(tasks, max_concurrent=3)
```

### Performance Tracking
```python
tracker = AsyncPerformanceTracker()
result = await tracker.track_operation("operation_name", operation_func)
tracker.assert_performance("operation_name", max_duration=1.0)
```

## Writing Tests

### Basic Async Test
```python
@pytest.mark.asyncio
@pytest.mark.unit
async def test_example(test_db_session: AsyncSession):
    db_helper = AsyncDatabaseTestHelper(test_db_session)
    role = await db_helper.create_role(role_name="Test Role")
    assert role.role_name == "Test Role"
```

### API Test
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_api_endpoint(test_client: AsyncClient):
    api_helper = AsyncAPITestHelper(test_client)
    response = await api_helper.get("/health")
    assert_response_success(response)
    assert response["data"]["status"] == "healthy"
```

### Concurrent Test
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_operations(test_db_session: AsyncSession):
    db_helper = AsyncDatabaseTestHelper(test_db_session)

    async def create_role(index: int):
        return await db_helper.create_role(role_name=f"Role {index}")

    tasks = [create_role(i) for i in range(5)]
    roles = await AsyncTestUtils.run_concurrent_tasks(tasks)
    assert len(roles) == 5
```

## Configuration

### pytest.ini
Basic pytest configuration with async support:
```ini
[tool:pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

### pyproject.toml
Advanced configuration including coverage, code quality tools, and test dependencies.

## Best Practices

1. **Use Async Fixtures**: Always use async fixtures for database and API operations
2. **Proper Cleanup**: Use fixtures that automatically clean up resources
3. **Isolation**: Each test should be independent and not rely on other tests
4. **Performance**: Mark slow tests appropriately and exclude them from regular runs
5. **Error Handling**: Test both success and error scenarios
6. **Concurrency**: Test concurrent operations where applicable
7. **Mocking**: Use mocks for external dependencies

## Troubleshooting

### Common Issues

1. **Event Loop Errors**: Ensure `asyncio_mode = auto` is set in pytest configuration
2. **Database Errors**: Check that test database fixtures are properly configured
3. **Import Errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`
4. **Timeout Errors**: Increase timeout values for slow operations or mark tests as slow

### Debug Mode
Run tests with verbose output and no capture:
```bash
pytest -v -s tests/test_specific.py
```

### Coverage Reports
Generate detailed coverage reports:
```bash
pytest --cov=. --cov-report=html --cov-report=term-missing tests/
```

## Examples

See `test_async_examples.py` for comprehensive examples of:
- Basic async operations
- Concurrent testing
- Performance tracking
- Error handling
- Context managers
- Mocking
- Complex workflows

This file serves as a reference for all async testing patterns used in the application.
