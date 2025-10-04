# Changelog

All notable changes to this project will be documented in this file. See [Conventional Commits](https://conventionalcommits.org) for commit guidelines.

## [0.3.1](https://github.com/matt-richardson/home-assistant-firefly-cloud/compare/v0.3.0...v0.3.1) (2025-10-04)


### Bug Fixes

* show time prefix on now/next class sensors in local time ([177b573](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/177b57359df97bbd22393525d61b33711a05d8a0))

## [0.3.0](https://github.com/matt-richardson/home-assistant-firefly-cloud/compare/v0.2.0...v0.3.0) (2025-10-04)


### Features

* add translations and improve options dialog UI ([eecb198](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/eecb1984300e8866a58d08e9bba391a57d1ed99c))

## [0.2.0](https://github.com/matt-richardson/home-assistant-firefly-cloud/compare/v0.1.2...v0.2.0) (2025-10-04)


### Features

* add optional time prefix for current and next class sensors ([d924ab6](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/d924ab6bb8efb8038873bb29d8777f0dcfde439e))
* support multi-week timetable fetching for 30-day calendar range ([f5d9500](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/f5d9500c3fb59589d8ce0a5f34a1fff085ad09a7))


### Bug Fixes

* ensure PNG icons are available for Home Assistant UI ([aaa8a4f](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/aaa8a4f98e9fb4899c4a9796e9e4876055bc0958))

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
