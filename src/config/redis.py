"""
Redis configuration supporting local Redis and Upstash REST.

Set REDIS_URL to use a standard Redis server.
If REDIS_URL is absent, use the existing Upstash REST configuration.
"""

import os
import logging
from typing import Any

from dotenv import load_dotenv
from redis.asyncio import Redis as LocalRedis
from upstash_redis.asyncio import Redis as UpstashRedis

logger = logging.getLogger(__name__)

_redis_client: Any | None = None
_using_local_redis = False


def get_redis_client():
    """Return the shared local Redis or Upstash client."""
    global _redis_client, _using_local_redis

    if _redis_client is None:
        load_dotenv()

        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            _redis_client = LocalRedis.from_url(
                redis_url,
                decode_responses=True,
            )
            _using_local_redis = True
            logger.info("Local Redis client initialized")
        else:
            url = os.environ.get("UPSTASH_REDIS_REST_URL")
            token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

            if url:
                url = url.strip().strip('"\'')
            if token:
                token = token.strip().strip('"\'')

            if not url:
                raise ValueError(
                    "Set REDIS_URL or UPSTASH_REDIS_REST_URL."
                )
            if not token:
                raise ValueError(
                    "UPSTASH_REDIS_REST_TOKEN is required when using Upstash."
                )

            _redis_client = UpstashRedis(url=url, token=token)
            _using_local_redis = False
            logger.info("Upstash Redis client initialized")

    return _redis_client


async def close_redis_client():
    """Close local Redis connections and reset the shared client."""
    global _redis_client, _using_local_redis

    client = _redis_client
    using_local = _using_local_redis

    try:
        if client is not None and using_local:
            await client.aclose()
    finally:
        _redis_client = None
        _using_local_redis = False

    logger.info("Redis client reference cleared")
