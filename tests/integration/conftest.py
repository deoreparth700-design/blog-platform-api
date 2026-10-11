"""
Integration test fixtures and configuration.

Safety rules:
- Skips if TEST_DATABASE_URL is not set.
- Refuses to run (raises RuntimeError) if TEST_DATABASE_URL == DATABASE_URL.
- Connects to TEST_DATABASE_URL, executes src/db/schema.sql, and truncates
  tables with RESTART IDENTITY CASCADE before each test.
- Uses real repositories and services. Only Redis is replaced with FakeRedis.
"""

import os
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import pytest
import asyncpg
from dotenv import load_dotenv
import httpx

from src.app import app
from src.config.db import get_pool
from src.routes.posts import get_cache_service
from src.services.cache_service import CacheService
from tests.conftest import FakeRedis

# Load .env to make sure DATABASE_URL is available for collision check
load_dotenv()

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL")
PROD_DB_URL = os.environ.get("DATABASE_URL")

# Check 1: Skip if TEST_DATABASE_URL is not set
if not TEST_DB_URL:
    pytest.skip("TEST_DATABASE_URL not set; skipping integration tests", allow_module_level=True)

# Check 2: Refuse to run if TEST_DATABASE_URL equals production DATABASE_URL
if PROD_DB_URL and TEST_DB_URL == PROD_DB_URL:
    raise RuntimeError("TEST_DATABASE_URL cannot be identical to production DATABASE_URL")


def _strip_channel_binding(url: str) -> str:
    parsed = urlparse(url)
    params = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k != "channel_binding"]
    return urlunparse(parsed._replace(query=urlencode(params)))


CLEANED_TEST_DB_URL = _strip_channel_binding(TEST_DB_URL)

_schema_applied = False


@pytest.fixture
async def test_pool():
    """Create a connection pool to the dedicated test database in the current event loop."""
    global _schema_applied
    pool = await asyncpg.create_pool(CLEANED_TEST_DB_URL)
    if not _schema_applied:
        schema_path = Path(__file__).resolve().parent.parent.parent / "src" / "db" / "schema.sql"
        async with pool.acquire() as conn:
            await conn.execute(schema_path.read_text(encoding="utf-8"))
        _schema_applied = True
    yield pool
    await pool.close()


@pytest.fixture(autouse=True)
async def clean_tables(test_pool):
    """Truncate all application tables before each integration test for full test isolation."""
    async with test_pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE posts, comments, likes RESTART IDENTITY CASCADE;")
    yield


@pytest.fixture
def integration_cache() -> CacheService:
    """FakeRedis-backed CacheService for caching in integration tests."""
    return CacheService(FakeRedis())


@pytest.fixture
async def integration_client(test_pool, integration_cache):
    """
    httpx.AsyncClient wired to the real PostgreSQL test pool and FakeRedis via ASGITransport.
    Runs in the same event loop as test_pool and guarantees cleanup of dependency overrides.
    """
    app.dependency_overrides[get_pool] = lambda: test_pool
    app.dependency_overrides[get_cache_service] = lambda: integration_cache
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
