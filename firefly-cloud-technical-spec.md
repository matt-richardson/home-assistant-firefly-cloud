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
├── __init__.py              # Integration setup and coordinator
├── config_flow.py           # Configuration flow and reauthentication  
├── const.py                 # Constants and configuration
├── coordinator.py           # Data update coordinator
├── sensor.py                # Sensor platform implementation
├── api.py                   # Firefly API client wrapper
├── exceptions.py            # Custom exception classes
├── manifest.json            # Integration manifest
└── strings.json             # Localization strings

tests/
├── __init__.py
├── conftest.py              # Test configuration and fixtures
├── test_init.py             # Integration setup tests
├── test_config_flow.py      # Config flow tests
├── test_coordinator.py      # Coordinator tests
├── test_sensor.py           # Sensor tests
├── test_api.py              # API client tests
└── fixtures/                # Test data fixtures
    ├── firefly_responses.json
    └── mock_data.py
```

### Data Flow
1. **Authentication**: OAuth-like flow via browser redirect to Firefly login
2. **Data Fetching**: Coordinator polls Firefly API every 15 minutes
3. **Entity Updates**: Sensors receive data through coordinator callbacks
4. **Error Handling**: Automatic retry with exponential backoff, reauthentication on token expiry

## Technical Implementation

### 1. Integration Entry Point (`__init__.py`)
```python
PLATFORMS = ["sensor"]
SCAN_INTERVAL = timedelta(minutes=15)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Firefly Cloud from a config entry."""
    
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
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
    def __init__(self, hass: HomeAssistant, api: FireflyAPIClient):
        super().__init__(
            hass,
            _LOGGER,
            name="Firefly Cloud",
            update_interval=timedelta(minutes=15),
        )
        
    async def _async_update_data(self) -> dict:
        """Fetch data from Firefly API."""
        # Fetch events and tasks
        # Handle rate limiting and errors
        # Return structured data for sensors
```

### 5. Sensor Platform (`sensor.py`)
**Sensor Types**:
- `firefly_today_schedule` - Today's class schedule
- `firefly_week_schedule` - This week's schedule  
- `firefly_upcoming_tasks` - Tasks due in next N days
- `firefly_tasks_due_today` - Tasks due today

**Sensor Base Class**:
```python
class FireflyBaseSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, sensor_type, child_guid=None):
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name="Firefly Cloud",
            manufacturer="Firefly Learning",
        )
        
    @property
    def available(self) -> bool:
        """Return if sensor is available."""
        return self.coordinator.last_update_success
        
    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
```

### 6. Error Handling (`exceptions.py`)
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

## Sensor Implementation Details

### Today's Schedule Sensor
- **Entity ID**: `sensor.firefly_today_schedule_[child_name]`
- **State**: Number of classes today
- **Attributes**: 
  - `classes`: List of class objects with time, subject, location
  - `special_requirements`: Sports kit, equipment needed
  - `next_class`: Upcoming class info

### Weekly Schedule Sensor  
- **Entity ID**: `sensor.firefly_week_schedule_[child_name]`
- **State**: Number of classes this week
- **Attributes**:
  - `schedule_by_day`: Dict of day -> classes
  - `special_days`: Days requiring special equipment

### Upcoming Tasks Sensor
- **Entity ID**: `sensor.firefly_upcoming_tasks_[child_name]` 
- **State**: Number of tasks due in configured timeframe
- **Attributes**:
  - `tasks`: List of task objects
  - `tasks_by_subject`: Tasks grouped by subject
  - `tasks_by_due_date`: Tasks grouped by due date
  - `overdue_tasks`: Past due tasks

### Tasks Due Today Sensor
- **Entity ID**: `sensor.firefly_tasks_due_today_[child_name]`
- **State**: Number of tasks due today
- **Attributes**:
  - `tasks`: List of today's tasks
  - `urgent_tasks`: High priority tasks

## Configuration Options

### Integration Configuration
- School code (required)
- Update interval (15-60 minutes, default: 15)
- Task lookahead days (1-30 days, default: 7)
- Children to monitor (auto-discovered from account)

### Per-Child Options
- Display name override
- Enable/disable specific sensors
- Custom task filtering rules

## Testing Strategy

### Unit Tests (Target: >95% Coverage)
- **API Client Tests**: Mock HTTP responses, test error handling
- **Coordinator Tests**: Mock API calls, test update logic
- **Config Flow Tests**: Test all authentication steps
- **Sensor Tests**: Test state and attribute calculation
- **Error Handling Tests**: Test all exception scenarios

### Integration Tests
- **Authentication Flow**: End-to-end auth testing with mock server
- **Data Fetching**: Test complete data flow from API to sensors
- **Error Recovery**: Test reconnection and reauthentication

### Test Fixtures
- Sample API responses (anonymized real data)
- Mock authentication tokens
- Various error scenarios

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

### Logging Strategy
- Info level: Successful updates, authentication events
- Warning level: Recoverable errors, fallback data usage  
- Error level: Authentication failures, unrecoverable errors
- Debug level: API request/response details (sanitized)

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

## Future Extensibility

### Planned Features
- Calendar integration (events as calendar entities)
- Notification support for urgent tasks
- Multi-school support for families
- Task completion tracking

### API Evolution Support
- Version detection and compatibility checking
- Graceful handling of API changes
- Configuration migration support

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