import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.db import get_pool, close_pool

async def main():
    load_dotenv()
    
    try:
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            # Execute simple query
            server_time = await conn.fetchval('SELECT NOW();')
            
        print("Success: PostgreSQL/Neon is reachable.")
        print(f"Server timestamp: {server_time}")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
