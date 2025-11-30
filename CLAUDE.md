# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Firefly Cloud (school learning platform). The integration displays children's school schedules and upcoming tasks on Home Assistant dashboards. Target quality level: Silver tier.

## Architecture

The integration follows Home Assistant's modern async architecture pattern:

- **API Layer** (`api.py`): Async HTTP client wrapping Firefly's GraphQL API and REST endpoints
- **Data Coordinator** (`coordinator.py`): Centralized data fetching with 15-minute polling interval
- **Config Flow** (`config_flow.py`): Multi-step authentication via browser redirect to Firefly login
- **Sensor Platform** (`sensor.py`): Five sensor types (upcoming tasks, tasks due today, overdue tasks, current class, next class)
- **Calendar Platform** (`calendar.py`): School events and tasks in Home Assistant calendar format
- **Todo Platform** (`todo.py`): Interactive todo list for managing school tasks
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
- **Tasks**: Homework/assignments with due dates, subjects, and types
- **Events**: School calendar events (via calendar platform)
- **Todo Items**: Interactive task management (via todo platform)
- **Multi-child support**: Family dashboard + individual child views

## Testing Strategy

Comprehensive mocking required for:
- Firefly API HTTP responses (use anonymized fixtures)
- Authentication token flows
- Config flow user interactions
- Coordinator update cycles
- Error scenarios (network failures, auth expiry, rate limiting)

Target test structure in `tests/` with fixtures in `tests/conftest.py`.

**For detailed testing guidance**, see [docs/testing.md](docs/testing.md) which covers:
- Running tests and coverage reports
- Version compatibility across Home Assistant versions
- Writing new tests with proper fixtures
- Common testing patterns and troubleshooting

## Development Workflow

Use `venv` when running tests
Always run tests before saying that a change is complete.
Always ask the user if they want commit to git after a change is complete.

### Commit Message Format

This project uses [Conventional Commits](https://conventionalcommits.org) for automated release management via release-please.

**Required format:**
```
<type>: <description>

[optional body]

[optional footer(s)]
```

**Common types:**
- `feat:` - New feature (triggers minor version bump)
- `fix:` - Bug fix (triggers patch version bump)
- `docs:` - Documentation changes
- `chore:` - Maintenance tasks, dependency updates
- `refactor:` - Code refactoring without functional changes
- `test:` - Test additions or modifications
- `ci:` - CI/CD configuration changes

**Examples:**
```
feat: add sensor for current class schedule
fix: resolve timezone handling for next class sensor
docs: update installation instructions
chore: update dependencies to latest versions
```

**Breaking changes:** Add `BREAKING CHANGE:` in the footer to trigger a major version bump.

### Release Process

Releases are automated via release-please:
1. Push conventional commits to `main` branch
2. Release-please creates/updates a release PR automatically
3. Merge the release PR to publish the release
4. Version bumps happen in both `manifest.json` and `CHANGELOG.md`

Do not manually edit version numbers - let release-please manage them.

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

After successful setup, verify these entities are created for each child:
- `sensor.firefly_upcoming_tasks_*` - Homework and assignments
- `sensor.firefly_tasks_due_today_*` - Today's due tasks
- `sensor.firefly_overdue_tasks_*` - Tasks past their due date
- `sensor.firefly_current_class_*` - Currently active class/lesson
- `sensor.firefly_next_class_*` - Next scheduled class/lesson
- `calendar.firefly_*` - School events and tasks in calendar format
- `todo.firefly_*` - Interactive todo list for school tasks

Check entity attributes contain structured data suitable for dashboard cards.
