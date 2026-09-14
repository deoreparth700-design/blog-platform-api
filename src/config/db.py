import os
import asyncpg
from typing import Optional

# Global connection pool
pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    """
    Get the existing database connection pool, or create it if it doesn't exist.
    This pattern is safe for FastAPI startup events and dependency injection.
    """
    global pool
    if pool is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        # Create connection pool
        pool = await asyncpg.create_pool(database_url)
    
    return pool

async def close_pool():
    """
    Close the database connection pool.
    """
    global pool
    if pool is not None:
        await pool.close()
        pool = None
