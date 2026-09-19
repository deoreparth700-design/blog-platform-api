from typing import List, Optional
import asyncpg
from uuid import UUID

class PostRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_post(self, author_id: UUID, title: str, content: str) -> dict:
        query = """
            INSERT INTO posts (author_id, title, content)
            VALUES ($1, $2, $3)
            RETURNING id, author_id, title, content, created_at, updated_at
        """
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, author_id, title, content)
            return dict(row)

    async def get_posts(self, skip: int = 0, limit: int = 100) -> List[dict]:
        query = """
            SELECT id, author_id, title, content, created_at, updated_at
            FROM posts
            ORDER BY created_at DESC
            OFFSET $1 LIMIT $2
        """
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, skip, limit)
            return [dict(row) for row in rows]

    async def get_post_by_id(self, post_id: int) -> Optional[dict]:
        query = """
            SELECT id, author_id, title, content, created_at, updated_at
            FROM posts
            WHERE id = $1
        """
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, post_id)
            return dict(row) if row else None

    async def update_post(self, post_id: int, title: Optional[str], content: Optional[str]) -> Optional[dict]:
        # Build the dynamic update query
        updates = []
        values = []
        if title is not None:
            updates.append(f"title = ${len(values) + 1}")
            values.append(title)
        if content is not None:
            updates.append(f"content = ${len(values) + 1}")
            values.append(content)
            
        if not updates:
            return await self.get_post_by_id(post_id)

        updates.append(f"updated_at = now()")
        
        query = f"""
            UPDATE posts
            SET {", ".join(updates)}
            WHERE id = ${len(values) + 1}
            RETURNING id, author_id, title, content, created_at, updated_at
        """
        values.append(post_id)
        
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, *values)
            return dict(row) if row else None

    async def delete_post(self, post_id: int) -> bool:
        query = """
            DELETE FROM posts
            WHERE id = $1
            RETURNING id
        """
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, post_id)
            return row is not None
