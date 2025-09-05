# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Firefly Cloud (school learning platform). The integration displays children's school schedules and upcoming tasks on Home Assistant dashboards. Target quality level: Silver tier.

## Architecture

The integration follows Home Assistant's modern async architecture pattern:

- **API Layer** (`api.py`): Async HTTP client wrapping Firefly's GraphQL API and REST endpoints
- **Data Coordinator** (`coordinator.py`): Centralized data fetching with 15-minute polling interval
- **Config Flow** (`config_flow.py`): Multi-step authentication via browser redirect to Firefly login
- **Sensor Platform** (`sensor.py`): Four sensor types (today's schedule, weekly schedule, upcoming tasks, tasks due today)
- **Authentication Flow**: Device-based authentication using UUID device ID and secret token

## Reference Implementation

The Node.js reference implementation is located at `~/dev/public-repo-forks/FireflyAPI/Driver/firefly-api.js`. This contains the working authentication flow and API endpoints. Key elements to translate to Python async:
- School lookup via `appgateway.fireflysolutions.co.uk`
- Device registration and token extraction from XML responses
- GraphQL queries for events and tasks
- REST API for task filtering

## Quality Requirements

This integration targets Home Assistant Silver tier certification, requiring:
- >95% test coverage across all modules
- Config entry unloading support
- UI-based reauthentication
- Proper error handling and entity unavailable states
- Modern Python async patterns (3.11+)

See `firefly-cloud-technical-spec.md` for complete Bronze + Silver tier checklist.

## Data Models

Key entities the integration handles:
- **Events**: School classes with start/end times, subjects, locations
- **Tasks**: Homework/assignments with due dates, subjects, and types
- **Multi-child support**: Family dashboard + individual child views
- **Time-aware display**: Different information priorities for morning/afternoon/evening usage

## Testing Strategy

Comprehensive mocking required for:
- Firefly API HTTP responses (use anonymized fixtures)
- Authentication token flows
- Config flow user interactions
- Coordinator update cycles
- Error scenarios (network failures, auth expiry, rate limiting)

Target test structure in `tests/` with fixtures in `tests/fixtures/`.

## Development Workflow

Use `venv` when running tests
Always run tests before saying that a change is complete.
Always ask the user if they want commit to git after a change is complete.

## Manual Testing Approach

### DevContainer Testing (Recommended)

The project includes a complete VS Code devcontainer setup for comprehensive manual testing:

**Setup:**
1. Open project in VS Code
2. Command Palette > "Dev Containers: Reopen in Container"
3. Wait for automatic setup completion

**Testing Commands:**
```bash
./dev.sh test-cov      # Unit tests with >95% coverage requirement
./dev.sh ha-test       # Start Home Assistant test instance on port 8123
./dev.sh validate      # Full validation suite (format + lint + test + config)
./dev.sh lint          # Run all linting tools (black, flake8, mypy, pylint)
```

**Manual Integration Testing:**
1. Run `./dev.sh ha-test` to start Home Assistant
2. Navigate to http://localhost:8123 in browser
3. Go to Settings > Devices & Services
4. Add Firefly Cloud integration
5. Complete authentication flow with real Firefly credentials
6. Verify sensors are created and updating with real data

**VS Code Integration:**
- Use Test Explorer to run/debug individual tests
- Set breakpoints in integration code for debugging
- Port 8123 automatically forwarded for Home Assistant access
- Code formatting on save with black/isort

### Error Scenario Testing

Test the following error conditions:
- Invalid school codes during setup
- Network connectivity failures
- Authentication token expiry and reauthentication
- API rate limiting responses
- Missing or malformed API responses

### Sensor Validation

After successful setup, verify these sensors are created for each child:
- `sensor.firefly_today_schedule_*` - Today's classes with times/locations
- `sensor.firefly_week_schedule_*` - Weekly view with equipment requirements
- `sensor.firefly_upcoming_tasks_*` - Homework and assignments
- `sensor.firefly_tasks_due_today_*` - Today's due tasks

Check sensor attributes contain structured data suitable for dashboard cards.
