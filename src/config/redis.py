"""
Redis Configuration

Initializes and manages the Upstash Redis async client.
Loads credentials from environment variables:
  - UPSTASH_REDIS_REST_URL
  - UPSTASH_REDIS_REST_TOKEN

The Upstash Redis Python SDK is HTTP-based (REST over HTTPS),
so there is no persistent TCP connection or traditional connection pool.
A single client instance is reused across the application.
"""

import os
import logging
from upstash_redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    """
    Get the singleton async Redis client.

    On first call, validates that the required environment variables are set
    and creates the client. Subsequent calls return the same instance.

    Raises:
        ValueError: If UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN
                    environment variables are missing.
    """
    global _redis_client

    if _redis_client is None:
        url = os.environ.get("UPSTASH_REDIS_REST_URL")
        token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

        if not url:
            raise ValueError(
                "UPSTASH_REDIS_REST_URL environment variable is not set. "
                "Please configure your Upstash Redis credentials in .env"
            )
        if not token:
            raise ValueError(
                "UPSTASH_REDIS_REST_TOKEN environment variable is not set. "
                "Please configure your Upstash Redis credentials in .env"
            )

        _redis_client = Redis(url=url, token=token)
        logger.info("Upstash Redis client initialized successfully")

    return _redis_client


async def close_redis_client():
    """
    Clean up the Redis client reference.

    The Upstash SDK is HTTP-based (stateless REST calls), so there is no
    persistent connection to close. This function resets the global reference
    for clean application shutdown.
    """
    global _redis_client
    _redis_client = None
    logger.info("Redis client reference cleared")
