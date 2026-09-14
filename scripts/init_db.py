import os
import sys
import asyncio
from dotenv import load_dotenv

# Add project root to Python path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.db import get_pool, close_pool

async def main():
    load_dotenv()
    
    try:
        pool = await get_pool()
        
        # Read schema file
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'db', 'schema.sql')
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
            
        async with pool.acquire() as conn:
            await conn.execute(schema_sql)
            
        print("Success: Database schema initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
