import asyncpg
from uuid import UUID

class LikeRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_like(self, post_id: int, user_id: UUID) -> None:
        query = """
            INSERT INTO likes (post_id, user_id)
            VALUES ($1, $2)
        """
        async with self.pool.acquire() as connection:
            await connection.execute(query, post_id, user_id)

    async def delete_like(self, post_id: int, user_id: UUID) -> bool:
        query = """
            DELETE FROM likes
            WHERE post_id = $1 AND user_id = $2
            RETURNING post_id
        """
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, post_id, user_id)
            return row is not None

    async def get_like_count(self, post_id: int) -> int:
        query = """
            SELECT COUNT(*)
            FROM likes
            WHERE post_id = $1
        """
        async with self.pool.acquire() as connection:
            count = await connection.fetchval(query, post_id)
            return count

    async def like_exists(self, post_id: int, user_id: UUID) -> bool:
        query = """
            SELECT 1
            FROM likes
            WHERE post_id = $1 AND user_id = $2
        """
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, post_id, user_id)
            return row is not None
