"""Constants for the Firefly Cloud integration."""

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
RETRY_DELAY_BASE = 2  # Exponential backoff base in seconds
TIMEOUT_SECONDS = 30

# Parallel updates
PARALLEL_UPDATES = 1
