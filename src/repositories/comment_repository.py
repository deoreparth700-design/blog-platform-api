from typing import List, Optional
import asyncpg
from uuid import UUID

class CommentRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_comment(self, post_id: int, author_id: UUID, content: str) -> dict:
        query = """
            INSERT INTO comments (post_id, author_id, content)
            VALUES ($1, $2, $3)
            RETURNING id, post_id, author_id, content, created_at
        """
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, post_id, author_id, content)
            return dict(row)

    async def get_comments_by_post_id(self, post_id: int) -> List[dict]:
        query = """
            SELECT id, post_id, author_id, content, created_at
            FROM comments
            WHERE post_id = $1
            ORDER BY created_at ASC, id ASC
        """
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, post_id)
            return [dict(row) for row in rows]

    async def get_comment_by_id(self, comment_id: int) -> Optional[dict]:
        query = """
            SELECT id, post_id, author_id, content, created_at
            FROM comments
            WHERE id = $1
        """
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, comment_id)
            return dict(row) if row else None

    async def update_comment(self, comment_id: int, content: Optional[str]) -> Optional[dict]:
        if content is None:
            return await self.get_comment_by_id(comment_id)
            
        query = """
            UPDATE comments
            SET content = $1
            WHERE id = $2
            RETURNING id, post_id, author_id, content, created_at
        """
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, content, comment_id)
            return dict(row) if row else None

    async def delete_comment(self, comment_id: int) -> bool:
        query = """
            DELETE FROM comments
            WHERE id = $1
            RETURNING id
        """
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, comment_id)
            return row is not None
