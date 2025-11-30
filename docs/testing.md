# Testing Guide

This guide explains the testing approach for the Firefly Cloud integration, including how to run tests and how version compatibility is handled.

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_coordinator.py -v

# Run specific test
pytest tests/test_coordinator.py::test_coordinator_initialization -v

# Run with coverage report
pytest --cov=custom_components.firefly_cloud --cov-report=html

# Run with detailed output
pytest -vv
```

### Using the DevContainer

The project includes a VS Code devcontainer with all dependencies pre-configured:

```bash
# Run tests with coverage (requires >95% for passing)
./dev.sh test-cov

# Run all linting and validation
./dev.sh validate

# Run individual linting tools
./dev.sh lint
```

### Test Structure

Tests are organized by module:

- `tests/test_api.py` - API client tests
- `tests/test_config_flow.py` - Configuration flow tests
- `tests/test_coordinator.py` - Data coordinator tests
- `tests/test_diagnostics.py` - Diagnostics platform tests
- `tests/test_init.py` - Integration initialization tests
- `tests/conftest.py` - Shared fixtures and test utilities

## Version Compatibility

### The Challenge

Home Assistant evolves rapidly, and API changes between versions can break tests. The integration supports multiple Home Assistant versions, each with different `ConfigEntry` requirements:

- **HA 2025.x and newer**: Requires `subentries_data` parameter, has `discovery_keys` parameter
- **HA 2024.x and older**: Doesn't have `subentries_data` or `discovery_keys` parameters

### The Solution: `create_config_entry_with_version_compat()`

The integration includes a sophisticated version compatibility helper in `tests/conftest.py` that automatically detects which parameters are supported and adjusts accordingly.

**Implementation** ([conftest.py:27-53](../tests/conftest.py#L27-L53)):

```python
def create_config_entry_with_version_compat(**kwargs):
    """Create a ConfigEntry with version-compatible parameters.

    Home Assistant versions have different required/optional parameters:
    - 2025.x: requires 'subentries_data', has 'discovery_keys'
    - Older: doesn't have 'subentries_data' or 'discovery_keys'
    """
    # Check if ConfigEntry.__init__ accepts parameters
    sig = inspect.signature(ConfigEntry.__init__)
    params = sig.parameters

    # Handle subentries_data (required in 2025.x, doesn't exist in older)
    if "subentries_data" in params:
        # HA 2025.x and newer - subentries_data is required
        if "subentries_data" not in kwargs:
            kwargs["subentries_data"] = {}
    else:
        # Older HA versions - subentries_data doesn't exist
        kwargs.pop("subentries_data", None)

    # Handle discovery_keys (exists in newer versions, not in older)
    if "discovery_keys" not in params:
        # Older HA versions don't have discovery_keys parameter
        kwargs.pop("discovery_keys", None)

    return ConfigEntry(**kwargs)
```

### How It Works

1. **Runtime Inspection**: Uses Python's `inspect` module to check which parameters the current HA version's `ConfigEntry.__init__` accepts
2. **Automatic Adjustment**:
   - If `subentries_data` is required but not provided → adds empty dict
   - If `subentries_data` doesn't exist in this HA version → removes it from kwargs
   - If `discovery_keys` doesn't exist in this HA version → removes it from kwargs
3. **Transparent Usage**: Tests can be written once and work across all supported HA versions

### Usage in Tests

```python
from tests.conftest import create_config_entry_with_version_compat
from types import MappingProxyType

# Create a config entry that works across all HA versions
entry = create_config_entry_with_version_compat(
    version=1,
    minor_version=1,
    domain=DOMAIN,
    title="Test School",
    data={
        CONF_SCHOOL_CODE: "testschool",
        CONF_SCHOOL_NAME: "Test School",
        CONF_HOST: "testschool.fireflysolutions.co.uk",
        CONF_DEVICE_ID: "test-device-123",
        CONF_SECRET: "secret-token-456",
        CONF_USER_GUID: "user-guid-789",
    },
    options={},
    entry_id="test-entry-1",
    unique_id="test-unique-1",
    source="user",
    discovery_keys=MappingProxyType({}),  # Automatically removed if not supported
)
```

## Test Coverage Requirements

The integration targets Home Assistant Silver tier certification, which requires:

- **>95% test coverage** across all modules
- **All error scenarios tested** (network failures, auth expiry, rate limiting, etc.)
- **Config flow testing** including user input validation and error handling
- **Coordinator testing** for data fetching and error recovery
- **Entity testing** for state updates and attribute handling

### Checking Coverage

```bash
# Generate HTML coverage report
pytest --cov=custom_components.firefly_cloud --cov-report=html

# Open coverage report
open htmlcov/index.html
```

Coverage report shows:
- Overall coverage percentage
- Line-by-line coverage for each file
- Uncovered lines highlighted in red

## Writing New Tests

### Test Fixtures

Use the provided fixtures in `conftest.py`:

```python
def test_example(hass, mock_config_entry, mock_firefly_api):
    """Example test using fixtures."""
    # hass - Home Assistant instance
    # mock_config_entry - Pre-configured config entry
    # mock_firefly_api - Mocked API client

    # Your test code here
    pass
```

Available fixtures:
- `hass` - Full Home Assistant instance
- `mock_config_entry` - Config entry with test data
- `mock_school_info` - Mock school information
- `mock_user_info` - Mock user information
- `mock_events` - Mock calendar events
- `mock_tasks` - Mock homework/assignment tasks
- `mock_firefly_api` - Fully mocked API client
- `mock_coordinator_data` - Complete coordinator data structure

### Async Testing

All tests that interact with async functions must be marked:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function(hass):
    """Test an async function."""
    result = await some_async_function()
    assert result == expected_value
```

### Mocking API Responses

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_api_call(mock_firefly_api):
    """Test API error handling."""
    # Configure mock to raise an exception
    mock_firefly_api.get_user_info.side_effect = FireflyConnectionError("Connection failed")

    # Test that error is handled correctly
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
```

## Common Testing Patterns

### Testing Error Scenarios

```python
@pytest.mark.asyncio
async def test_connection_error_handling(hass, mock_api):
    """Test coordinator handles connection errors."""
    coordinator = FireflyUpdateCoordinator(hass=hass, api=mock_api, task_lookahead_days=7)

    # Simulate connection failure
    mock_api.get_user_info.side_effect = FireflyConnectionError("Network error")

    # Verify error is raised and statistics are updated
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator.statistics["failed_updates"] == 1
    assert "FireflyConnectionError" in coordinator.statistics["error_counts"]
```

### Testing State Updates

```python
@pytest.mark.asyncio
async def test_sensor_state(hass, mock_coordinator):
    """Test sensor state updates."""
    sensor = FireflyUpcomingTasksSensor(coordinator=mock_coordinator, child_guid="child-1")

    assert sensor.state == 3  # Expected number of tasks
    assert sensor.extra_state_attributes["tasks"][0]["title"] == "Math Homework"
```

### Testing Config Flow

```python
@pytest.mark.asyncio
async def test_config_flow_user_init(hass):
    """Test the user config flow initialization."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
```

## Continuous Integration

Tests run automatically on GitHub Actions for:
- **Multiple Python versions** (3.11, 3.12)
- **Multiple Home Assistant versions** (stable, beta, dev)
- **Code quality checks** (black, flake8, mypy, pylint)

All tests must pass before PRs can be merged.

## Troubleshooting

### Tests Fail with ConfigEntry Parameter Errors

If you see errors like `TypeError: ConfigEntry.__init__() missing required keyword-only arguments`, make sure you're using `create_config_entry_with_version_compat()` instead of `ConfigEntry()` directly.

### Mock Not Resetting Between Tests

Use `side_effect = None` to clear exceptions, not `return_value`:

```python
# Wrong - doesn't clear side_effect
mock_api.get_user_info.return_value = {"guid": "123"}

# Right - clears side_effect first
mock_api.get_user_info.side_effect = None
mock_api.get_user_info.return_value = {"guid": "123"}
```

### Coverage Drops Unexpectedly

Check for:
- Uncovered error handling paths
- Missing tests for new features
- Untested edge cases (None values, empty lists, etc.)

Run coverage report to see exactly which lines are uncovered:

```bash
pytest --cov=custom_components.firefly_cloud --cov-report=term-missing
```

## Additional Resources

- [Home Assistant Testing Documentation](https://developers.home-assistant.io/docs/development_testing/)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
