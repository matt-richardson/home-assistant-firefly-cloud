"""Firefly Cloud API client."""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from uuid import uuid4

import aiohttp
import async_timeout
from lxml import etree

from .const import (
    DEFAULT_APP_ID,
    FIREFLY_API_VERSION_PATH,
    FIREFLY_APP_GATEWAY,
    FIREFLY_GRAPHQL_PATH,
    FIREFLY_VERIFY_TOKEN_PATH,
    MAX_RETRIES,
    RETRY_DELAY_BASE,
    TASK_ARCHIVE_ALL,
    TASK_OWNER_ONLY_SETTERS,
    TASK_STATUS_TODO,
    TIMEOUT_SECONDS,
)
from .exceptions import (
    FireflyAPIError,
    FireflyAuthenticationError,
    FireflyConnectionError,
    FireflyDataError,
    FireflyRateLimitError,
    FireflySchoolNotFoundError,
    FireflyTokenExpiredError,
)


class FireflyAPIClient:
    """Firefly Cloud API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        device_id: str,
        secret: str,
        app_id: str = DEFAULT_APP_ID,
        user_guid: Optional[str] = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._host = host.rstrip("/")
        self._device_id = device_id
        self._secret = secret
        self._app_id = app_id
        self._user_info: Optional[Dict[str, Any]] = None

        # If user_guid is provided, create minimal user info
        if user_guid:
            self._user_info = {"guid": user_guid}

    @classmethod
    async def get_school_info(
        cls, session: aiohttp.ClientSession, school_code: str
    ) -> Dict[str, Any]:
        """Get school information from school code."""
        if not school_code:
            raise FireflySchoolNotFoundError("Invalid school code")

        url = f"{FIREFLY_APP_GATEWAY}{school_code}"

        try:
            async with async_timeout.timeout(TIMEOUT_SECONDS):
                async with session.get(url) as response:
                    response.raise_for_status()
                    content = await response.text()
        except asyncio.TimeoutError as err:
            raise FireflyConnectionError(
                "Timeout connecting to Firefly") from err
        except aiohttp.ClientError as err:
            raise FireflyConnectionError(
                f"Error connecting to Firefly: {err}") from err

        try:
            response_elem = etree.fromstring(content.encode())

            if response_elem is None or response_elem.get("exists") == "false":
                raise FireflySchoolNotFoundError(
                    f"School not found: {school_code}")

            address_elem = response_elem.find("address")
            if address_elem is None:
                raise FireflyDataError("Invalid school data received")

            host = address_elem.text
            ssl = address_elem.get("ssl", "false") == "true"
            url = f"{'https' if ssl else 'http'}://{host}"
            device_id = str(uuid4())

            token_url = quote(
                f"{url}/Login/api/gettoken?"
                f"ffauth_device_id={device_id}&ffauth_secret="
                f"&device_id={device_id}&app_id={DEFAULT_APP_ID}"
            )

            name_elem = response_elem.find("name")
            id_elem = response_elem.find("installationId")

            if name_elem is None or id_elem is None:
                raise FireflyDataError("Missing required school data")

            return {
                "enabled": response_elem.get("enabled", "false") == "true",
                "name": name_elem.text,
                "id": id_elem.text,
                "host": host,
                "ssl": ssl,
                "url": url,
                "token_url": f"{url}/login/login.aspx?prelogin={token_url}",
                "device_id": device_id,
            }

        except etree.XMLSyntaxError as err:
            raise FireflyDataError(f"Invalid XML response: {err}") from err

    async def get_api_version(self) -> Dict[str, int]:
        """Get the API version."""
        url = f"{self._host}{FIREFLY_API_VERSION_PATH}"

        try:
            async with async_timeout.timeout(TIMEOUT_SECONDS):
                async with self._session.get(url) as response:
                    response.raise_for_status()
                    content = await response.text()
        except asyncio.TimeoutError as err:
            raise FireflyConnectionError(
                "Timeout getting API version") from err
        except aiohttp.ClientError as err:
            raise FireflyConnectionError(
                f"Error getting API version: {err}") from err

        try:
            version_elem = etree.fromstring(content.encode())

            if version_elem is None:
                raise FireflyDataError("Invalid version response")

            major_elem = version_elem.find("majorVersion")
            minor_elem = version_elem.find("minorVersion")
            increment_elem = version_elem.find("incrementVersion")

            if major_elem is None or minor_elem is None or increment_elem is None:
                raise FireflyDataError("Missing version data")

            if major_elem.text is None or minor_elem.text is None or increment_elem.text is None:
                raise FireflyDataError("Empty version data")

            return {
                "major": int(major_elem.text),
                "minor": int(minor_elem.text),
                "increment": int(increment_elem.text),
            }
        except (etree.XMLSyntaxError, ValueError, AttributeError) as err:
            raise FireflyDataError(f"Invalid version data: {err}") from err

    async def verify_credentials(self) -> bool:
        """Verify that the stored credentials are valid."""
        url = f"{self._host}{FIREFLY_VERIFY_TOKEN_PATH}"
        params = {
            "ffauth_device_id": self._device_id,
            "ffauth_secret": self._secret,
        }

        try:
            async with async_timeout.timeout(TIMEOUT_SECONDS):
                async with self._session.get(url, params=params) as response:
                    if response.status == 401:
                        return False
                    response.raise_for_status()
                    data = await response.json()
                    return data.get("valid", False)
        except asyncio.TimeoutError as err:
            raise FireflyConnectionError(
                "Timeout verifying credentials") from err
        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                return False
            raise FireflyAuthenticationError(
                f"Authentication error: {err}") from err
        except aiohttp.ClientError as err:
            raise FireflyConnectionError(
                f"Error verifying credentials: {err}") from err

    async def parse_authentication_response(self, xml_response: str) -> Dict[str, Any]:
        """Parse the authentication response and extract user info and secret."""
        if not xml_response:
            raise FireflyAuthenticationError("Empty authentication response")

        # Clean up the response (remove quotes and escape characters)
        xml_response = xml_response.strip()
        if xml_response.startswith('"') and xml_response.endswith('"'):
            xml_response = xml_response[1:-1]
        xml_response = xml_response.replace('\\"', '"').replace("\\\\", "\\")

        try:
            token_elem = etree.fromstring(xml_response.encode())

            if token_elem is None:
                raise FireflyAuthenticationError(
                    "Invalid authentication response")

            secret_elem = token_elem.find("secret")
            user_elem = token_elem.find("user")

            if secret_elem is None or user_elem is None:
                raise FireflyAuthenticationError("Missing authentication data")

            if secret_elem.text is None:
                raise FireflyAuthenticationError("Empty secret in authentication response")

            user_info = {
                "username": user_elem.get("username"),
                "fullname": user_elem.get("fullname"),
                "email": user_elem.get("email"),
                "role": user_elem.get("role"),
                "guid": user_elem.get("guid"),
            }

            self._secret = secret_elem.text
            self._user_info = user_info

            return {
                "secret": secret_elem.text,
                "user": user_info,
            }

        except etree.XMLSyntaxError as err:
            raise FireflyAuthenticationError(
                f"Invalid XML in auth response: {err}") from err

    async def _graphql_query(self, query: str) -> Dict[str, Any]:
        """Execute a GraphQL query."""
        url = f"{self._host}{FIREFLY_GRAPHQL_PATH}"
        params = {
            "ffauth_device_id": self._device_id,
            "ffauth_secret": self._secret,
        }
        data = f"data={quote(query)}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        for attempt in range(MAX_RETRIES):
            try:
                async with async_timeout.timeout(TIMEOUT_SECONDS):
                    async with self._session.post(
                        url, params=params, data=data, headers=headers
                    ) as response:
                        if response.status == 401:
                            raise FireflyTokenExpiredError(
                                "Authentication token expired")
                        if response.status == 429:
                            raise FireflyRateLimitError("Rate limit exceeded")

                        response.raise_for_status()
                        result = await response.json()

                        if "errors" in result:
                            raise FireflyAPIError(
                                f"GraphQL errors: {result['errors']}")

                        return result.get("data", {})

            except asyncio.TimeoutError as exc:
                if attempt == MAX_RETRIES - 1:
                    raise FireflyConnectionError(
                        "Timeout executing GraphQL query") from exc
                await asyncio.sleep(RETRY_DELAY_BASE ** attempt)
                continue
            except (FireflyTokenExpiredError, FireflyRateLimitError):  # pylint: disable=try-except-raise
                raise
            except aiohttp.ClientError as err:
                if attempt == MAX_RETRIES - 1:
                    raise FireflyConnectionError(
                        f"Error executing query: {err}") from err
                await asyncio.sleep(RETRY_DELAY_BASE ** attempt)
                continue

        # This should never be reached due to MAX_RETRIES logic, but satisfy type checker
        raise FireflyConnectionError("Failed to execute GraphQL query after all retries")

    async def get_user_info(self) -> Dict[str, Any]:
        """Get current user information."""
        if self._user_info:
            return self._user_info

        # User info should be provided during initialization from stored config
        # If we don't have it, we need to re-authenticate
        raise FireflyAuthenticationError("No user information available")

    async def get_children_info(self) -> List[Dict[str, Any]]:
        """Get children information if authenticated user is a parent."""
        if not self._user_info:
            raise FireflyAuthenticationError("No user information available")

        # If user role is student, return themselves as the only "child"
        if self._user_info.get("role") == "student":
            return [self._user_info]

        # If user role is parent, query for their children
        query = f"""
        query GetChildren {{
            users(guid: "{self._user_info['guid']}") {{
                children {{
                    guid,
                    username,
                    name
                }}
            }}
        }}
        """
        response = await self._graphql_query(query)
        users_data = response["users"]

        if not users_data or not users_data[0].get("children"):
            # If no children found, return empty list
            return []

        return users_data[0]["children"]

    async def get_events(
        self, start: datetime, end: datetime, user_guid: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get calendar events for a date range."""
        if not user_guid and self._user_info:
            user_guid = self._user_info["guid"]

        if not user_guid:
            raise FireflyAuthenticationError("No user GUID available")

        # struggling a bit with getting the events via graphql
        # query - 500 internal server error
        # Use the REST API for timetable data
        return await self._get_events_rest_api(start, end, user_guid)

    async def _get_events_rest_api(
        self, start: datetime, end: datetime, user_guid: str
    ) -> List[Dict[str, Any]]:
        """Get events using the REST API timetable endpoint."""
        # Determine the time period (week/day) based on date range
        days_diff = (end - start).days
        if days_diff <= 1:
            period = "day"
        else:
            period = "week"

        url = f"{self._host}/api/v3/timetable/{user_guid}/{period}"
        params = {
            "ffauth_device_id": self._device_id,
            "ffauth_secret": self._secret,
            "datetime": start.strftime('%Y-%m-%dT%H:%M')
        }

        for attempt in range(MAX_RETRIES):
            try:
                async with async_timeout.timeout(TIMEOUT_SECONDS):
                    async with self._session.get(url, params=params) as response:
                        if response.status == 401:
                            raise FireflyTokenExpiredError(
                                "Authentication token expired")
                        if response.status == 429:
                            raise FireflyRateLimitError("Rate limit exceeded")

                        response.raise_for_status()
                        events_data = await response.json()

                        # Convert REST API format to match GraphQL format
                        converted_events = []
                        for event in events_data:
                            converted_event = {
                                "guid": event.get("guid"),
                                "start": event.get("startUtc", event.get("startZoned")),
                                "end": event.get("endUtc", event.get("endZoned")),
                                "location": event.get("location", ""),
                                "subject": event.get("subject", ""),
                                "description": event.get("description", ""),
                                "attendees": [
                                    {
                                        "role": str(attendee.get("role", "")),
                                        "principal": {
                                            "guid": attendee.get("guid", {}).get("value", ""),
                                            "name": attendee.get("name", "")
                                        }
                                    }
                                    for attendee in event.get("attendees", [])
                                ]
                            }
                            converted_events.append(converted_event)

                        return converted_events

            except asyncio.TimeoutError as exc:
                if attempt == MAX_RETRIES - 1:
                    raise FireflyConnectionError(
                        "Timeout getting events via REST API") from exc
                await asyncio.sleep(RETRY_DELAY_BASE ** attempt)
                continue
            except (FireflyTokenExpiredError, FireflyRateLimitError):  # pylint: disable=try-except-raise
                raise
            except aiohttp.ClientError as err:
                if attempt == MAX_RETRIES - 1:
                    raise FireflyConnectionError(
                        f"Error getting events via REST API: {err}") from err
                await asyncio.sleep(RETRY_DELAY_BASE ** attempt)
                continue

        # Should never reach here due to exception handling above
        return []

    async def get_tasks(
        self,
        student_guid: Optional[str] = None,
        page: int = 0,
        page_size: int = 100,
        completion_status: str = TASK_STATUS_TODO,
        owner_type: str = TASK_OWNER_ONLY_SETTERS,
        archive_status: str = TASK_ARCHIVE_ALL,
        sorting_criteria: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """Get tasks/assignments."""
        if sorting_criteria is None:
            sorting_criteria = [{"column": "DueDate", "order": "Descending"}]

        url = f"{self._host}/api/v2/taskListing/view/parent/tasks/all/filterBy"
        params = {
            "ffauth_device_id": self._device_id,
            "ffauth_secret": self._secret,
        }

        payload = {
            "ownerType": owner_type,
            "page": page,
            "pageSize": page_size,
            "archiveStatus": archive_status,
            "completionStatus": completion_status,
            "readStatus": "All",
            "markingStatus": "All",
            "sortingCriteria": sorting_criteria,
        }

        # Add student GUID filter if provided (for parent accounts)
        if student_guid:
            payload["forStudentGuid"] = student_guid

        for attempt in range(MAX_RETRIES):
            try:
                async with async_timeout.timeout(TIMEOUT_SECONDS):
                    async with self._session.post(
                        url, params=params, json=payload
                    ) as response:
                        if response.status == 401:
                            raise FireflyTokenExpiredError(
                                "Authentication token expired")
                        if response.status == 429:
                            raise FireflyRateLimitError("Rate limit exceeded")

                        response.raise_for_status()
                        data = await response.json()
                        return data.get("items", [])

            except asyncio.TimeoutError as exc:
                if attempt == MAX_RETRIES - 1:
                    raise FireflyConnectionError("Timeout getting tasks") from exc
                await asyncio.sleep(RETRY_DELAY_BASE ** attempt)
                continue
            except (FireflyTokenExpiredError, FireflyRateLimitError):  # pylint: disable=try-except-raise
                raise
            except aiohttp.ClientError as err:
                if attempt == MAX_RETRIES - 1:
                    raise FireflyConnectionError(
                        f"Error getting tasks: {err}") from err
                await asyncio.sleep(RETRY_DELAY_BASE ** attempt)
                continue

        # Should never reach here due to exception handling above
        return []

    async def get_participating_groups(
        self, user_guid: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get groups/classes the user participates in."""
        if not user_guid and self._user_info:
            user_guid = self._user_info["guid"]

        if not user_guid:
            raise FireflyAuthenticationError("No user GUID available")

        query = f"""
        query GetGroups {{
            users(guid: "{user_guid}") {{
                participating_in {{
                    guid,
                    sort_key,
                    name,
                    personal_colour
                }}
            }}
        }}
        """

        data = await self._graphql_query(query)
        users = data.get("users", [])
        if not users:
            return []

        return users[0].get("participating_in", [])

    def get_auth_url(self) -> str:
        """Get the authentication URL for browser redirect."""
        redirect = quote(
            f"{self._host}/Login/api/gettoken?"
            f"ffauth_device_id={self._device_id}&ffauth_secret="
            f"&device_id={self._device_id}&app_id={self._app_id}"
        )
        return f"{self._host}/login/login.aspx?prelogin={redirect}"
