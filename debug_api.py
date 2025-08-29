#!/usr/bin/env python3
"""
Debug script for Firefly API client.

This script can be used to test and debug the Firefly API client functionality
outside of Home Assistant. Use this with the "Debug API Client" launch configuration
in VS Code.

Usage:
    python debug_api.py

Or use VS Code launch configuration: "🔧 Debug API Client"
"""
import asyncio
import logging
from datetime import datetime, timedelta

from custom_components.firefly_cloud.api import FireflyAPIClient
from custom_components.firefly_cloud.exceptions import (
    FireflyException,
    FireflySchoolNotFoundError,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_school_lookup():
    """Test school lookup functionality."""
    logger.info("Testing school lookup...")
    
    # Test with a fake school code (should fail gracefully)
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            result = await FireflyAPIClient.get_school_info(session, "testschool")
            logger.info("School lookup result: %s", result)
    except FireflySchoolNotFoundError as e:
        logger.info("Expected error for test school: %s", e)
    except Exception as e:
        logger.error("Unexpected error: %s", e)


async def test_api_client_creation():
    """Test API client creation and basic functionality."""
    logger.info("Testing API client creation...")
    
    import aiohttp
    async with aiohttp.ClientSession() as session:
        client = FireflyAPIClient(
            session=session,
            host="https://example.fireflycloud.net",
            device_id="debug-device-123",
            secret="debug-secret-456"
        )
        
        # Test auth URL generation
        auth_url = client.get_auth_url()
        logger.info("Generated auth URL: %s", auth_url)
        
        # Test user info (should fail without proper auth)
        try:
            user_info = await client.get_user_info()
            logger.info("User info: %s", user_info)
        except FireflyException as e:
            logger.info("Expected auth error: %s", e)


async def main():
    """Main debug function."""
    logger.info("🚀 Starting Firefly API debug session...")
    
    try:
        await test_school_lookup()
        await test_api_client_creation()
        
        logger.info("✅ Debug session completed successfully")
        
    except Exception as e:
        logger.error("❌ Debug session failed: %s", e, exc_info=True)


if __name__ == "__main__":
    # Run the debug session
    asyncio.run(main())