# Changelog

All notable changes to this project will be documented in this file. See [Conventional Commits](https://conventionalcommits.org) for commit guidelines.

## [0.1.2](https://github.com/matt-richardson/home-assistant-firefly-cloud/compare/v0.1.1...v0.1.2) (2025-10-03)


### Bug Fixes

* change current class sensor to display "None" instead of "unknown" ([5e2f256](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/5e2f256524c0ef8a45e2e693249501c72737758e))

## [Unreleased]

### Added
- Current class sensor - shows actively running classes/lessons
- Next class sensor - shows upcoming scheduled classes/lessons
- Real-time school schedule tracking
- HACS compatibility and metadata
- GitHub release workflow
- Changelog for version tracking

### Fixed
- Code quality improvements and linting fixes

## [0.1.1] - 2024-09-06

### Added
- Calendar platform for school events
- Todo platform for task management
- Sensor entities for upcoming tasks and tasks due today
- Multi-child support for family dashboards
- Comprehensive test coverage (>95%)

### Fixed
- Various bug fixes and stability improvements

## [0.1.0] - 2024-09-05

### Added
- Initial release
- Firefly Cloud integration for Home Assistant
- Authentication flow via browser redirect
- API client for Firefly's GraphQL and REST endpoints
- Data coordinator with 15-minute polling interval
- Configuration flow with school code lookup
