"""Custom exceptions for the Firefly Cloud integration."""

from homeassistant.exceptions import HomeAssistantError


class FireflyException(HomeAssistantError):
    """Base exception for Firefly integration."""


class FireflyAuthenticationError(FireflyException):
    """Authentication with Firefly failed."""


class FireflyConnectionError(FireflyException):
    """Connection to Firefly failed."""


class FireflyRateLimitError(FireflyException):
    """Rate limit exceeded."""


class FireflyConfigurationError(FireflyException):
    """Invalid configuration provided."""


class FireflySchoolNotFoundError(FireflyException):
    """School not found for given code."""


class FireflyAPIError(FireflyException):
    """API returned an error response."""


class FireflyUnexpectedResponseError(FireflyException):
    """Firefly returned an unexpected HTTP status."""

    def __init__(self, message: str, status_code: int) -> None:
        """Initialise with the HTTP status code Firefly returned."""
        super().__init__(message)
        self.status_code = status_code


class FireflyTokenExpiredError(FireflyAuthenticationError):
    """Authentication token has expired."""


class FireflyDataError(FireflyException):
    """Invalid or malformed data received from API."""
