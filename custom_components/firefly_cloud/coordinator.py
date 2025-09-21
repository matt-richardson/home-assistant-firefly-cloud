"""Data update coordinator for Firefly Cloud integration."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FireflyAPIClient
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TASK_LOOKAHEAD_DAYS,
    DOMAIN,
)
from .exceptions import (
    FireflyAuthenticationError,
    FireflyConnectionError,
    FireflyRateLimitError,
    FireflyTokenExpiredError,
)

_LOGGER = logging.getLogger(__name__)


class FireflyUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Firefly data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: FireflyAPIClient,
        task_lookahead_days: int = DEFAULT_TASK_LOOKAHEAD_DAYS,
        children_guids: Optional[List[str]] = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.api = api
        self.task_lookahead_days = task_lookahead_days
        self.children_guids = children_guids or []
        self._user_info: Optional[Dict[str, Any]] = None
        self._children_info: Optional[List[Dict[str, Any]]] = None

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Firefly API."""
        try:
            # Get user info if we don't have it
            if not self._user_info:
                self._user_info = await self.api.get_user_info()

            # Get children info if we don't have it and we have children GUIDs
            if not self._children_info and self.children_guids:
                try:
                    self._children_info = await self.api.get_children_info()
                except (FireflyConnectionError, FireflyAuthenticationError, FireflyTokenExpiredError) as err:
                    _LOGGER.warning("Failed to fetch children info: %s", err)
                    self._children_info = []

            # Calculate date ranges (timezone-aware)
            from .const import get_offset_time

            now = get_offset_time()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            week_start = today_start
            # Extended range for calendar view (30 days)
            calendar_end = today_start + timedelta(days=30)
            task_end = today_start + timedelta(days=self.task_lookahead_days)

            # Determine which users to fetch data for
            target_guids = self.children_guids if self.children_guids else [self._user_info["guid"]]

            # Initialize data structure for multi-child support
            children_data = {}

            # Fetch data for each child/user
            for child_guid in target_guids:

                # Fetch data in parallel for this child
                events_today = await self.api.get_events(today_start, today_end, child_guid)
                events_calendar = await self.api.get_events(week_start, calendar_end, child_guid)
                tasks = await self.api.get_tasks(student_guid=child_guid)

                children_data[child_guid] = {
                    "events": {
                        "today": self._process_events(events_today),
                        "week": self._process_events(events_calendar),  # Use extended range for calendar
                    },
                    "tasks": {
                        "all": self._process_tasks(tasks),
                        "due_today": self._filter_tasks_by_date(tasks, today_start, today_end),
                        "upcoming": self._filter_tasks_by_date(tasks, now, task_end),
                        "overdue": self._filter_overdue_tasks(tasks, now),
                    },
                    "name": self._extract_child_name(child_guid),
                }

            # Process and organize the data
            data = {
                "user_info": self._user_info,
                "children_guids": target_guids,
                "children_data": children_data,
                "last_updated": now,
            }

            total_events_today = 0
            total_events_week = 0
            total_tasks = 0
            for child_data in children_data.values():
                if isinstance(child_data, dict):
                    events_data = child_data.get("events")
                    tasks_data = child_data.get("tasks")
                    if isinstance(events_data, dict):
                        total_events_today += len(events_data.get("today", []))
                        total_events_week += len(events_data.get("week", []))
                    if isinstance(tasks_data, dict):
                        total_tasks += len(tasks_data.get("all", []))

            _LOGGER.debug(
                "Successfully updated Firefly data for %d children: "
                "%d events today, %d events this week, %d total tasks",
                len(target_guids),
                total_events_today,
                total_events_week,
                total_tasks,
            )

            return data

        except FireflyTokenExpiredError as err:
            _LOGGER.warning("Firefly authentication token expired, reauthentication required")
            raise UpdateFailed("Authentication token expired") from err
        except FireflyAuthenticationError as err:
            _LOGGER.error("Firefly authentication error: %s", err)
            raise UpdateFailed(f"Authentication error: {err}") from err
        except FireflyConnectionError as err:
            _LOGGER.warning("Connection error while updating Firefly data: %s", err)
            raise UpdateFailed(f"Connection error: {err}") from err
        except FireflyRateLimitError as err:
            _LOGGER.warning("Rate limit error while updating Firefly data: %s", err)
            raise UpdateFailed("Rate limit exceeded") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error updating Firefly data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _process_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and clean event data."""
        processed_events = []

        for event in events:
            try:
                processed_event = {
                    "start": datetime.fromisoformat(event["start"].replace("Z", "+00:00")),
                    "end": datetime.fromisoformat(event["end"].replace("Z", "+00:00")),
                    "subject": event.get("subject", "Unknown Subject"),
                    "location": event.get("location"),
                    "description": event.get("description"),
                    "guild": event.get("guild"),
                    "attendees": event.get("attendees", []),
                }
                processed_events.append(processed_event)
            except (ValueError, KeyError) as err:
                _LOGGER.warning("Error processing event data: %s", err)
                continue

        # Sort by start time
        processed_events.sort(key=lambda x: x["start"])
        return processed_events

    def _process_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and clean task data."""
        processed_tasks = []

        for task in tasks:
            try:
                due_date_str = task.get("dueDate")
                set_date_str = task.get("setDate")

                # Handle due date parsing with fallback for invalid dates
                due_date = None
                if due_date_str:
                    try:
                        due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        _LOGGER.debug("Invalid due date format: %s", due_date_str)
                        due_date = None

                # Handle set date parsing with fallback
                set_date = None
                if set_date_str:
                    try:
                        set_date = datetime.fromisoformat(set_date_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        _LOGGER.debug("Invalid set date format: %s", set_date_str)
                        set_date = None

                # Extract subject information
                subject = "Unknown Subject"
                if "subject" in task:
                    subject_data = task["subject"]
                    if isinstance(subject_data, dict):
                        subject = subject_data.get("name", "Unknown Subject")
                    elif isinstance(subject_data, str):
                        subject = subject_data

                processed_task = {
                    "id": task.get("guid", task.get("id", "unknown")),
                    "title": task.get("title", "Untitled Task"),
                    "description": task.get("description", ""),
                    "due_date": due_date,
                    "set_date": set_date,
                    "subject": subject,
                    "task_type": self._determine_task_type(task),
                    "completion_status": task.get("completionStatus", "Unknown"),
                    "setter": (
                        task.get("setter", {}).get("name", "Unknown")
                        if isinstance(task.get("setter"), dict)
                        else task.get("setter", "Unknown")
                    ),
                    "raw_data": task,  # Keep raw data for debugging
                }
                processed_tasks.append(processed_task)
            except (KeyError, TypeError) as err:
                _LOGGER.warning("Error processing task data: %s", err)
                continue

        return processed_tasks

    def _determine_task_type(self, task: Dict[str, Any]) -> str:
        """Determine task type from task data."""
        title = task.get("title", "").lower()
        description = task.get("description", "").lower()

        # Simple classification based on keywords
        if any(keyword in title for keyword in ["test", "exam", "assessment"]):
            return "test"
        if any(keyword in title for keyword in ["project", "assignment"]):
            return "project"
        if any(keyword in description for keyword in ["permission", "slip", "form"]):
            return "permission_slip"
        return "homework"

    def _filter_tasks_by_date(
        self, tasks: List[Dict[str, Any]], start: datetime, end: datetime
    ) -> List[Dict[str, Any]]:
        """Filter tasks by date range."""
        filtered_tasks = []

        # Ensure start and end are timezone-aware for comparison
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        for task in tasks:
            due_date_str = task.get("dueDate")
            if not due_date_str:
                continue

            try:
                # Parse the due date and ensure it's timezone-aware
                if due_date_str.endswith("Z"):
                    due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
                else:
                    # If no timezone info, parse as naive then add UTC timezone
                    due_date = datetime.fromisoformat(due_date_str)
                    if due_date.tzinfo is None:
                        due_date = due_date.replace(tzinfo=timezone.utc)

                if start <= due_date < end:
                    filtered_tasks.append(task)
            except ValueError:
                continue

        return self._process_tasks(filtered_tasks)

    def _filter_overdue_tasks(self, tasks: List[Dict[str, Any]], now: datetime) -> List[Dict[str, Any]]:
        """Filter overdue tasks."""
        overdue_tasks = []

        for task in tasks:
            due_date_str = task.get("dueDate")
            completion_status = task.get("completionStatus", "")

            if not due_date_str or completion_status.lower() == "completed":
                continue

            try:
                if due_date_str.endswith("Z"):
                    due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
                else:
                    # If no timezone info, parse as naive then add UTC timezone
                    due_date = datetime.fromisoformat(due_date_str)
                    if due_date.tzinfo is None:
                        due_date = due_date.replace(tzinfo=timezone.utc)

                # Ensure now is timezone-aware
                if now.tzinfo is None:
                    now = now.replace(tzinfo=timezone.utc)

                if due_date < now:
                    overdue_tasks.append(task)
            except ValueError:
                continue

        return self._process_tasks(overdue_tasks)

    def get_events_for_day(self, target_date: datetime) -> List[Dict[str, Any]]:
        """Get events for a specific day."""
        if not self.data or "events" not in self.data:
            return []

        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # For today, use the cached today events
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if day_start == today:
            return self.data["events"]["today"]

        # For other days in the week, filter from week events
        week_events = self.data["events"]["week"]
        return [event for event in week_events if day_start <= event["start"] < day_end]

    def get_tasks_by_subject(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group tasks by subject."""
        if not self.data or "tasks" not in self.data:
            return {}

        tasks_by_subject: Dict[str, List[Dict[str, Any]]] = {}
        for task in self.data["tasks"]["upcoming"]:
            subject = task["subject"]
            if subject not in tasks_by_subject:
                tasks_by_subject[subject] = []
            tasks_by_subject[subject].append(task)

        return tasks_by_subject

    def get_special_requirements_today(self) -> List[str]:
        """Get special requirements for today (sports kit, equipment, etc.)."""
        today_events = self.get_events_for_day(datetime.now())
        requirements = []

        for event in today_events:
            subject = event["subject"].lower()
            description = (event["description"] or "").lower()

            # Check for sports/PE requirements
            if any(keyword in subject for keyword in ["pe", "sport", "games", "physical"]):
                requirements.append("Sports kit required")

            # Check for equipment mentions in description
            if any(keyword in description for keyword in ["equipment", "kit", "uniform"]):
                requirements.append(f"Special equipment for {event['subject']}")

        return list(set(requirements))  # Remove duplicates

    def _extract_child_name(self, child_guid: str) -> Optional[str]:
        """Extract child name from user info or children info."""
        # Check if this is the main user account
        if self._user_info and child_guid == self._user_info.get("guid"):
            return self._user_info.get("name") or self._user_info.get("fullname") or self._user_info.get("username")

        # For children, look up their names from children info
        if self._children_info:
            for child in self._children_info:
                if child.get("guid") == child_guid:
                    return child.get("name") or child.get("fullname")

        # If this is the user GUID, try username fallback
        if self._user_info and child_guid == self._user_info.get("guid"):
            return self._user_info.get("username")

        # Final fallback to GUID
        return child_guid
