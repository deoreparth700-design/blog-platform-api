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

    async def get_posts(self, page: int = 1, limit: int = 10) -> tuple[List[dict], int]:
        offset = (page - 1) * limit
        query = """
            SELECT id, author_id, title, content, created_at, updated_at
            FROM posts
            ORDER BY created_at DESC, id DESC
            OFFSET $1 LIMIT $2
        """
        count_query = "SELECT COUNT(*) FROM posts"
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, offset, limit)
            total = await connection.fetchval(count_query)
            return [dict(row) for row in rows], total

    async def get_post_by_id(self, post_id: int) -> Optional[dict]:
        query = """
            SELECT id, author_id, title, content, created_at, updated_at
            FROM posts
            WHERE id = $1
        """
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, post_id)
            return dict(row) if row else None

    async def get_post_with_comments(self, post_id: int) -> Optional[dict]:
        # Note: comments are ordered by created_at, id and are not paginated yet.
        query = """
            SELECT 
                p.id,
                p.author_id,
                p.title,
                p.content,
                p.created_at,
                p.updated_at,
                c.id AS comment_id,
                c.post_id AS comment_post_id,
                c.author_id AS comment_author_id,
                c.content AS comment_content,
                c.created_at AS comment_created_at
            FROM posts p
            LEFT JOIN comments c ON p.id = c.post_id
            WHERE p.id = $1
            ORDER BY c.created_at ASC, c.id ASC
        """
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, post_id)
            if not rows:
                return None

            first = rows[0]
            post = {
                "id": first["id"],
                "author_id": first["author_id"],
                "title": first["title"],
                "content": first["content"],
                "created_at": first["created_at"],
                "updated_at": first["updated_at"],
                "comments": [],
            }
            for row in rows:
                if row["comment_id"] is not None:
                    post["comments"].append({
                        "id": row["comment_id"],
                        "post_id": row["comment_post_id"],
                        "author_id": row["comment_author_id"],
                        "content": row["comment_content"],
                        "created_at": row["comment_created_at"],
                    })
            return post

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
