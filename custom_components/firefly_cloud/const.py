"""Constants for the Firefly Cloud integration."""

import datetime
from datetime import timedelta

DOMAIN = "firefly_cloud"

# Configuration keys
CONF_SCHOOL_CODE = "school_code"
CONF_DEVICE_ID = "device_id"
CONF_SECRET = "secret"
CONF_USER_GUID = "user_guid"
CONF_CHILDREN_GUIDS = "children_guids"
CONF_SCHOOL_NAME = "school_name"
CONF_HOST = "host"
CONF_TASK_LOOKAHEAD_DAYS = "task_lookahead_days"

# Defaults
DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)
DEFAULT_TASK_LOOKAHEAD_DAYS = 7
DEFAULT_APP_ID = "Home Assistant Firefly Cloud Integration"

# API endpoints
FIREFLY_APP_GATEWAY = "https://appgateway.fireflysolutions.co.uk/appgateway/school/"
FIREFLY_LOGIN_PATH = "/Login/api"
FIREFLY_API_VERSION_PATH = "/login/api/version"
FIREFLY_VERIFY_TOKEN_PATH = "/Login/api/verifytoken"
FIREFLY_GRAPHQL_PATH = "/_api/1.0/graphql"
FIREFLY_TASK_API_PATH = "/api/v2/taskListing/view/student/tasks/all/filterBy"

# Sensor types
SENSOR_UPCOMING_TASKS = "upcoming_tasks"
SENSOR_TASKS_DUE_TODAY = "tasks_due_today"
SENSOR_CURRENT_CLASS = "current_class"
SENSOR_NEXT_CLASS = "next_class"

# Sensor configurations
SENSOR_TYPES = {
    SENSOR_UPCOMING_TASKS: {
        "name": "Upcoming Tasks",
        "icon": "mdi:clipboard-text",
        "unit": "tasks",
        "device_class": None,
    },
    SENSOR_TASKS_DUE_TODAY: {
        "name": "Tasks Due Today",
        "icon": "mdi:clipboard-alert",
        "unit": "tasks",
        "device_class": None,
    },
    SENSOR_CURRENT_CLASS: {
        "name": "Current Class",
        "icon": "mdi:school",
        "unit": None,
        "device_class": None,
    },
    SENSOR_NEXT_CLASS: {
        "name": "Next Class",
        "icon": "mdi:clock-outline",
        "unit": None,
        "device_class": None,
    },
}

# Task completion statuses
TASK_STATUS_TODO = "Todo"
TASK_STATUS_COMPLETED = "Completed"
TASK_STATUS_OVERDUE = "Overdue"

# Task owner types
TASK_OWNER_ONLY_SETTERS = "OnlySetters"

# Task archive statuses
TASK_ARCHIVE_ALL = "All"

# Task sorting
TASK_SORT_DUE_DATE_ASC = {"column": "DueDate", "order": "Ascending"}

# Error retry configuration
MAX_RETRIES = 3

# Time offset parameters for testing/debugging
# Set both to 0 for normal operation
# Negative values go back in time (useful for testing with historical data)
#
# Usage examples:
# TIME_OFFSET_DAYS = 0, TIME_OFFSET_HOURS = 0     # Normal operation
# TIME_OFFSET_DAYS = -6, TIME_OFFSET_HOURS = 0    # 6 days ago (testing with historical data)
# TIME_OFFSET_DAYS = -1, TIME_OFFSET_HOURS = -2   # Yesterday, 2 hours earlier
# TIME_OFFSET_DAYS = 0, TIME_OFFSET_HOURS = 3     # Today, 3 hours later
# TIME_OFFSET_DAYS = 1, TIME_OFFSET_HOURS = 0     # Tomorrow (same time)
#
TIME_OFFSET_DAYS = 0  # Days offset for testing (0 for normal operation)
TIME_OFFSET_HOURS = 0  # Additional hour offset (can be fractional)


def get_offset_time() -> "datetime.datetime":
    """Get current time with configured offset applied.

    Returns:
        datetime: Current UTC time with TIME_OFFSET_DAYS and TIME_OFFSET_HOURS applied.
    """
    from datetime import timedelta
    from homeassistant.util import dt as dt_util

    base_time = dt_util.now()

    if TIME_OFFSET_DAYS == 0 and TIME_OFFSET_HOURS == 0:
        return base_time

    offset = timedelta(days=TIME_OFFSET_DAYS, hours=TIME_OFFSET_HOURS)
    return base_time + offset


RETRY_DELAY_BASE = 2  # Exponential backoff base in seconds
TIMEOUT_SECONDS = 30

# Parallel updates
PARALLEL_UPDATES = 1
