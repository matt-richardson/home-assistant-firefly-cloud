# Home Assistant Firefly Cloud Integration

A Home Assistant custom integration that connects to Firefly Cloud (school learning platform) to display children's school schedules and upcoming tasks on your smart home dashboard.

## Features

- **Today's Schedule**: View current day's classes with times, subjects, and locations
- **Weekly Schedule**: See upcoming classes for the week with special requirements (sports kit, equipment)
- **Upcoming Tasks**: Monitor homework, projects, and assignments with due dates
- **Multi-Child Support**: Family dashboard view or individual child dashboards
- **Time-Aware Display**: Different information priorities for morning prep, afternoon homework, and evening check-ins

## Installation

### HACS (Recommended)
1. Add this repository as a custom repository in HACS
2. Install the Firefly Cloud integration
3. Restart Home Assistant
4. Add the integration through Settings > Devices & Services

### Manual Installation
1. Copy the `custom_components/firefly_cloud/` folder to your Home Assistant `custom_components/` directory
2. Restart Home Assistant
3. Add the integration through Settings > Devices & Services

## Configuration

1. In Home Assistant, go to Settings > Devices & Services
2. Click "Add Integration" and search for "Firefly Cloud"
3. Enter your school's Firefly code
4. Follow the browser authentication flow to log into Firefly
5. The integration will automatically discover your children and create sensors

## Sensors Created

For each child, the integration creates:
- `sensor.firefly_today_schedule_[child_name]` - Today's classes
- `sensor.firefly_week_schedule_[child_name]` - This week's schedule  
- `sensor.firefly_upcoming_tasks_[child_name]` - Tasks due in configured timeframe
- `sensor.firefly_tasks_due_today_[child_name]` - Tasks due today

## Dashboard Usage

The sensors provide rich attributes perfect for Home Assistant dashboard cards:
- Class schedules with times and special requirements
- Task lists grouped by subject and due date
- Overdue task notifications
- Sports uniform and equipment reminders

## Target Quality

This integration is designed to meet Home Assistant's Silver-tier quality standards, including:
- Comprehensive test coverage (>95%)
- Proper error handling and recovery
- UI-based reauthentication
- Modern Python async implementation

## Support

For issues, feature requests, or questions, please use the GitHub Issues tab.

## Development

See `CLAUDE.md` for development guidance and `firefly-cloud-technical-spec.md` for detailed technical specifications.