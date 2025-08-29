"""Test the Firefly Cloud API client."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio

from custom_components.firefly_cloud.api import FireflyAPIClient
from custom_components.firefly_cloud.exceptions import (
    FireflyAPIError,
    FireflyAuthenticationError,
    FireflyConnectionError,
    FireflyDataError,
    FireflyRateLimitError,
    FireflySchoolNotFoundError,
    FireflyTokenExpiredError,
)


@pytest.fixture
def api_client(mock_aiohttp_session):
    """Return a FireflyAPIClient instance."""
    return FireflyAPIClient(
        session=mock_aiohttp_session,
        host="https://testschool.fireflycloud.net",
        device_id="test-device-123",
        secret="test-secret-456",
    )


@pytest.mark.asyncio
async def test_get_school_info_success(mock_aiohttp_session, mock_school_info):
    """Test successful school info retrieval."""
    # Mock XML response
    xml_response = """<?xml version="1.0"?>
    <response exists="true" enabled="true">
        <name>Test School</name>
        <installationId>test-installation-id</installationId>
        <address ssl="true">testschool.fireflycloud.net</address>
    </response>"""
    
    mock_response = AsyncMock()
    mock_response.text.return_value = xml_response
    mock_response.raise_for_status.return_value = None
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response
    
    result = await FireflyAPIClient.get_school_info(mock_aiohttp_session, "testschool")
    
    assert result["enabled"] is True
    assert result["name"] == "Test School"
    assert result["host"] == "testschool.fireflycloud.net"
    assert result["ssl"] is True
    assert result["url"] == "https://testschool.fireflycloud.net"
    assert "device_id" in result


@pytest.mark.asyncio
async def test_get_school_info_not_found(mock_aiohttp_session):
    """Test school not found."""
    xml_response = """<?xml version="1.0"?>
    <response exists="false">
    </response>"""
    
    mock_response = AsyncMock()
    mock_response.text.return_value = xml_response
    mock_response.raise_for_status.return_value = None
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response
    
    with pytest.raises(FireflySchoolNotFoundError):
        await FireflyAPIClient.get_school_info(mock_aiohttp_session, "nonexistent")


@pytest.mark.asyncio
async def test_get_school_info_invalid_code():
    """Test invalid school code."""
    with pytest.raises(FireflySchoolNotFoundError):
        await FireflyAPIClient.get_school_info(AsyncMock(), "")


@pytest.mark.asyncio
async def test_get_api_version_success(api_client, mock_aiohttp_session):
    """Test successful API version retrieval."""
    xml_response = """<?xml version="1.0"?>
    <version>
        <majorVersion>1</majorVersion>
        <minorVersion>2</minorVersion>
        <incrementVersion>3</incrementVersion>
    </version>"""
    
    mock_response = AsyncMock()
    mock_response.text.return_value = xml_response
    mock_response.raise_for_status.return_value = None
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response
    
    result = await api_client.get_api_version()
    
    assert result["major"] == 1
    assert result["minor"] == 2
    assert result["increment"] == 3


@pytest.mark.asyncio
async def test_verify_credentials_success(api_client, mock_aiohttp_session):
    """Test successful credential verification."""
    mock_response = AsyncMock()
    mock_response.json.return_value = {"valid": True}
    mock_response.status = 200
    mock_response.raise_for_status.return_value = None
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response
    
    result = await api_client.verify_credentials()
    
    assert result is True


@pytest.mark.asyncio
async def test_verify_credentials_invalid(api_client, mock_aiohttp_session):
    """Test invalid credential verification."""
    mock_response = AsyncMock()
    mock_response.status = 401
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response
    
    result = await api_client.verify_credentials()
    
    assert result is False


@pytest.mark.asyncio
async def test_parse_authentication_response_success(api_client):
    """Test successful authentication response parsing."""
    xml_response = """<token>
        <secret>test-secret-789</secret>
        <user username="john.doe" fullname="John Doe" email="john.doe@test.com" role="student" guid="test-user-123"/>
    </token>"""
    
    result = await api_client.parse_authentication_response(xml_response)
    
    assert result["secret"] == "test-secret-789"
    assert result["user"]["username"] == "john.doe"
    assert result["user"]["fullname"] == "John Doe"
    assert result["user"]["guid"] == "test-user-123"


@pytest.mark.asyncio
async def test_parse_authentication_response_empty():
    """Test empty authentication response."""
    api_client = FireflyAPIClient(
        session=AsyncMock(),
        host="https://test.com",
        device_id="test",
        secret="test",
    )
    
    with pytest.raises(FireflyAuthenticationError):
        await api_client.parse_authentication_response("")


@pytest.mark.asyncio
async def test_parse_authentication_response_invalid_xml():
    """Test invalid XML in authentication response."""
    api_client = FireflyAPIClient(
        session=AsyncMock(),
        host="https://test.com",
        device_id="test",
        secret="test",
    )
    
    with pytest.raises(FireflyAuthenticationError):
        await api_client.parse_authentication_response("invalid xml")


@pytest.mark.asyncio
async def test_graphql_query_success(api_client, mock_aiohttp_session):
    """Test successful GraphQL query."""
    mock_response = AsyncMock()
    mock_response.json.return_value = {"data": {"test": "result"}}
    mock_response.status = 200
    mock_response.raise_for_status.return_value = None
    mock_aiohttp_session.post.return_value.__aenter__.return_value = mock_response
    
    result = await api_client._graphql_query("query { test }")
    
    assert result == {"test": "result"}


@pytest.mark.asyncio
async def test_graphql_query_token_expired(api_client, mock_aiohttp_session):
    """Test GraphQL query with expired token."""
    mock_response = AsyncMock()
    mock_response.status = 401
    mock_aiohttp_session.post.return_value.__aenter__.return_value = mock_response
    
    with pytest.raises(FireflyTokenExpiredError):
        await api_client._graphql_query("query { test }")


@pytest.mark.asyncio
async def test_graphql_query_rate_limit(api_client, mock_aiohttp_session):
    """Test GraphQL query with rate limit."""
    mock_response = AsyncMock()
    mock_response.status = 429
    mock_aiohttp_session.post.return_value.__aenter__.return_value = mock_response
    
    with pytest.raises(FireflyRateLimitError):
        await api_client._graphql_query("query { test }")


@pytest.mark.asyncio
async def test_graphql_query_api_errors(api_client, mock_aiohttp_session):
    """Test GraphQL query with API errors."""
    mock_response = AsyncMock()
    mock_response.json.return_value = {"errors": [{"message": "Test error"}]}
    mock_response.status = 200
    mock_response.raise_for_status.return_value = None
    mock_aiohttp_session.post.return_value.__aenter__.return_value = mock_response
    
    with pytest.raises(FireflyAPIError):
        await api_client._graphql_query("query { test }")


@pytest.mark.asyncio
async def test_get_events_success(api_client, mock_events):
    """Test successful event retrieval."""
    api_client._user_info = {"guid": "test-user-123"}
    
    with patch.object(api_client, "_graphql_query") as mock_query:
        mock_query.return_value = {"events": mock_events}
        
        start = datetime(2023, 1, 1, 9, 0)
        end = datetime(2023, 1, 1, 17, 0)
        
        result = await api_client.get_events(start, end)
        
        assert len(result) == len(mock_events)
        assert result == mock_events


@pytest.mark.asyncio
async def test_get_tasks_success(api_client, mock_tasks):
    """Test successful task retrieval."""
    mock_response = AsyncMock()
    mock_response.json.return_value = {"items": mock_tasks}
    mock_response.status = 200
    mock_response.raise_for_status.return_value = None
    api_client._session.post.return_value.__aenter__.return_value = mock_response
    
    result = await api_client.get_tasks()
    
    assert len(result) == len(mock_tasks)
    assert result == mock_tasks


@pytest.mark.asyncio
async def test_get_tasks_token_expired(api_client):
    """Test task retrieval with expired token."""
    mock_response = AsyncMock()
    mock_response.status = 401
    api_client._session.post.return_value.__aenter__.return_value = mock_response
    
    with pytest.raises(FireflyTokenExpiredError):
        await api_client.get_tasks()


@pytest.mark.asyncio
async def test_get_participating_groups_success(api_client):
    """Test successful participating groups retrieval."""
    api_client._user_info = {"guid": "test-user-123"}
    mock_groups = [{"guid": "group1", "name": "Test Group"}]
    
    with patch.object(api_client, "_graphql_query") as mock_query:
        mock_query.return_value = {"users": [{"participating_in": mock_groups}]}
        
        result = await api_client.get_participating_groups()
        
        assert result == mock_groups


@pytest.mark.asyncio
async def test_get_participating_groups_no_user(api_client):
    """Test participating groups retrieval without user info."""
    with pytest.raises(FireflyAuthenticationError):
        await api_client.get_participating_groups()


@pytest.mark.asyncio
async def test_get_auth_url(api_client):
    """Test authentication URL generation."""
    url = api_client.get_auth_url()
    
    assert "https://testschool.fireflycloud.net/login/login.aspx" in url
    assert "prelogin=" in url
    assert "test-device-123" in url


@pytest.mark.asyncio
async def test_get_user_info_cached(api_client):
    """Test getting cached user info."""
    user_info = {"guid": "test-user-123", "fullname": "Test User"}
    api_client._user_info = user_info
    
    result = await api_client.get_user_info()
    
    assert result == user_info


@pytest.mark.asyncio
async def test_get_user_info_no_cache(api_client):
    """Test getting user info without cache."""
    with pytest.raises(FireflyAuthenticationError):
        await api_client.get_user_info()