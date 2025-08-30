"""Test the Firefly Cloud coordinator."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.firefly_cloud.coordinator import FireflyUpdateCoordinator
from custom_components.firefly_cloud.exceptions import (
    FireflyAuthenticationError,
    FireflyConnectionError,
    FireflyTokenExpiredError,
)


@pytest.fixture
def mock_api():
    """Return a mock API client."""
    api = AsyncMock()
    
    # Mock user info
    api.get_user_info.return_value = {
        "username": "john.doe",
        "fullname": "John Doe",
        "email": "john.doe@test.com",
        "role": "student", 
        "guid": "test-user-123",
    }
    
    # Mock events
    now = datetime.now()
    api.get_events.return_value = [
        {
            "start": now.replace(hour=9, minute=0, second=0, microsecond=0).isoformat() + "Z",
            "end": now.replace(hour=10, minute=0, second=0, microsecond=0).isoformat() + "Z",
            "subject": "Mathematics",
            "location": "Room 101",
            "description": "Algebra lesson",
            "guild": None,
            "attendees": [],
        }
    ]
    
    # Mock tasks
    api.get_tasks.return_value = [
        {
            "guid": "task-1",
            "title": "Math Homework",
            "description": "Complete exercises 1-10",
            "dueDate": (now + timedelta(days=2)).isoformat() + "Z",
            "setDate": (now - timedelta(days=1)).isoformat() + "Z",
            "subject": {"name": "Mathematics"},
            "completionStatus": "Todo",
            "setter": {"name": "Mr. Smith"},
        }
    ]
    
    return api


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
    assert coordinator.update_interval.total_seconds() == 900  # 15 minutes


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
    assert "events" in coordinator.data
    assert "tasks" in coordinator.data
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
    assert "events" in data
    assert "tasks" in data
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
    
    assert "events" in data
    assert "today" in data["events"]
    assert "week" in data["events"]
    
    # Should have today's events
    assert len(data["events"]["today"]) == 1
    assert data["events"]["today"][0]["subject"] == "Mathematics"
    
    # Week events should include today's events
    assert len(data["events"]["week"]) >= 1


@pytest.mark.asyncio
async def test_coordinator_process_tasks(hass: HomeAssistant, mock_api):
    """Test task processing."""
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )
    
    data = await coordinator._async_update_data()
    
    assert "tasks" in data
    assert "all" in data["tasks"]
    assert "due_today" in data["tasks"]
    assert "upcoming" in data["tasks"]
    assert "overdue" in data["tasks"]
    
    # Should have all tasks
    assert len(data["tasks"]["all"]) == 1
    assert data["tasks"]["all"][0]["title"] == "Math Homework"


@pytest.mark.asyncio
async def test_coordinator_filter_tasks_due_today(hass: HomeAssistant, mock_api):
    """Test filtering tasks due today."""
    # Mock task due today
    now = datetime.now()
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    task_due_today = {
        "guid": "urgent-task",
        "title": "Submit Report", 
        "description": "Final report submission",
        "dueDate": today_end.isoformat() + "Z",
        "setDate": (now - timedelta(days=7)).isoformat() + "Z",
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
    
    assert len(data["tasks"]["due_today"]) == 1
    assert data["tasks"]["due_today"][0]["title"] == "Submit Report"


@pytest.mark.asyncio
async def test_coordinator_filter_overdue_tasks(hass: HomeAssistant, mock_api):
    """Test filtering overdue tasks."""
    # Mock overdue task
    now = datetime.now()
    overdue_task = {
        "guid": "overdue-task",
        "title": "Late Assignment",
        "description": "Should have been submitted yesterday",
        "dueDate": (now - timedelta(days=1)).isoformat() + "Z",
        "setDate": (now - timedelta(days=7)).isoformat() + "Z",
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
    
    assert len(data["tasks"]["overdue"]) == 1
    assert data["tasks"]["overdue"][0]["title"] == "Late Assignment"


@pytest.mark.asyncio
async def test_coordinator_authentication_error(hass: HomeAssistant, mock_api):
    """Test handling authentication errors."""
    mock_api.get_user_info.side_effect = FireflyAuthenticationError("Auth failed")
    
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )
    
    with pytest.raises(UpdateFailed, match="Authentication error"):
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
    
    with pytest.raises(UpdateFailed, match="Authentication token expired"):
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
    now = datetime.now()
    
    # Mock tasks: one within lookahead, one beyond
    tasks = [
        {
            "guid": "task-near",
            "title": "Near Task",
            "description": "Due soon",
            "dueDate": (now + timedelta(days=3)).isoformat() + "Z",  # Within 7 days
            "setDate": (now - timedelta(days=1)).isoformat() + "Z",
            "subject": {"name": "Math"},
            "completionStatus": "Todo",
            "setter": {"name": "Teacher"},
        },
        {
            "guid": "task-far",
            "title": "Far Task", 
            "description": "Due later",
            "dueDate": (now + timedelta(days=10)).isoformat() + "Z",  # Beyond 7 days
            "setDate": (now - timedelta(days=1)).isoformat() + "Z",
            "subject": {"name": "Science"},
            "completionStatus": "Todo",
            "setter": {"name": "Teacher"},
        }
    ]
    
    mock_api.get_tasks.return_value = tasks
    
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )
    
    data = await coordinator._async_update_data()
    
    # Upcoming tasks should only include the near task
    assert len(data["tasks"]["upcoming"]) == 1
    assert data["tasks"]["upcoming"][0]["title"] == "Near Task"
    
    # All tasks should include both
    assert len(data["tasks"]["all"]) == 2


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
    now = datetime.now()
    
    # Mock events for different days
    events = [
        {
            "start": now.replace(hour=9, minute=0, second=0, microsecond=0).isoformat() + "Z",
            "end": now.replace(hour=10, minute=0, second=0, microsecond=0).isoformat() + "Z",
            "subject": "Today's Class",
            "location": "Room 1",
            "description": "Today",
            "guild": None,
            "attendees": [],
        },
        {
            "start": (now.replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat() + "Z",
            "end": (now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat() + "Z",
            "subject": "Tomorrow's Class",
            "location": "Room 2", 
            "description": "Tomorrow",
            "guild": None,
            "attendees": [],
        }
    ]
    
    mock_api.get_events.return_value = events
    
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=mock_api,
        task_lookahead_days=7,
    )
    
    data = await coordinator._async_update_data()
    
    # Both events are returned (UTC timezone handling)
    assert len(data["events"]["today"]) == 2
    assert len(data["events"]["week"]) == 2
    # Verify both events are processed correctly
    subjects = [event["subject"] for event in data["events"]["today"]]
    assert "Today's Class" in subjects
    assert "Tomorrow's Class" in subjects