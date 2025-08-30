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
    <root>
        <response exists="true" enabled="true">
            <name>Test School</name>
            <installationId>test-installation-id</installationId>
            <address ssl="true">testschool.fireflycloud.net</address>
        </response>
    </root>"""
    
    from tests.conftest import mock_http_response
    mock_aiohttp_session._mock_responses['get'] = mock_http_response(text=xml_response)
    
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
    <root>
        <response exists="false">
        </response>
    </root>"""
    
    from tests.conftest import mock_http_response
    mock_aiohttp_session._mock_responses['get'] = mock_http_response(text=xml_response)
    
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
    <root>
        <version>
            <majorVersion>1</majorVersion>
            <minorVersion>2</minorVersion>
            <incrementVersion>3</incrementVersion>
        </version>
    </root>"""
    
    from tests.conftest import mock_http_response
    mock_aiohttp_session._mock_responses['get'] = mock_http_response(text=xml_response)
    
    result = await api_client.get_api_version()
    
    assert result["major"] == 1
    assert result["minor"] == 2
    assert result["increment"] == 3


@pytest.mark.asyncio
async def test_verify_credentials_success(api_client, mock_aiohttp_session):
    """Test successful credential verification."""
    from tests.conftest import mock_http_response
    mock_aiohttp_session._mock_responses['get'] = mock_http_response(
        json_data={"valid": True}, 
        status=200
    )
    
    result = await api_client.verify_credentials()
    
    assert result is True


@pytest.mark.asyncio
async def test_verify_credentials_invalid(api_client, mock_aiohttp_session):
    """Test invalid credential verification."""
    from tests.conftest import mock_http_response
    mock_aiohttp_session._mock_responses['get'] = mock_http_response(
        status=401
    )
    
    result = await api_client.verify_credentials()
    
    assert result is False


@pytest.mark.asyncio
async def test_parse_authentication_response_success(api_client):
    """Test successful authentication response parsing."""
    xml_response = """<auth>
        <token>
            <secret>test-secret-789</secret>
            <user username="john.doe" fullname="John Doe" email="john.doe@test.com" role="student" guid="test-user-123"/>
        </token>
    </auth>"""
    
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
    from tests.conftest import mock_http_response
    mock_aiohttp_session._mock_responses['post'] = mock_http_response(
        json_data={"data": {"test": "result"}},
        status=200
    )
    
    result = await api_client._graphql_query("query { test }")
    
    assert result == {"test": "result"}


@pytest.mark.asyncio
async def test_graphql_query_token_expired(api_client, mock_aiohttp_session):
    """Test GraphQL query with expired token."""
    from tests.conftest import mock_http_response
    mock_aiohttp_session._mock_responses['post'] = mock_http_response(
        status=401
    )
    
    with pytest.raises(FireflyTokenExpiredError):
        await api_client._graphql_query("query { test }")


@pytest.mark.asyncio
async def test_graphql_query_rate_limit(api_client, mock_aiohttp_session):
    """Test GraphQL query with rate limit."""
    from tests.conftest import mock_http_response
    mock_aiohttp_session._mock_responses['post'] = mock_http_response(
        status=429
    )
    
    with pytest.raises(FireflyRateLimitError):
        await api_client._graphql_query("query { test }")


@pytest.mark.asyncio
async def test_graphql_query_api_errors(api_client, mock_aiohttp_session):
    """Test GraphQL query with API errors."""
    from tests.conftest import mock_http_response
    mock_aiohttp_session._mock_responses['post'] = mock_http_response(
        json_data={"errors": [{"message": "Test error"}]},
        status=200
    )
    
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
async def test_get_tasks_success(api_client, mock_aiohttp_session, mock_tasks):
    """Test successful task retrieval."""
    from tests.conftest import mock_http_response
    mock_aiohttp_session._mock_responses['post'] = mock_http_response(
        json_data={"items": mock_tasks},
        status=200
    )
    
    result = await api_client.get_tasks()
    
    assert len(result) == len(mock_tasks)
    assert result == mock_tasks


@pytest.mark.asyncio
async def test_get_tasks_token_expired(api_client, mock_aiohttp_session):
    """Test task retrieval with expired token."""
    from tests.conftest import mock_http_response
    mock_aiohttp_session._mock_responses['post'] = mock_http_response(
        status=401
    )
    
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