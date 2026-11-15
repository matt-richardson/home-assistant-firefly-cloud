"""Constants for the Firefly Cloud integration."""

from datetime import timedelta
from typing import TypedDict

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
CONF_SHOW_CLASS_TIMES = "show_class_times"

# Defaults
DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)
DEFAULT_TASK_LOOKAHEAD_DAYS = 7

# Websocket command for the dashboard cards
WS_TYPE_CHILD_OVERVIEW = f"{DOMAIN}/child_overview"

# Dashboard cards, served by the integration
FRONTEND_URL_BASE = "/firefly_cloud_frontend"
CARD_FILENAME = "firefly-cards.js"
DEFAULT_SHOW_CLASS_TIMES = False
DEFAULT_APP_ID = "Home Assistant Firefly Cloud Integration"

# API endpoints
FIREFLY_APP_GATEWAY = "https://appgateway.fireflysolutions.co.uk/appgateway/school/"
FIREFLY_API_VERSION_PATH = "/login/api/version"
FIREFLY_VERIFY_TOKEN_PATH = "/Login/api/verifytoken"
FIREFLY_GRAPHQL_PATH = "/_api/1.0/graphql"
FIREFLY_TASK_LISTING_PATH = "/api/v2/taskListing/view/parent/tasks/all/filterBy"

# Sensor types
SENSOR_UPCOMING_TASKS = "upcoming_tasks"
SENSOR_TASKS_DUE_TODAY = "tasks_due_today"
SENSOR_OVERDUE_TASKS = "overdue_tasks"
SENSOR_CURRENT_CLASS = "current_class"
SENSOR_NEXT_CLASS = "next_class"


class SensorConfig(TypedDict):
    """Type definition for sensor configuration."""

    name: str
    icon: str
    unit: str | None
    device_class: str | None


# Sensor configurations
SENSOR_TYPES: dict[str, SensorConfig] = {
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
    SENSOR_OVERDUE_TASKS: {
        "name": "Overdue Tasks",
        "icon": "mdi:alert-circle",
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

# Task owner types
TASK_OWNER_ONLY_SETTERS = "OnlySetters"

# Task archive statuses
TASK_ARCHIVE_ALL = "All"

# Error retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # Exponential backoff base in seconds
TIMEOUT_SECONDS = 30
