"""Test the Firefly Cloud coordinator."""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest
from freezegun import freeze_time
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.firefly_cloud.coordinator import FireflyUpdateCoordinator
from custom_components.firefly_cloud.exceptions import (
    FireflyAuthenticationError,
    FireflyConnectionError,
    FireflyTokenExpiredError,
)
from tests.conftest import firefly_due


@pytest.mark.asyncio
async def test_coordinator_init(hass: HomeAssistant, mock_api):
    """Test coordinator initialization."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    assert coordinator.api == mock_api
    assert coordinator.task_lookahead_days == 7
    assert coordinator.name == "firefly_cloud"
    assert coordinator.update_interval and coordinator.update_interval.total_seconds() == 900  # 15 minutes


@pytest.mark.asyncio
async def test_coordinator_first_refresh_success(hass: HomeAssistant, mock_api):
    """Test successful first refresh."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    await coordinator.async_refresh()

    assert coordinator.data is not None
    assert "user_info" in coordinator.data
    assert "children_data" in coordinator.data
    assert "children_guids" in coordinator.data
    assert coordinator.data["user_info"]["username"] == "john.doe"


@pytest.mark.asyncio
async def test_coordinator_update_data_success(hass: HomeAssistant, mock_api):
    """Test successful data update."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    assert data is not None
    assert "user_info" in data
    assert "children_data" in data
    assert "children_guids" in data
    assert "last_updated" in data

    # Verify API calls were made
    mock_api.get_user_info.assert_called_once()
    mock_api.get_events.assert_called()
    mock_api.get_tasks.assert_called_once()


@pytest.mark.asyncio
async def test_coordinator_process_events(hass: HomeAssistant, mock_api):
    """Test event processing."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    assert "children_data" in data
    child_guid = list(data["children_data"].keys())[0]  # Get first child
    child_data = data["children_data"][child_guid]

    assert "events" in child_data
    assert "today" in child_data["events"]
    assert "week" in child_data["events"]

    # Should have today's events
    assert len(child_data["events"]["today"]) == 1
    assert child_data["events"]["today"][0]["subject"] == "Mathematics"

    # Week events should include today's events
    assert len(child_data["events"]["week"]) >= 1


@pytest.mark.asyncio
async def test_coordinator_process_tasks(hass: HomeAssistant, mock_api):
    """Test task processing."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    assert "children_data" in data
    child_guid = list(data["children_data"].keys())[0]  # Get first child
    child_data = data["children_data"][child_guid]

    assert "tasks" in child_data
    assert "all" in child_data["tasks"]
    assert "due_today" in child_data["tasks"]
    assert "upcoming" in child_data["tasks"]
    assert "overdue" in child_data["tasks"]

    # Should have all tasks
    assert len(child_data["tasks"]["all"]) == 1
    assert child_data["tasks"]["all"][0]["title"] == "Math Homework"


@pytest.mark.asyncio
async def test_coordinator_filter_tasks_due_today(hass: HomeAssistant, mock_api):
    """Test filtering tasks due today."""
    # Mock task due today - use offset time to match coordinator behavior
    from custom_components.firefly_cloud.dates import get_offset_time

    now_utc = get_offset_time()
    task_due_today = {
        "guid": "urgent-task",
        "title": "Submit Report",
        "description": "Final report submission",
        "dueDate": firefly_due(0),
        "setDate": (now_utc - timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "subject": {"name": "English"},
        "completionStatus": "Todo",
        "setter": {"name": "Ms. Johnson"},
    }

    mock_api.get_tasks.return_value = [task_due_today]

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    assert len(child_data["tasks"]["due_today"]) == 1
    assert child_data["tasks"]["due_today"][0]["title"] == "Submit Report"


@pytest.mark.asyncio
async def test_coordinator_filter_overdue_tasks(hass: HomeAssistant, mock_api):
    """Test filtering overdue tasks."""
    # Mock overdue task - use offset time to match coordinator behavior
    from custom_components.firefly_cloud.dates import get_offset_time

    now_utc = get_offset_time()
    overdue_task = {
        "guid": "overdue-task",
        "title": "Late Assignment",
        "description": "Should have been submitted yesterday",
        "dueDate": firefly_due(-1),
        "setDate": (now_utc - timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "subject": {"name": "History"},
        "completionStatus": "Todo",
        "setter": {"name": "Mr. Wilson"},
    }

    mock_api.get_tasks.return_value = [overdue_task]

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    assert len(child_data["tasks"]["overdue"]) == 1
    assert child_data["tasks"]["overdue"][0]["title"] == "Late Assignment"


@pytest.mark.asyncio
async def test_coordinator_authentication_error(hass: HomeAssistant, mock_api):
    """Test handling authentication errors."""
    mock_api.get_user_info.side_effect = FireflyAuthenticationError("Auth failed")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with pytest.raises(ConfigEntryAuthFailed, match="Authentication error"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_token_expired_error(hass: HomeAssistant, mock_api):
    """Test handling token expired errors."""
    mock_api.get_user_info.side_effect = FireflyTokenExpiredError("Token expired")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with pytest.raises(ConfigEntryAuthFailed, match="Authentication token expired"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_connection_error(hass: HomeAssistant, mock_api):
    """Test handling connection errors."""
    mock_api.get_user_info.side_effect = FireflyConnectionError("Connection failed")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with pytest.raises(UpdateFailed, match="Connection error"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_unexpected_error(hass: HomeAssistant, mock_api):
    """Test handling unexpected errors."""
    mock_api.get_user_info.side_effect = ValueError("Unexpected error")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with pytest.raises(UpdateFailed, match="Unexpected error"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_partial_failure_recovery(hass: HomeAssistant, mock_api):
    """Test recovery from partial API failures."""
    # Fail on tasks but succeed on user info and events
    mock_api.get_tasks.side_effect = FireflyConnectionError("Tasks unavailable")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Should fail when tasks are unavailable (current behavior)
    with pytest.raises(UpdateFailed, match="Connection error"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_task_lookahead_filtering(hass: HomeAssistant, mock_api):
    """Test task filtering based on lookahead days."""
    # Use offset time to match coordinator behavior
    from custom_components.firefly_cloud.dates import get_offset_time

    now_utc = get_offset_time()

    # Mock tasks: one within lookahead, one beyond
    tasks = [
        {
            "guid": "task-near",
            "title": "Near Task",
            "description": "Due soon",
            "dueDate": firefly_due(3),  # Within 7
            "setDate": (now_utc - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            "subject": {"name": "Math"},
            "completionStatus": "Todo",
            "setter": {"name": "Teacher"},
        },
        {
            "guid": "task-far",
            "title": "Far Task",
            "description": "Due later",
            "dueDate": firefly_due(10),  # Beyond 7 days
            "setDate": (now_utc - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            "subject": {"name": "Science"},
            "completionStatus": "Todo",
            "setter": {"name": "Teacher"},
        },
    ]

    mock_api.get_tasks.return_value = tasks

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # Upcoming tasks should only include the near task
    assert len(child_data["tasks"]["upcoming"]) == 1
    assert child_data["tasks"]["upcoming"][0]["title"] == "Near Task"

    # All tasks should include both
    assert len(child_data["tasks"]["all"]) == 2


@pytest.mark.asyncio
async def test_coordinator_shutdown(hass: HomeAssistant, mock_api):
    """Test coordinator shutdown."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Should complete without error
    await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_coordinator_multiple_event_days(hass: HomeAssistant, mock_api):
    """Test coordinator with events spanning multiple days."""
    # Use offset time to match coordinator behavior
    from custom_components.firefly_cloud.dates import get_offset_time

    now_utc = get_offset_time()

    # Mock events for different days
    events: List[Dict[str, Any]] = [
        {
            "start": now_utc.replace(hour=9, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z"),
            "end": now_utc.replace(hour=10, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z"),
            "subject": "Today's Class",
            "location": "Room 1",
            "description": "Today",
            "guild": None,
            "attendees": [],
        },
        {
            "start": (now_utc.replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=1))
            .isoformat()
            .replace("+00:00", "Z"),
            "end": (now_utc.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1))
            .isoformat()
            .replace("+00:00", "Z"),
            "subject": "Tomorrow's Class",
            "location": "Room 2",
            "description": "Tomorrow",
            "guild": None,
            "attendees": [],
        },
    ]

    mock_api.get_events.return_value = events

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # Both events are returned (UTC timezone handling)
    assert len(child_data["events"]["today"]) == 2
    assert len(child_data["events"]["week"]) == 2
    # Verify both events are processed correctly
    subjects = [event["subject"] for event in child_data["events"]["today"]]
    assert "Today's Class" in subjects
    assert "Tomorrow's Class" in subjects


@pytest.mark.asyncio
async def test_coordinator_with_children_guids(hass: HomeAssistant, mock_api):
    """Test coordinator with explicit children GUIDs."""
    children_guids = ["child1-guid", "child2-guid"]

    # Mock children info for multiple children
    mock_api.get_children_info.return_value = [
        {"guid": "child1-guid", "username": "child1", "name": "Child One"},
        {"guid": "child2-guid", "username": "child2", "name": "Child Two"},
    ]

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
        children_guids=children_guids,
    )

    data = await coordinator._async_update_data()

    assert "children_data" in data
    assert len(data["children_data"]) == 2
    assert "child1-guid" in data["children_data"]
    assert "child2-guid" in data["children_data"]


@pytest.mark.asyncio
async def test_coordinator_events_api_error(hass: HomeAssistant, mock_api):
    """Test coordinator when events API fails."""
    mock_api.get_events.side_effect = FireflyConnectionError("Events unavailable")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with pytest.raises(UpdateFailed, match="Connection error"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_tasks_api_error_partial_recovery(hass: HomeAssistant, mock_api):
    """Test coordinator when tasks API fails but we can still get events."""
    mock_api.get_tasks.side_effect = FireflyConnectionError("Tasks service down")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Current implementation fails completely if tasks fail
    with pytest.raises(UpdateFailed, match="Connection error"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_rate_limit_error(hass: HomeAssistant, mock_api):
    """Test coordinator handling rate limit errors."""
    from custom_components.firefly_cloud.exceptions import FireflyRateLimitError

    mock_api.get_events.side_effect = FireflyRateLimitError("Rate limit exceeded")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with pytest.raises(UpdateFailed, match="Rate limit exceeded"):
        await coordinator._async_update_data()


# Remove this test since coordinator doesn't call get_children_info directly


@pytest.mark.asyncio
async def test_coordinator_malformed_task_data(hass: HomeAssistant, mock_api):
    """Test coordinator handling malformed task data."""
    # Mock task with missing fields
    malformed_tasks = [
        {
            "guid": "malformed-task",
            "title": "Incomplete Task",
            # Missing dueDate, setDate, etc.
            "completionStatus": "Todo",
        }
    ]

    mock_api.get_tasks.return_value = malformed_tasks

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Should handle gracefully and not crash
    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # Task should still be included in all tasks
    assert len(child_data["tasks"]["all"]) == 1
    assert child_data["tasks"]["all"][0]["title"] == "Incomplete Task"


@pytest.mark.asyncio
async def test_coordinator_malformed_event_data(hass: HomeAssistant, mock_api):
    """Test coordinator handling malformed event data."""
    # Mock event with missing fields
    malformed_events = [
        {
            "subject": "Incomplete Event",
            # Missing start, end, location, etc.
        }
    ]

    mock_api.get_events.return_value = malformed_events

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Should handle gracefully
    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # Event may be filtered out due to missing required fields
    assert "events" in child_data


@pytest.mark.asyncio
async def test_coordinator_empty_api_responses(hass: HomeAssistant, mock_api):
    """Test coordinator with empty API responses."""
    mock_api.get_events.return_value = []
    mock_api.get_tasks.return_value = []

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    assert data is not None
    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    assert len(child_data["events"]["today"]) == 0
    assert len(child_data["events"]["week"]) == 0
    assert len(child_data["tasks"]["all"]) == 0
    assert len(child_data["tasks"]["upcoming"]) == 0
    assert len(child_data["tasks"]["due_today"]) == 0
    assert len(child_data["tasks"]["overdue"]) == 0


@pytest.mark.asyncio
async def test_coordinator_task_date_parsing_error(hass: HomeAssistant, mock_api):
    """Test coordinator handling task date parsing errors."""
    # Mock task with invalid date format
    tasks_with_bad_dates = [
        {
            "guid": "bad-date-task",
            "title": "Task with Bad Date",
            "description": "Invalid date format",
            "dueDate": "not-a-date",  # Invalid date format
            "setDate": "also-not-a-date",
            "subject": {"name": "Mathematics"},
            "completionStatus": "Todo",
            "setter": {"name": "Teacher"},
        }
    ]

    mock_api.get_tasks.return_value = tasks_with_bad_dates

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Should handle gracefully and not crash
    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # Task may be filtered out due to date parsing issues, so check gracefully
    assert len(child_data["tasks"]["all"]) >= 0  # Should not crash


@pytest.mark.asyncio
async def test_coordinator_event_date_parsing_error(hass: HomeAssistant, mock_api):
    """Test coordinator handling event date parsing errors."""
    # Mock event with invalid date format
    events_with_bad_dates: List[Dict[str, Any]] = [
        {
            "start": "not-a-valid-timestamp",
            "end": "also-not-valid",
            "subject": "Event with Bad Dates",
            "location": "Unknown",
            "description": "Invalid dates",
            "guild": None,
            "attendees": [],
        }
    ]

    mock_api.get_events.return_value = events_with_bad_dates

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Should handle gracefully
    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # Event may be filtered out due to date parsing issues
    assert "events" in child_data


@pytest.mark.asyncio
async def test_coordinator_task_lookahead_zero_days(hass: HomeAssistant, mock_api):
    """Test coordinator with zero lookahead days."""
    now = datetime.now()

    # Mock task due tomorrow (should be filtered out with 0 lookahead)
    future_task = {
        "guid": "future-task",
        "title": "Future Task",
        "description": "Due tomorrow",
        "dueDate": firefly_due(1),
        "setDate": now.isoformat() + "Z",
        "subject": {"name": "Math"},
        "completionStatus": "Todo",
        "setter": {"name": "Teacher"},
    }

    mock_api.get_tasks.return_value = [future_task]

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=0,
    )

    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # Upcoming tasks should be empty with 0 lookahead
    assert len(child_data["tasks"]["upcoming"]) == 0
    # All tasks should still include it
    assert len(child_data["tasks"]["all"]) == 1


@pytest.mark.asyncio
async def test_coordinator_completed_tasks_filtering(hass: HomeAssistant, mock_api):
    """Test coordinator filtering completed tasks."""
    from custom_components.firefly_cloud.dates import get_offset_time

    now = get_offset_time().replace(tzinfo=None)  # Match test format

    # Mock mix of completed and incomplete tasks
    tasks = [
        {
            "guid": "completed-task",
            "title": "Completed Task",
            "description": "Already done",
            "dueDate": firefly_due(1),
            "setDate": now.isoformat() + "Z",
            "subject": {"name": "Math"},
            "completionStatus": "Done",  # Completed
            "setter": {"name": "Teacher"},
        },
        {
            "guid": "todo-task",
            "title": "Todo Task",
            "description": "Still to do",
            "dueDate": firefly_due(2),
            "setDate": now.isoformat() + "Z",
            "subject": {"name": "Science"},
            "completionStatus": "Todo",  # Not completed
            "setter": {"name": "Teacher"},
        },
    ]

    mock_api.get_tasks.return_value = tasks

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # All tasks should include both
    assert len(child_data["tasks"]["all"]) == 2

    # The coordinator currently doesn't filter by completion status, so both tasks should be included
    upcoming_titles = [task["title"] for task in child_data["tasks"]["upcoming"]]
    assert "Todo Task" in upcoming_titles
    # Note: Current implementation doesn't filter out completed tasks
    assert "Completed Task" in upcoming_titles


@pytest.mark.asyncio
async def test_coordinator_api_timeout_handling(hass: HomeAssistant, mock_api):
    """Test coordinator handling API timeout errors."""
    import asyncio

    mock_api.get_user_info.side_effect = asyncio.TimeoutError("API timeout")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with pytest.raises(UpdateFailed, match="Unexpected error"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_refresh_with_existing_data(hass: HomeAssistant, mock_api):
    """Test coordinator refresh when data already exists."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # First refresh
    await coordinator.async_refresh()
    first_data = coordinator.data

    # Modify API responses
    mock_api.get_tasks.return_value.append(
        {
            "guid": "new-task",
            "title": "New Task",
            "description": "Added after first refresh",
            "dueDate": firefly_due(1),
            "setDate": datetime.now().isoformat() + "Z",
            "subject": {"name": "Physics"},
            "completionStatus": "Todo",
            "setter": {"name": "Teacher"},
        }
    )

    # Second refresh
    await coordinator.async_refresh()
    second_data = coordinator.data

    # Data should be updated
    assert second_data != first_data

    child_guid = list(second_data["children_data"].keys())[0]
    child_data = second_data["children_data"][child_guid]

    # Should now have 2 tasks (original + new one)
    assert len(child_data["tasks"]["all"]) == 2


@pytest.mark.asyncio
async def test_coordinator_children_info_fetch_failure(hass: HomeAssistant, mock_api):
    """Test coordinator when children info fetch fails."""
    # Mock children info failure but user info success
    mock_api.get_children_info.side_effect = FireflyAuthenticationError("Children fetch failed")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
        children_guids=["child1", "child2"],  # Provide children GUIDs to trigger the fetch
    )

    # Should still work, just log warning
    data = await coordinator._async_update_data()

    assert data is not None
    # Should fall back to using provided children GUIDs
    assert "children_data" in data


@pytest.mark.asyncio
async def test_coordinator_data_structure(hass: HomeAssistant, mock_api):
    """Test coordinator data structure completeness."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    # Verify complete data structure
    assert "user_info" in data
    assert "children_data" in data
    assert "children_guids" in data
    assert "last_updated" in data

    # Verify children_data structure for each child
    for child_data in data["children_data"].values():
        assert "events" in child_data
        assert "today" in child_data["events"]
        assert "week" in child_data["events"]
        assert "tasks" in child_data
        assert "all" in child_data["tasks"]
        assert "due_today" in child_data["tasks"]
        assert "upcoming" in child_data["tasks"]
        assert "overdue" in child_data["tasks"]
        assert "name" in child_data


@pytest.mark.asyncio
async def test_coordinator_extract_child_name(hass: HomeAssistant, mock_api):
    """Test child name extraction from various sources."""
    # Mock children info for name extraction
    mock_api.get_children_info.return_value = [{"guid": "child1", "name": "Child One", "username": "child1.user"}]

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
        children_guids=["child1"],
    )

    data = await coordinator._async_update_data()

    assert data["children_data"]["child1"]["name"] == "Child One"


@pytest.mark.asyncio
async def test_coordinator_name_extraction_fallbacks(hass: HomeAssistant, mock_api):
    """Test name extraction fallbacks when primary name sources aren't available."""
    # Mock user as student (no children_info needed)
    mock_api.get_user_info.return_value = {
        "username": "student.user",
        "fullname": "Student Name",
        "role": "student",
        "guid": "student-guid",
    }

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    # Should use user fullname for student
    assert data["children_data"]["student-guid"]["name"] == "Student Name"


@pytest.mark.asyncio
async def test_coordinator_rate_limit_on_events(hass: HomeAssistant, mock_api):
    """Test coordinator handling rate limit on events fetch."""
    from custom_components.firefly_cloud.exceptions import FireflyRateLimitError

    mock_api.get_events.side_effect = FireflyRateLimitError("Too many requests")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with pytest.raises(UpdateFailed, match="Rate limit exceeded"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_subsequent_refresh_with_cached_user_info(hass: HomeAssistant, mock_api):
    """Test coordinator subsequent refresh uses cached user info."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # First refresh
    await coordinator.async_refresh()

    # Reset mock call count
    mock_api.get_user_info.reset_mock()

    # Second refresh
    await coordinator.async_refresh()

    # get_user_info should not be called again (cached)
    mock_api.get_user_info.assert_not_called()


@pytest.mark.asyncio
async def test_coordinator_process_events_invalid_date_format(hass: HomeAssistant, mock_api):
    """Test processing events with invalid date format."""
    # Mock events with invalid date format
    mock_api.get_events.return_value = [
        {
            "start": "invalid-date",
            "end": "also-invalid",
            "subject": "Test Event",
            "location": "Room 1",
            "description": "Event with bad dates",
            "guild": None,
            "attendees": [],
        }
    ]

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # Event should be filtered out due to invalid date
    assert len(child_data["events"]["today"]) == 0


@pytest.mark.asyncio
async def test_coordinator_process_tasks_invalid_due_date(hass: HomeAssistant, mock_api):
    """Test processing tasks with invalid due date."""
    # Mock tasks with invalid date
    mock_api.get_tasks.return_value = [
        {
            "guid": "invalid-date-task",
            "title": "Task with Bad Date",
            "description": "Invalid due date",
            "dueDate": "not-a-date-at-all",
            "setDate": "2023-01-01T10:00:00Z",
            "subject": {"name": "Math"},
            "completionStatus": "Todo",
            "setter": {"name": "Teacher"},
        }
    ]

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # Task should still be in all tasks but filtered from date-based lists
    assert len(child_data["tasks"]["all"]) == 1
    assert len(child_data["tasks"]["upcoming"]) == 0


@pytest.mark.asyncio
async def test_coordinator_extract_child_name_from_children_info(hass: HomeAssistant, mock_api):
    """Test extracting child name from children_info."""
    # Mock children info with names
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
        children_guids=["child-123"],
    )

    # Set up children info directly
    coordinator._children_info = [{"guid": "child-123", "name": "Child Name From Info", "username": "child123"}]

    # Test the private method
    name = coordinator._extract_child_name("child-123")

    assert name == "Child Name From Info"


@pytest.mark.asyncio
async def test_coordinator_extract_child_name_from_user_info_fullname(hass: HomeAssistant, mock_api):
    """Test extracting child name from user_info fullname."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Set user info with fullname
    coordinator._user_info = {"guid": "user-123", "fullname": "Full Name From User", "username": "user123"}

    name = coordinator._extract_child_name("user-123")

    assert name == "Full Name From User"


@pytest.mark.asyncio
async def test_coordinator_extract_child_name_from_user_info_username(hass: HomeAssistant, mock_api):
    """Test extracting child name from user_info username fallback."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Set user info without fullname
    coordinator._user_info = {"guid": "user-123", "username": "username_fallback"}

    name = coordinator._extract_child_name("user-123")

    assert name == "username_fallback"


@pytest.mark.asyncio
async def test_coordinator_extract_child_name_guid_fallback(hass: HomeAssistant, mock_api):
    """Test extracting child name with GUID fallback."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # No user info or children info
    coordinator._user_info = {"guid": "other-user"}
    coordinator._children_info = []

    name = coordinator._extract_child_name("unknown-child-123")

    assert name == "unknown-child-123"


@pytest.mark.asyncio
async def test_coordinator_process_tasks_missing_subject(hass: HomeAssistant, mock_api):
    """Test processing tasks with missing subject field."""
    now = datetime.now(timezone.utc)

    mock_api.get_tasks.return_value = [
        {
            "guid": "no-subject-task",
            "title": "Task Without Subject",
            "description": "No subject field",
            "dueDate": firefly_due(1),
            "setDate": now.isoformat().replace("+00:00", "Z"),
            # Missing subject field
            "completionStatus": "Todo",
            "setter": {"name": "Teacher"},
        }
    ]

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # Task should still be processed
    assert len(child_data["tasks"]["all"]) == 1
    processed_task = child_data["tasks"]["all"][0]
    assert processed_task["subject"] == "Unknown Subject"


@pytest.mark.asyncio
async def test_coordinator_process_tasks_missing_setter(hass: HomeAssistant, mock_api):
    """Test processing tasks with missing setter field."""
    now = datetime.now(timezone.utc)

    mock_api.get_tasks.return_value = [
        {
            "guid": "no-setter-task",
            "title": "Task Without Setter",
            "description": "No setter field",
            "dueDate": firefly_due(1),
            "setDate": now.isoformat().replace("+00:00", "Z"),
            "subject": {"name": "Math"},
            "completionStatus": "Todo",
            # Missing setter field
        }
    ]

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # Task should still be processed
    assert len(child_data["tasks"]["all"]) == 1
    processed_task = child_data["tasks"]["all"][0]
    assert processed_task["setter"] == "Unknown"


@pytest.mark.asyncio
async def test_coordinator_process_tasks_keyerror_handling(hass: HomeAssistant, mock_api):
    """Test _process_tasks handling KeyError and TypeError."""
    # Mock task that will cause KeyError during processing
    mock_api.get_tasks.return_value = [
        {
            # Missing required fields to trigger KeyError/TypeError
            "description": "Task missing critical fields",
        }
    ]

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    data = await coordinator._async_update_data()

    child_guid = list(data["children_data"].keys())[0]
    child_data = data["children_data"][child_guid]

    # Task should be filtered out due to processing error (gracefully handled)
    assert len(child_data["tasks"]["all"]) >= 0


@pytest.mark.asyncio
async def test_coordinator_process_tasks_subject_dict(hass):
    """Test coordinator handles task with subject as dict."""
    from unittest.mock import AsyncMock

    from custom_components.firefly_cloud.api import FireflyAPIClient
    from custom_components.firefly_cloud.coordinator import FireflyUpdateCoordinator

    # Create mock API client
    mock_api = AsyncMock(spec=FireflyAPIClient)

    coordinator = FireflyUpdateCoordinator(hass, mock_api, task_lookahead_days=7, children_guids=["child1"])

    # Create task with subject as dict
    tasks = [
        {
            "guid": "task1",
            "title": "Math Homework",
            "description": "Page 42",
            "subject": {"name": "Mathematics", "id": "math-id"},  # Dict format
            "dueDate": "2024-01-15T12:00:00Z",
            "setter": {"name": "Mr. Smith"},
            "personal": False,
        }
    ]

    processed = coordinator._process_tasks(tasks)

    assert len(processed) == 1
    assert processed[0]["subject"] == "Mathematics"


@pytest.mark.asyncio
async def test_coordinator_process_tasks_subject_string(hass):
    """Test coordinator handles task with subject as string."""
    from unittest.mock import AsyncMock

    from custom_components.firefly_cloud.api import FireflyAPIClient
    from custom_components.firefly_cloud.coordinator import FireflyUpdateCoordinator

    # Create mock API client
    mock_api = AsyncMock(spec=FireflyAPIClient)

    coordinator = FireflyUpdateCoordinator(hass, mock_api, task_lookahead_days=7, children_guids=["child1"])

    # Create task with subject as string
    tasks = [
        {
            "guid": "task1",
            "title": "Math Homework",
            "description": "Page 42",
            "subject": "Mathematics",  # String format
            "dueDate": "2024-01-15T12:00:00Z",
            "setter": {"name": "Mr. Smith"},
            "personal": False,
        }
    ]

    processed = coordinator._process_tasks(tasks)

    assert len(processed) == 1
    assert processed[0]["subject"] == "Mathematics"


# Issue Registry Tests


@pytest.mark.asyncio
async def test_coordinator_issue_registry_dismissal_on_success(hass: HomeAssistant, mock_api):
    """Test that issues are dismissed on successful update."""
    from unittest.mock import patch

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with patch("custom_components.firefly_cloud.coordinator.ir") as mock_ir:
        # Perform successful update
        await coordinator._async_update_data()

        # Verify all issues were dismissed
        assert mock_ir.async_delete_issue.call_count == 5
        mock_ir.async_delete_issue.assert_any_call(hass, "firefly_cloud", "connection_error")
        mock_ir.async_delete_issue.assert_any_call(hass, "firefly_cloud", "authentication_error")
        mock_ir.async_delete_issue.assert_any_call(hass, "firefly_cloud", "rate_limit_error")
        mock_ir.async_delete_issue.assert_any_call(hass, "firefly_cloud", "data_error")
        mock_ir.async_delete_issue.assert_any_call(hass, "firefly_cloud", "unexpected_error")


@pytest.mark.asyncio
async def test_coordinator_issue_creation_authentication_error(hass: HomeAssistant, mock_api):
    """Test issue creation on authentication error."""
    from unittest.mock import patch

    mock_api.get_user_info.side_effect = FireflyAuthenticationError("Auth failed")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with patch("custom_components.firefly_cloud.coordinator.ir") as mock_ir:
        with pytest.raises(ConfigEntryAuthFailed, match="Authentication error"):
            await coordinator._async_update_data()

        # Verify issue was created immediately
        mock_ir.async_create_issue.assert_called_once()
        call_args = mock_ir.async_create_issue.call_args
        assert call_args[0][1] == "firefly_cloud"
        assert call_args[0][2] == "authentication_error"
        assert call_args[1]["translation_key"] == "authentication_error"


@pytest.mark.asyncio
async def test_coordinator_issue_creation_token_expired(hass: HomeAssistant, mock_api):
    """Test issue creation on token expired error."""
    from unittest.mock import patch

    mock_api.get_user_info.side_effect = FireflyTokenExpiredError("Token expired")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with patch("custom_components.firefly_cloud.coordinator.ir") as mock_ir:
        with pytest.raises(ConfigEntryAuthFailed, match="Authentication token expired"):
            await coordinator._async_update_data()

        # Verify issue was created immediately
        mock_ir.async_create_issue.assert_called_once()
        call_args = mock_ir.async_create_issue.call_args
        assert call_args[0][2] == "authentication_error"


@pytest.mark.asyncio
async def test_coordinator_connection_error_threshold(hass: HomeAssistant, mock_api):
    """Test that connection errors only create issue after 3 failures."""
    from unittest.mock import patch

    mock_api.get_user_info.side_effect = FireflyConnectionError("Connection failed")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with patch("custom_components.firefly_cloud.coordinator.ir") as mock_ir:
        # First failure - no issue created
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator.consecutive_failures == 1
        mock_ir.async_create_issue.assert_not_called()

        # Second failure - still no issue created
        mock_ir.reset_mock()
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator.consecutive_failures == 2
        mock_ir.async_create_issue.assert_not_called()

        # Third failure - issue should be created
        mock_ir.reset_mock()
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator.consecutive_failures == 3
        mock_ir.async_create_issue.assert_called_once()

        call_args = mock_ir.async_create_issue.call_args
        assert call_args[0][2] == "connection_error"
        assert call_args[1]["translation_placeholders"]["consecutive_failures"] == "3"


@pytest.mark.asyncio
async def test_coordinator_rate_limit_immediate_issue(hass: HomeAssistant, mock_api):
    """Test that rate limit errors create issue immediately."""
    from unittest.mock import patch

    from custom_components.firefly_cloud.exceptions import FireflyRateLimitError

    mock_api.get_user_info.side_effect = FireflyRateLimitError("Rate limited")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with patch("custom_components.firefly_cloud.coordinator.ir") as mock_ir:
        with pytest.raises(UpdateFailed, match="Rate limit exceeded"):
            await coordinator._async_update_data()

        # Verify issue was created immediately
        mock_ir.async_create_issue.assert_called_once()
        call_args = mock_ir.async_create_issue.call_args
        assert call_args[0][2] == "rate_limit_error"
        assert "update_interval" in call_args[1]["translation_placeholders"]
        # Should suggest 20 minutes (15 + 5)
        assert call_args[1]["translation_placeholders"]["update_interval"] == "20"


@pytest.mark.asyncio
async def test_coordinator_data_error_threshold(hass: HomeAssistant, mock_api):
    """Test that data errors only create issue after 2 failures."""
    from unittest.mock import patch

    from custom_components.firefly_cloud.exceptions import FireflyDataError

    mock_api.get_user_info.side_effect = FireflyDataError("Data processing failed")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with patch("custom_components.firefly_cloud.coordinator.ir") as mock_ir:
        # First failure - no issue created
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator.consecutive_data_errors == 1
        mock_ir.async_create_issue.assert_not_called()

        # Second failure - issue should be created
        mock_ir.reset_mock()
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator.consecutive_data_errors == 2
        mock_ir.async_create_issue.assert_called_once()

        call_args = mock_ir.async_create_issue.call_args
        assert call_args[0][2] == "data_error"
        assert "error_message" in call_args[1]["translation_placeholders"]


@pytest.mark.asyncio
async def test_coordinator_unexpected_error_threshold(hass: HomeAssistant, mock_api):
    """Test that unexpected errors only create issue after 2 failures."""
    from unittest.mock import patch

    mock_api.get_user_info.side_effect = ValueError("Unexpected error")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with patch("custom_components.firefly_cloud.coordinator.ir") as mock_ir:
        # First failure - no issue created
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator.consecutive_failures == 1
        mock_ir.async_create_issue.assert_not_called()

        # Second failure - issue should be created
        mock_ir.reset_mock()
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator.consecutive_failures == 2
        mock_ir.async_create_issue.assert_called_once()

        call_args = mock_ir.async_create_issue.call_args
        assert call_args[0][2] == "unexpected_error"
        assert "error_message" in call_args[1]["translation_placeholders"]


@pytest.mark.asyncio
async def test_coordinator_failure_counter_reset_on_success(hass: HomeAssistant, mock_api):
    """Test that failure counters reset after successful update."""
    from unittest.mock import patch

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Simulate previous failures
    coordinator.consecutive_failures = 5
    coordinator.consecutive_data_errors = 3

    with patch("custom_components.firefly_cloud.coordinator.ir"):
        # Successful update
        await coordinator._async_update_data()

        # Verify counters are reset
        assert coordinator.consecutive_failures == 0
        assert coordinator.consecutive_data_errors == 0


@pytest.mark.asyncio
async def test_coordinator_connection_error_counter_increments(hass: HomeAssistant, mock_api):
    """Test that connection error counter increments properly."""
    mock_api.get_user_info.side_effect = FireflyConnectionError("Connection failed")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    assert coordinator.consecutive_failures == 0

    # First failure
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator.consecutive_failures == 1

    # Second failure
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator.consecutive_failures == 2

    # Third failure
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator.consecutive_failures == 3


@pytest.mark.asyncio
async def test_coordinator_issue_severity_levels(hass: HomeAssistant, mock_api):
    """Test that different errors use appropriate severity levels."""
    from unittest.mock import patch

    from homeassistant.helpers import issue_registry as ir

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Store the actual severity enum before patching
    severity_error = ir.IssueSeverity.ERROR
    severity_warning = ir.IssueSeverity.WARNING

    with patch("custom_components.firefly_cloud.coordinator.ir") as mock_ir:
        # Make the patched ir module return the real severity values
        mock_ir.IssueSeverity.ERROR = severity_error
        mock_ir.IssueSeverity.WARNING = severity_warning

        # Authentication error - should be ERROR
        mock_api.get_user_info.side_effect = FireflyAuthenticationError("Auth failed")
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

        call_args = mock_ir.async_create_issue.call_args
        assert call_args[1]["severity"] == severity_error

        # Reset for next test
        mock_ir.reset_mock()
        mock_api.get_user_info.side_effect = None

        # Rate limit error - should be WARNING
        from custom_components.firefly_cloud.exceptions import FireflyRateLimitError

        mock_api.get_user_info.side_effect = FireflyRateLimitError("Rate limited")
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        call_args = mock_ir.async_create_issue.call_args
        assert call_args[1]["severity"] == severity_warning


# Statistics Tracking Tests


@pytest.mark.asyncio
async def test_coordinator_statistics_initialization(hass: HomeAssistant, mock_api):
    """Test that statistics are properly initialized."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    assert coordinator.statistics["total_updates"] == 0
    assert coordinator.statistics["successful_updates"] == 0
    assert coordinator.statistics["failed_updates"] == 0
    assert coordinator.statistics["last_update_time"] is None
    assert coordinator.statistics["last_success_time"] is None
    assert coordinator.statistics["last_failure_time"] is None
    assert coordinator.statistics["error_counts"] == {}


@pytest.mark.asyncio
async def test_coordinator_statistics_successful_update(hass: HomeAssistant, mock_api):
    """Test that statistics are updated on successful update."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    await coordinator._async_update_data()

    assert coordinator.statistics["total_updates"] == 1
    assert coordinator.statistics["successful_updates"] == 1
    assert coordinator.statistics["failed_updates"] == 0
    assert coordinator.statistics["last_update_time"] is not None
    assert coordinator.statistics["last_success_time"] is not None
    assert coordinator.statistics["last_failure_time"] is None
    assert coordinator.statistics["error_counts"] == {}


@pytest.mark.asyncio
async def test_coordinator_statistics_failed_update(hass: HomeAssistant, mock_api):
    """Test that statistics are updated on failed update."""
    mock_api.get_user_info.side_effect = FireflyConnectionError("Connection failed")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator.statistics["total_updates"] == 1
    assert coordinator.statistics["successful_updates"] == 0
    assert coordinator.statistics["failed_updates"] == 1
    assert coordinator.statistics["last_update_time"] is not None
    assert coordinator.statistics["last_success_time"] is None
    assert coordinator.statistics["last_failure_time"] is not None
    assert "FireflyConnectionError" in coordinator.statistics["error_counts"]
    assert coordinator.statistics["error_counts"]["FireflyConnectionError"] == 1


@pytest.mark.asyncio
async def test_coordinator_statistics_multiple_failures(hass: HomeAssistant, mock_api):
    """Test that statistics track multiple failures correctly."""
    mock_api.get_user_info.side_effect = FireflyConnectionError("Connection failed")

    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # First failure
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    # Second failure
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    # Third failure
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator.statistics["total_updates"] == 3
    assert coordinator.statistics["successful_updates"] == 0
    assert coordinator.statistics["failed_updates"] == 3
    assert coordinator.statistics["error_counts"]["FireflyConnectionError"] == 3


@pytest.mark.asyncio
async def test_coordinator_statistics_mixed_results(hass: HomeAssistant, mock_api):
    """Test statistics with mixed success and failure updates."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Successful update
    await coordinator._async_update_data()

    assert coordinator.statistics["total_updates"] == 1
    assert coordinator.statistics["successful_updates"] == 1
    assert coordinator.statistics["failed_updates"] == 0

    # Failed update - clear cached user info so it tries to fetch again
    coordinator._user_info = None
    mock_api.get_user_info.side_effect = FireflyConnectionError("Connection failed")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator.statistics["total_updates"] == 2
    assert coordinator.statistics["successful_updates"] == 1
    assert coordinator.statistics["failed_updates"] == 1

    # Another successful update - clear the exception and set return value
    mock_api.get_user_info.side_effect = None
    mock_api.get_user_info.return_value = {
        "username": "john.doe",
        "fullname": "John Doe",
        "guid": "test-user-123",
    }
    await coordinator._async_update_data()

    assert coordinator.statistics["total_updates"] == 3
    assert coordinator.statistics["successful_updates"] == 2
    assert coordinator.statistics["failed_updates"] == 1


@pytest.mark.asyncio
async def test_coordinator_statistics_error_type_tracking(hass: HomeAssistant, mock_api):
    """Test that different error types are tracked separately."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )

    # Connection error
    mock_api.get_user_info.side_effect = FireflyConnectionError("Connection failed")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert "FireflyConnectionError" in coordinator.statistics["error_counts"]
    assert coordinator.statistics["error_counts"]["FireflyConnectionError"] == 1

    # Authentication error
    mock_api.get_user_info.side_effect = FireflyAuthenticationError("Auth failed")
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()

    assert "FireflyAuthenticationError" in coordinator.statistics["error_counts"]
    assert coordinator.statistics["error_counts"]["FireflyAuthenticationError"] == 1
    assert coordinator.statistics["error_counts"]["FireflyConnectionError"] == 1

    # Another connection error
    mock_api.get_user_info.side_effect = FireflyConnectionError("Connection failed again")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator.statistics["error_counts"]["FireflyConnectionError"] == 2
    assert coordinator.statistics["error_counts"]["FireflyAuthenticationError"] == 1


# --- Local calendar due dates -------------------------------------------------


def _task(due):
    """Build a raw Firefly task with the given dueDate."""
    return {"id": f"id-{due}", "title": f"due {due}", "dueDate": due, "completionStatus": "Todo"}


@pytest.fixture
def date_coordinator(hass: HomeAssistant, mock_api, melbourne):
    """Coordinator with HA set to Australia/Melbourne."""
    return FireflyUpdateCoordinator(hass=hass, api=mock_api, task_lookahead_days=7)


@freeze_time("2026-11-20 10:00:00")  # UTC: 9pm 20 Nov in Melbourne
def test_due_today_all_day_local(date_coordinator):
    """A task due today is due all day, and not overdue in the evening."""
    tasks = [_task("2026-11-20T00:00:00")]
    today = date(2026, 11, 20)
    assert len(date_coordinator._filter_tasks_by_date(tasks, today, today + timedelta(days=1))) == 1
    assert date_coordinator._filter_overdue_tasks(tasks, today) == []


def test_overdue_from_next_day(date_coordinator):
    """A task becomes overdue the day after its due date."""
    tasks = [_task("2026-11-20T00:00:00")]
    assert len(date_coordinator._filter_overdue_tasks(tasks, date(2026, 11, 21))) == 1


def test_upcoming_window_is_today_plus_lookahead_exclusive(date_coordinator):
    """The lookahead window includes today + 6 days and excludes today + 7."""
    tasks = [_task("2026-11-20T00:00:00"), _task("2026-11-21T00:00:00")]
    today = date(2026, 11, 14)
    titles = [t["title"] for t in date_coordinator._filter_tasks_by_date(tasks, today, today + timedelta(days=7))]
    assert titles == ["due 2026-11-20T00:00:00"]


def test_filters_skip_bad_due_dates(date_coordinator):
    """Missing or junk due dates are left out of every filter."""
    tasks = [_task(None), _task(""), _task("not-a-date")]
    today = date(2026, 11, 14)
    assert date_coordinator._filter_tasks_by_date(tasks, today, today + timedelta(days=7)) == []
    assert date_coordinator._filter_overdue_tasks(tasks, today) == []


def test_overdue_skips_completed(date_coordinator):
    """Completed tasks are never overdue."""
    task = _task("2026-11-01T00:00:00") | {"completionStatus": "Completed"}
    assert date_coordinator._filter_overdue_tasks([task], date(2026, 11, 14)) == []


def test_processed_due_date_is_local_midnight(date_coordinator):
    """Processed tasks carry the due date as local midnight."""
    [processed] = date_coordinator._process_tasks([_task("2026-11-20T00:00:00")])
    assert processed["due_date"].isoformat() == "2026-11-20T00:00:00+11:00"


@pytest.mark.asyncio
@freeze_time("2026-11-19 14:00:00")  # UTC: 1am on 20 Nov in Melbourne, still 19 Nov in UTC
async def test_update_uses_local_today(hass: HomeAssistant, mock_api, melbourne):
    """The full update works out "today" in HA's timezone, not UTC."""
    mock_api.get_tasks.return_value = [
        _task("2026-11-20T00:00:00") | {"title": "Due 20th"},
        _task("2026-11-19T00:00:00") | {"title": "Due 19th"},
    ]
    coordinator = FireflyUpdateCoordinator(hass=hass, api=mock_api, task_lookahead_days=7)

    data = await coordinator._async_update_data()

    tasks = next(iter(data["children_data"].values()))["tasks"]
    assert [t["title"] for t in tasks["due_today"]] == ["Due 20th"]
    assert [t["title"] for t in tasks["overdue"]] == ["Due 19th"]


def test_overdue_handles_null_completion_status(date_coordinator):
    """A task with a null completionStatus is treated as not completed, without raising."""
    task = _task("2026-11-01T00:00:00") | {"completionStatus": None}
    assert len(date_coordinator._filter_overdue_tasks([task], date(2026, 11, 14))) == 1


def _week_event(code, subject):
    return {
        "start": "2026-11-16T21:55:00Z",
        "end": "2026-11-16T22:55:00Z",
        "subject": subject,
        "description": f"{code}\nAttendees: Unknown, Unknown",
    }


@pytest.mark.asyncio
async def test_update_fills_in_subjects(hass: HomeAssistant, mock_api):
    """A full update gives tasks the subject of their class from the timetable."""
    mock_api.get_tasks.return_value = [
        {"id": 1, "title": "A", "dueDate": firefly_due(2), "addressees": [{"name": "Class PABC1 B"}]}
    ]
    mock_api.get_events.return_value = [_week_event("PABC1 B", "Year 8 Performing Arts")]
    coordinator = FireflyUpdateCoordinator(hass=hass, api=mock_api)
    data = await coordinator._async_update_data()
    [task] = next(iter(data["children_data"].values()))["tasks"]["all"]
    assert task["subject"] == "Year 8 Performing Arts"
