# Changelog

All notable changes to this project will be documented in this file. See [Conventional Commits](https://conventionalcommits.org) for commit guidelines.

## [0.6.1](https://github.com/matt-richardson/home-assistant-firefly-cloud/compare/v0.6.0...v0.6.1) (2026-01-06)


### Bug Fixes

* resolve Python 3.13 CI failures with version-specific dependencies ([#29](https://github.com/matt-richardson/home-assistant-firefly-cloud/issues/29)) ([52f8163](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/52f8163e4dd9848cfbcd4cef7602af0b3304c6dc))
* trigger reauthentication flow on token expiration ([#28](https://github.com/matt-richardson/home-assistant-firefly-cloud/issues/28)) ([89aa481](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/89aa4816758a93fb99f0475e6dda03f38b792338))

## [0.6.0](https://github.com/matt-richardson/home-assistant-firefly-cloud/compare/v0.5.0...v0.6.0) (2025-12-01)


### Features

* add statistics tracking and diagnostics platform ([#22](https://github.com/matt-richardson/home-assistant-firefly-cloud/issues/22)) ([806eaa9](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/806eaa9a0fd4ec1e6cef7d83527417b839a8f1e3))

## [0.5.0](https://github.com/matt-richardson/home-assistant-firefly-cloud/compare/v0.4.2...v0.5.0) (2025-10-06)


### Features

* removed of guessed task attributes ([#20](https://github.com/matt-richardson/home-assistant-firefly-cloud/issues/20)) ([a644657](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/a6446578b8b44055a1d849e63c074ee872d7cdc3))

## [0.4.2](https://github.com/matt-richardson/home-assistant-firefly-cloud/compare/v0.4.1...v0.4.2) (2025-10-05)


### Bug Fixes

* dont prefix sensors with school name ([#13](https://github.com/matt-richardson/home-assistant-firefly-cloud/issues/13)) ([3746d8f](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/3746d8f35bbfd8377fd90a0a9e478b9fb239e75c))
* use local time for overdue tasks ([#12](https://github.com/matt-richardson/home-assistant-firefly-cloud/issues/12)) ([e3aaf3b](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/e3aaf3b5dc39df0f1c27b584f1632797e910eb3c))

## [0.4.1](https://github.com/matt-richardson/home-assistant-firefly-cloud/compare/v0.4.0...v0.4.1) (2025-10-05)


### Bug Fixes

* fix mypy linting failure ([#7](https://github.com/matt-richardson/home-assistant-firefly-cloud/issues/7)) ([c9a3391](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/c9a3391f6f600cf165eb2db3717d8fb242c7236d))

## [0.4.0](https://github.com/matt-richardson/home-assistant-firefly-cloud/compare/v0.3.1...v0.4.0) (2025-10-05)


### Features

* add overdue tasks sensor ([3c9a630](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/3c9a630191ad5bcf7ab0a47c2f8c04cba6f057b5))


### Bug Fixes

* fix flake8 lining ([907be0e](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/907be0e42263e01070ff668a2b0cd82e79eebee0))
* fix python 3.11 / 2024.x issues ([8e1cd0f](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/8e1cd0f8945f374fa0fa73195f0f83146119bf43))
* fix tests ([9dda1b9](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/9dda1b92d886c9de80670f9aa9966bb1799285ec))
* fix tests for python 3.11 ([d57a90c](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/d57a90c225bb06bb14ef7ca11b8d9f4710ada775))
* fix version compat - subentries_data is required ([aa6bbcc](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/aa6bbcc165559c7da1a6f142673812fbe30ebea3))
* Remove `icon` key - not supported ([5b4c032](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/5b4c032adf77dd408764d4975296bf66708173da))
* Remove `platforms` key - not supported ([3c3490c](https://github.com/matt-richardson/home-assistant-firefly-cloud/commit/3c3490c2b43ad9ba356708bd151ea4340935c875))

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
