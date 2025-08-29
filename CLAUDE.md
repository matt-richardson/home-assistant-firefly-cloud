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

Always commit to git after a change is made.