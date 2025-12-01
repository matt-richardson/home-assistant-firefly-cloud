# Home Assistant Firefly Cloud Integration - Technical Specification

## Overview
This technical specification outlines the implementation of a Home Assistant integration for Firefly Cloud (school learning platform) that meets Silver-tier quality standards. The integration provides sensor entities for displaying children's school schedules and upcoming tasks.

## Quality Standards Target
Full details: https://developers.home-assistant.io/docs/core/integration-quality-scale/checklist

**Bronze Tier Requirements** (Foundation):
- Service actions registered in async_setup
- Appropriate polling interval (15 minutes)
- Branding assets (icons, logos)
- Common Home Assistant modules usage
- Config flow test coverage
- UI-based setup (no YAML configuration)
- Dependency transparency in manifest.json
- Comprehensive documentation
- Unique entity IDs
- Runtime data storage in hass.data
- Connection testing during setup
- Prevention of duplicate device/service setup

**Silver Tier Requirements** (Builds on the bronze tier):
- Above 95% test coverage for all integration modules
- Config entry unloading support
- Reauthentication available via UI
- Service actions raise exceptions when encountering failures
- Entity unavailable marking when appropriate
- Integration owner specified in manifest
- Logging when internet/device/service is unavailable
- Specify number of parallel updates
- Describes all integration configuration options
- Describes all integration installation parameters
- Modern Python standards (3.11+)

## Architecture Overview

### Core Components
```
custom_components/firefly_cloud/
├── __init__.py              # Integration setup and platform coordination
├── config_flow.py           # Configuration flow and reauthentication
├── const.py                 # Constants and configuration
├── coordinator.py           # Data update coordinator with statistics tracking
├── sensor.py                # Sensor platform implementation (5 sensor types)
├── calendar.py              # Calendar platform for school events
├── todo.py                  # Todo platform for task management
├── api.py                   # Firefly API client wrapper
├── entity.py                # Base entity class
├── exceptions.py            # Custom exception classes
├── diagnostics.py           # Diagnostics platform for troubleshooting
├── manifest.json            # Integration manifest
├── strings.json             # Localization strings
└── translations/            # Internationalization
    └── en.json

tests/
├── __init__.py
├── conftest.py              # Test configuration and fixtures
├── test_init.py             # Integration setup tests
├── test_config_flow.py      # Config flow tests
├── test_coordinator.py      # Coordinator tests (including statistics)
├── test_sensor.py           # Sensor tests
├── test_calendar.py         # Calendar platform tests
├── test_todo.py             # Todo platform tests
├── test_api.py              # API client tests
└── test_diagnostics.py      # Diagnostics platform tests
```

### Data Flow
1. **Authentication**: OAuth-like flow via browser redirect to Firefly login
2. **Data Fetching**: Coordinator polls Firefly API every 15 minutes
3. **Entity Updates**: Sensors receive data through coordinator callbacks
4. **Error Handling**: Automatic retry with exponential backoff, reauthentication on token expiry

## Technical Implementation

### 1. Integration Entry Point (`__init__.py`)
```python
PLATFORMS = [Platform.CALENDAR, Platform.SENSOR, Platform.TODO]
UPDATE_INTERVAL = timedelta(minutes=15)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Firefly Cloud from a config entry."""
    # Create API client, coordinator, and forward to platforms

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry with proper cleanup."""
    # Unload platforms, shutdown coordinator, cleanup hass.data

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options and reload entry."""

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry to current version."""
```

### 2. Configuration Flow (`config_flow.py`)
**Authentication Flow**:
- Step 1: User enters school code
- Step 2: Generate device ID and redirect to Firefly login
- Step 3: User completes browser authentication
- Step 4: Extract token from redirect URL
- Step 5: Validate credentials and store config entry

**Reauthentication Flow**:
- Triggered automatically on API 401/403 responses
- Reuses existing device ID
- Updates stored credentials without user intervention where possible

### 3. API Client (`api.py`)
Based on existing Node.js driver, translated to async Python:

```python
class FireflyAPIClient:
    def __init__(self, host: str, device_id: str, secret: str):
        self._host = host
        self._device_id = device_id  
        self._secret = secret
        self._session = aiohttp.ClientSession()

    async def async_get_school_info(code: str) -> dict:
        """Get school information from code."""
        
    async def async_verify_credentials(self) -> bool:
        """Verify stored credentials are valid."""
        
    async def async_get_events(self, start: datetime, end: datetime) -> list:
        """Get calendar events for date range."""
        
    async def async_get_tasks(self, options: dict = None) -> list:
        """Get tasks/assignments."""
        
    async def async_graphql_query(self, query: str) -> dict:
        """Execute GraphQL query."""
```

### 4. Data Coordinator (`coordinator.py`)
```python
class FireflyUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: FireflyAPIClient,
                 task_lookahead_days: int, children_guids: list[str] = None):
        super().__init__(
            hass,
            _LOGGER,
            name="Firefly Cloud",
            update_interval=timedelta(minutes=15),
        )
        # Statistics tracking for diagnostics
        self.statistics = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "last_update_time": None,
            "last_success_time": None,
            "last_failure_time": None,
            "error_counts": {},
        }

    async def _async_update_data(self) -> dict:
        """Fetch data from Firefly API with statistics tracking."""
        # Track update statistics
        # Fetch user info (cached), events, and tasks for each child
        # Handle rate limiting, authentication, and connection errors
        # Create/update/dismiss issue registry notifications
        # Return structured data for all platforms

    def _track_failure(self, error_type: str) -> None:
        """Track update failure statistics."""

    def _handle_update_success(self, update_time: str) -> None:
        """Handle successful update and dismiss issues."""
```

### 5. Sensor Platform (`sensor.py`)
**Sensor Types** (5 sensors created per child):
- `sensor.firefly_upcoming_tasks_*` - Tasks due within configured lookahead period
- `sensor.firefly_tasks_due_today_*` - Tasks due today
- `sensor.firefly_overdue_tasks_*` - Tasks past their due date
- `sensor.firefly_current_class_*` - Currently active class/lesson
- `sensor.firefly_next_class_*` - Next scheduled class/lesson

**Sensor Implementation**:
```python
class FireflySensor(FireflyBaseEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, sensor_type, child_guid):
        super().__init__(coordinator, config_entry, child_guid, base_name)
        self._sensor_type = sensor_type
        self._sensor_config = SENSOR_TYPES[sensor_type]

    @property
    def native_value(self) -> Optional[str | int]:
        """Return the state of the sensor."""
        # Task count sensors return integer count
        # Class sensors return class name with optional time prefix

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return detailed attributes for dashboard cards."""
        # Upcoming tasks: task list with due dates, days until due, overdue tasks
        # Tasks due today: task list with descriptions
        # Overdue tasks: task list with days overdue
        # Current class: class details, time remaining, location
        # Next class: class details, time until start, context
```

### 6. Calendar Platform (`calendar.py`)
**Implementation**:
```python
class FireflyCalendar(FireflyBaseEntity, CalendarEntity):
    """Calendar entity showing school events."""

    @property
    def event(self) -> Optional[CalendarEvent]:
        """Return the current or next upcoming event."""

    async def async_get_events(self, hass, start_date, end_date) -> List[CalendarEvent]:
        """Return calendar events within a datetime range."""
        # Filter and return school schedule events

    # Read-only - create/update/delete raise NotImplementedError
```

### 7. Todo Platform (`todo.py`)
**Implementation**:
```python
class FireflyTodoListEntity(FireflyBaseEntity, TodoListEntity):
    """Todo list entity for school tasks."""

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return all tasks as todo items, deduplicated."""
        # Combines upcoming, overdue, and due today tasks
        # Maps Firefly completion status to HA TodoItemStatus

    # Read-only - supported_features = 0
    # create/update/delete/move raise NotImplementedError
```

### 8. Diagnostics Platform (`diagnostics.py`)
**Implementation**:
```python
async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    """Return diagnostics for troubleshooting."""
    # Returns redacted config data (device_id, secret redacted)
    # Coordinator statistics (update counts, timestamps, errors)
    # Data summary (children count, last updated)
```

### 9. Base Entity (`entity.py`)
```python
class FireflyBaseEntity(CoordinatorEntity):
    """Base entity for all Firefly entities."""

    def __init__(self, coordinator, config_entry, child_guid, base_name):
        super().__init__(coordinator)
        self._child_guid = child_guid
        # Set up device info, entity naming, and availability

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self._get_child_data() is not None

    def _get_child_data(self) -> Optional[Dict[str, Any]]:
        """Get data for this specific child."""
```

### 10. Error Handling (`exceptions.py`)
```python
class FireflyException(HomeAssistantError):
    """Base exception for Firefly integration."""

class FireflyAuthenticationError(FireflyException):
    """Authentication failed."""
    
class FireflyConnectionError(FireflyException):  
    """Connection to Firefly failed."""
    
class FireflyRateLimitError(FireflyException):
    """Rate limit exceeded."""
```

## Data Models

### Configuration Data
```python
@dataclass
class FireflyConfigData:
    host: str
    device_id: str
    secret: str
    user_guid: str
    children_guids: list[str]
    school_name: str
```

### Event Data Structure
```python
@dataclass
class FireflyEvent:
    start: datetime
    end: datetime
    subject: str
    location: str | None
    description: str | None
    attendees: list[dict]
```

### Task Data Structure  
```python
@dataclass
class FireflyTask:
    id: str
    title: str
    description: str
    due_date: datetime
    set_date: datetime
    subject: str
    task_type: str  # homework, project, test, etc.
    completion_status: str
    setter: str
```

## Authentication Implementation

### Device Registration Flow
1. Generate UUID4 device ID
2. Build authentication URL with device ID
3. Redirect user to Firefly login page
4. User logs in and is redirected back with token
5. Parse token XML response to extract secret and user info
6. Store device ID, secret, and user GUID in config entry

### Token Management
- Store device ID and secret in encrypted config storage
- Implement token refresh mechanism
- Handle authentication failures gracefully
- Support manual reauthentication through UI

## Platform Implementation Details

### Upcoming Tasks Sensor
- **Entity ID**: `sensor.firefly_upcoming_tasks_[child_name]`
- **State**: Number of tasks due in configured lookahead period (default: 7 days)
- **Attributes**:
  - `tasks`: List of task objects with title, subject, due_date, days_until_due, setter
  - `overdue_count`: Number of overdue tasks
  - `overdue_tasks`: List of overdue tasks with days_overdue
  - `last_updated`: Last coordinator update timestamp
  - `child_guid`: Child's unique identifier

### Tasks Due Today Sensor
- **Entity ID**: `sensor.firefly_tasks_due_today_[child_name]`
- **State**: Number of tasks due today
- **Attributes**:
  - `tasks`: List of today's tasks with title, subject, setter, description (truncated to 100 chars)
  - `last_updated`: Last coordinator update timestamp
  - `child_guid`: Child's unique identifier

### Overdue Tasks Sensor
- **Entity ID**: `sensor.firefly_overdue_tasks_[child_name]`
- **State**: Number of overdue tasks
- **Attributes**:
  - `tasks`: List of overdue tasks with title, subject, due_date, days_overdue, setter, description
  - `last_updated`: Last coordinator update timestamp
  - `child_guid`: Child's unique identifier

### Current Class Sensor
- **Entity ID**: `sensor.firefly_current_class_[child_name]`
- **State**: Current class subject (with optional time prefix), or "None"
- **Attributes**:
  - `status`: "in_class" or "no_current_class"
  - `class_name`: Subject name (when in class)
  - `location`: Classroom location (when in class)
  - `start_time`: Class start time ISO format (when in class)
  - `end_time`: Class end time ISO format (when in class)
  - `minutes_remaining`: Time remaining in current class (when in class)
  - `description`: Additional event details (when in class)
  - `current_time`: Current timestamp for debugging

### Next Class Sensor
- **Entity ID**: `sensor.firefly_next_class_[child_name]`
- **State**: Next class subject (with optional time prefix), or "None"
- **Attributes**:
  - `status`: "class_scheduled", "last_class_of_day", or "no_upcoming_class"
  - `class_name`: Subject name (when scheduled)
  - `location`: Classroom location (when scheduled)
  - `start_time`: Class start time ISO format (when scheduled)
  - `end_time`: Class end time ISO format (when scheduled)
  - `minutes_until`: Time until class starts (when scheduled)
  - `description`: Additional event details (when scheduled)
  - `context`: "next_class_today", "last_class_of_day", or "next_class_future_day"
  - `current_time`: Current timestamp for debugging

### Calendar Platform
- **Entity ID**: `calendar.firefly_[child_name]`
- **Features**: Read-only calendar showing school schedule events
- **Event Properties**: Start/end times, subject as summary, location, description with class and attendee info

### Todo Platform
- **Entity ID**: `todo.firefly_[child_name]`
- **Features**: Read-only todo list showing all tasks (upcoming, due today, overdue)
- **Item Properties**: Task title, due date, completion status, description with setter and task type
- **Deduplication**: Tasks appearing in multiple categories are deduplicated by task ID

## Configuration Options

### Integration Configuration
- School code (required)
- Update interval (15-60 minutes, default: 15)
- Task lookahead days (1-30 days, default: 7)
- Children to monitor (auto-discovered from account)

### Per-Child Options
- Show class times in sensor state (on/off, default: on)
  - When enabled: "9.00-10.00: Mathematics"
  - When disabled: "Mathematics"

## Testing Strategy

### Unit Tests (Target: >95% Coverage - **Currently: 96%**)
- **API Client Tests** (`test_api.py`): Mock HTTP responses, test error handling, authentication flow
- **Coordinator Tests** (`test_coordinator.py`): Mock API calls, test update logic, statistics tracking, issue registry
- **Config Flow Tests** (`test_config_flow.py`): Test all authentication steps, reauthentication, options flow
- **Sensor Tests** (`test_sensor.py`): Test state and attribute calculation for all 5 sensor types
- **Calendar Tests** (`test_calendar.py`): Test event listing and current/next event logic
- **Todo Tests** (`test_todo.py`): Test task deduplication and status mapping
- **Diagnostics Tests** (`test_diagnostics.py`): Test data redaction and statistics exposure
- **Error Handling Tests**: Test all exception scenarios across all modules

### Version Compatibility
- **Test Helper** (`conftest.py`): `create_config_entry_with_version_compat()` for HA 2024.x and 2025.x
- **Runtime Inspection**: Uses `inspect.signature()` to adapt to parameter changes across HA versions
- **Documentation**: See [testing.md](./testing.md) for comprehensive version compatibility guide

### Test Fixtures
- **Shared Fixtures** (`conftest.py`): Mock config entries, school info, user info, events, tasks, API responses
- **Mock Helpers**: `mock_http_response()`, `mock_aiohttp_session()` for HTTP testing
- **Version Compatibility**: Handles `subentries_data` and `discovery_keys` parameter differences

## Error Handling & Logging

### Network Errors
- Connection timeouts: Exponential backoff retry
- Rate limiting: Respect rate limits with appropriate delays
- Server errors: Log and mark entities unavailable

### Authentication Errors
- Invalid credentials: Trigger reauthentication flow
- Expired tokens: Automatic token refresh
- Device not recognized: Re-register device

### Data Errors
- Malformed responses: Log warnings, use cached data
- Missing expected fields: Graceful degradation
- API changes: Version detection and adaptation
- Consecutive errors: Issue registry notifications after 3 consecutive failures

### Issue Registry Integration
- **Connection Errors**: Created after 3 consecutive failures, dismissed on success
- **Data Format Errors**: Created after 5 consecutive errors, dismissed on success
- **Authentication Errors**: Created immediately, requires user reauthentication
- **Smart Thresholds**: Prevents notification spam from transient failures

### Logging Strategy
- Info level: Successful updates, authentication events, integration setup/unload
- Warning level: Recoverable errors, fallback data usage, credential validation failures
- Error level: Authentication failures, unrecoverable errors, connection failures
- Debug level: API request/response details (sanitized), coordinator state changes

## Security Considerations

### Credential Storage
- Device secrets stored in Home Assistant's encrypted storage
- No plaintext passwords stored anywhere
- User tokens have limited scope (student data only)

### Data Privacy  
- No personal data logged in plaintext
- API requests sanitized in debug logs
- Support for data export/deletion

### Network Security
- HTTPS-only communication with Firefly servers
- Certificate validation enforced
- No insecure fallbacks

## Performance Optimization

### Caching Strategy
- Cache API responses for 15 minutes
- Incremental updates where supported by API
- Efficient data structures for large datasets

### Resource Management
- Single aiohttp session per integration instance
- Connection pooling and keep-alive
- Proper session cleanup on unload

### Rate Limiting
- Respect Firefly API rate limits
- Implement client-side rate limiting
- Exponential backoff on rate limit errors

## Implemented Features Beyond Original Spec

### Additional Platforms
- ✅ **Calendar Platform**: School events as calendar entities
- ✅ **Todo Platform**: Tasks as interactive todo items (read-only)
- ✅ **Diagnostics Platform**: Downloadable diagnostic data for troubleshooting

### Enhanced Error Handling
- ✅ **Issue Registry Integration**: User-visible error notifications in Settings > System > Repairs
- ✅ **Statistics Tracking**: Comprehensive update statistics for diagnostics
- ✅ **Smart Error Thresholds**: Prevents notification spam from transient failures

### Quality Improvements
- ✅ **Pre-commit Hooks**: Automated code quality checks (black, isort, flake8, mypy)
- ✅ **Version Compatibility**: Test helpers for HA 2024.x and 2025.x compatibility
- ✅ **Comprehensive Documentation**: Testing guide, API docs, specifications

### Future Extensibility

#### Potential Enhancements
- Smart notifications through Home Assistant speakers or mobile
- Automation integration for home routines (e.g., "when school ends, announce homework")
- Multi-school support for families with children at different schools
- Additional data sources (grades, attendance, announcements)
- Task completion tracking (if Firefly API supports write operations)

#### API Evolution Support
- Version detection and compatibility checking (implemented)
- Graceful handling of API changes (implemented)
- Configuration migration support (implemented in `async_migrate_entry`)

## Dependencies

### Required Home Assistant Components
- `aiohttp` (HTTP client)
- `voluptuous` (configuration validation)
- Core integration components

### External Dependencies
```python
# requirements.txt
aiohttp>=3.8.0
lxml>=4.9.0  # XML parsing for auth responses
python-dateutil>=2.8.0  # Date parsing
```

## Installation & Deployment

### HACS Installation
- Custom repository support
- Automatic updates via HACS
- Version compatibility checking

### Manual Installation
- Copy files to `custom_components/firefly_cloud/`
- Restart Home Assistant
- Add integration through UI

## Documentation Requirements (Silver Tier)

### Integration Documentation
- Complete setup instructions
- Authentication troubleshooting guide
- Sensor reference documentation
- Configuration options reference
- FAQ and common issues

### Developer Documentation  
- API client usage examples
- Extension point documentation
- Contribution guidelines
- Testing instructions

This technical specification provides a comprehensive blueprint for implementing a Silver-tier Home Assistant integration for Firefly Cloud, ensuring high code quality, robust error handling, and excellent user experience.
