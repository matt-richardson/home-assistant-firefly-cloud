"""Data update coordinator for Firefly Cloud integration."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FireflyAPIClient
from .const import DEFAULT_SCAN_INTERVAL, DEFAULT_TASK_LOOKAHEAD_DAYS, DOMAIN
from .exceptions import (
    FireflyAuthenticationError,
    FireflyConnectionError,
    FireflyDataError,
    FireflyRateLimitError,
    FireflyTokenExpiredError,
)

_LOGGER = logging.getLogger(__name__)


class FireflyUpdateCoordinator(DataUpdateCoordinator):  # pylint: disable=too-many-instance-attributes
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

        # Failure tracking for issue registry
        self.consecutive_failures = 0
        self.consecutive_data_errors = 0

        # Statistics tracking
        self.statistics: Dict[str, Any] = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "last_update_time": None,
            "last_success_time": None,
            "last_failure_time": None,
            "error_counts": {},  # Track errors by type
        }

    async def _async_update_data(self) -> Dict[str, Any]:  # pylint: disable=too-many-statements
        """Fetch data from Firefly API."""
        update_time = datetime.now(timezone.utc).isoformat()
        self.statistics["total_updates"] += 1
        self.statistics["last_update_time"] = update_time

        try:
            await self._ensure_user_and_children_info()

            # Calculate date ranges and fetch data
            from .const import get_offset_time

            now = get_offset_time()
            date_ranges = self._calculate_date_ranges(now)
            # _ensure_user_and_children_info guarantees _user_info is not None
            assert self._user_info is not None
            target_guids = self.children_guids if self.children_guids else [self._user_info["guid"]]

            # Fetch data for all children
            children_data = await self._fetch_all_children_data(target_guids, date_ranges, now)

            # Build response data
            data = {
                "user_info": self._user_info,
                "children_guids": target_guids,
                "children_data": children_data,
                "last_updated": now,
            }

            self._log_update_statistics(target_guids, children_data)

            # Update succeeded - reset counters and dismiss issues
            self._handle_update_success(update_time)

            return data

        except FireflyTokenExpiredError as err:
            self._track_failure("FireflyTokenExpiredError")
            _LOGGER.warning("Firefly authentication token expired, reauthentication required")
            # Token expired - immediate notification
            self._create_issue(
                "authentication_error",
                "authentication_error",
                severity=ir.IssueSeverity.ERROR,
            )
            raise ConfigEntryAuthFailed("Authentication token expired") from err
        except FireflyAuthenticationError as err:
            self._track_failure("FireflyAuthenticationError")
            _LOGGER.error("Firefly authentication error: %s", err)
            # Authentication error - immediate notification
            self._create_issue(
                "authentication_error",
                "authentication_error",
                severity=ir.IssueSeverity.ERROR,
            )
            raise ConfigEntryAuthFailed(f"Authentication error: {err}") from err
        except FireflyConnectionError as err:
            self._track_failure("FireflyConnectionError")
            self.consecutive_failures += 1
            _LOGGER.warning(
                "Connection error while updating Firefly data: %s (failure %d)", err, self.consecutive_failures
            )

            # Only notify after 3 consecutive failures
            if self.consecutive_failures >= 3:
                self._create_issue(
                    "connection_error",
                    "connection_error",
                    severity=ir.IssueSeverity.WARNING,
                    translation_placeholders={"consecutive_failures": str(self.consecutive_failures)},
                )

            raise UpdateFailed(f"Connection error: {err}") from err
        except FireflyRateLimitError as err:
            self._track_failure("FireflyRateLimitError")
            _LOGGER.warning("Rate limit error while updating Firefly data: %s", err)
            # Rate limit - immediate notification with interval suggestion
            update_interval_minutes = int(DEFAULT_SCAN_INTERVAL.total_seconds() / 60) + 5
            self._create_issue(
                "rate_limit_error",
                "rate_limit_error",
                severity=ir.IssueSeverity.WARNING,
                translation_placeholders={"update_interval": str(update_interval_minutes)},
            )
            raise UpdateFailed("Rate limit exceeded") from err
        except FireflyDataError as err:
            self._track_failure("FireflyDataError")
            self.consecutive_data_errors += 1
            _LOGGER.error("Data processing error: %s (error %d)", err, self.consecutive_data_errors)

            # Only notify after 2 consecutive data errors
            if self.consecutive_data_errors >= 2:
                self._create_issue(
                    "data_error",
                    "data_error",
                    severity=ir.IssueSeverity.WARNING,
                    translation_placeholders={"error_message": str(err)},
                )

            raise UpdateFailed(f"Data processing error: {err}") from err
        except Exception as err:
            self._track_failure("UnexpectedError")
            self.consecutive_failures += 1
            _LOGGER.exception("Unexpected error updating Firefly data (failure %d)", self.consecutive_failures)

            # Only notify after 2 consecutive unexpected errors
            if self.consecutive_failures >= 2:
                self._create_issue(
                    "unexpected_error",
                    "unexpected_error",
                    severity=ir.IssueSeverity.ERROR,
                    translation_placeholders={"error_message": str(err)},
                )

            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _ensure_user_and_children_info(self) -> None:
        """Ensure user info and children info are fetched."""
        if not self._user_info:
            self._user_info = await self.api.get_user_info()

        if not self._children_info and self.children_guids:
            try:
                self._children_info = await self.api.get_children_info()
            except (FireflyConnectionError, FireflyAuthenticationError, FireflyTokenExpiredError) as err:
                _LOGGER.warning("Failed to fetch children info: %s", err)
                self._children_info = []

    def _calculate_date_ranges(self, now: datetime) -> Dict[str, datetime]:
        """Calculate date ranges for data fetching."""
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            "today_start": today_start,
            "today_end": today_start + timedelta(days=1),
            "week_start": today_start,
            "calendar_end": today_start + timedelta(days=30),
            "task_end": today_start + timedelta(days=self.task_lookahead_days),
        }

    async def _fetch_all_children_data(
        self, target_guids: List[str], date_ranges: Dict[str, datetime], now: datetime
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch data for all children."""
        children_data = {}

        for child_guid in target_guids:
            children_data[child_guid] = await self._fetch_child_data(child_guid, date_ranges, now)

        return children_data

    async def _fetch_child_data(
        self, child_guid: str, date_ranges: Dict[str, datetime], now: datetime
    ) -> Dict[str, Any]:
        """Fetch data for a single child."""
        events_today = await self.api.get_events(date_ranges["today_start"], date_ranges["today_end"], child_guid)
        events_calendar = await self.api.get_events(date_ranges["week_start"], date_ranges["calendar_end"], child_guid)
        tasks = await self.api.get_tasks(student_guid=child_guid)

        return {
            "events": {
                "today": self._process_events(events_today),
                "week": self._process_events(events_calendar),
            },
            "tasks": {
                "all": self._process_tasks(tasks),
                "due_today": self._filter_tasks_by_date(tasks, date_ranges["today_start"], date_ranges["today_end"]),
                "upcoming": self._filter_tasks_by_date(tasks, now, date_ranges["task_end"]),
                "overdue": self._filter_overdue_tasks(tasks, now),
            },
            "name": self._extract_child_name(child_guid),
        }

    def _log_update_statistics(self, target_guids: List[str], children_data: Dict[str, Dict[str, Any]]) -> None:
        """Log statistics about the update."""
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
        from .const import get_offset_time

        today = get_offset_time().replace(hour=0, minute=0, second=0, microsecond=0)
        if day_start == today:
            return self.data["events"]["today"]

        # For other days in the week, filter from week events
        week_events = self.data["events"]["week"]
        return [event for event in week_events if day_start <= event["start"] < day_end]

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

    def _create_issue(
        self,
        issue_id: str,
        translation_key: str,
        severity: ir.IssueSeverity = ir.IssueSeverity.ERROR,
        translation_placeholders: Optional[Dict[str, str]] = None,
    ) -> None:
        """Create or update an issue in the issue registry."""
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=severity,
            translation_key=translation_key,
            translation_placeholders=translation_placeholders or {},
        )

    def _dismiss_issue(self, issue_id: str) -> None:
        """Dismiss an issue from the issue registry."""
        ir.async_delete_issue(self.hass, DOMAIN, issue_id)

    def _handle_update_success(self, update_time: str) -> None:
        """Handle successful update."""
        self.consecutive_failures = 0
        self.consecutive_data_errors = 0

        # Update statistics
        self.statistics["successful_updates"] += 1
        self.statistics["last_success_time"] = update_time

        # Dismiss any existing issues
        self._dismiss_issue("connection_error")
        self._dismiss_issue("authentication_error")
        self._dismiss_issue("rate_limit_error")
        self._dismiss_issue("data_error")
        self._dismiss_issue("unexpected_error")

    def _track_failure(self, error_type: str) -> None:
        """Track update failure statistics."""
        self.statistics["failed_updates"] += 1
        self.statistics["last_failure_time"] = datetime.now(timezone.utc).isoformat()

        # Track error counts by type
        if error_type not in self.statistics["error_counts"]:
            self.statistics["error_counts"][error_type] = 0
        self.statistics["error_counts"][error_type] += 1
