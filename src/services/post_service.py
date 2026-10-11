from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
import base64
import math
from fastapi import HTTPException, status
import asyncpg
from src.repositories.post_repository import PostRepository
from src.schemas.post import PostCreate, PostUpdate

def encode_cursor(created_at: datetime, post_id: int) -> str:
    iso_str = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
    payload = f"{iso_str}|{post_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")

def decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        padded_cursor = cursor + "=" * (-len(cursor) % 4)
        decoded_bytes = base64.urlsafe_b64decode(padded_cursor.encode("utf-8"))
        decoded_str = decoded_bytes.decode("utf-8")
        parts = decoded_str.split("|")
        if len(parts) != 2:
            raise ValueError("Cursor must contain created_at and id separated by '|'")
        created_at = datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
        post_id = int(parts[1])
        return created_at, post_id
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cursor format: {str(e)}"
        )

class PostService:
    def __init__(self, pool: asyncpg.Pool):
        self.repository = PostRepository(pool)

    async def create_post(self, author_id: str, post_data: PostCreate) -> dict:
        try:
            author_uuid = UUID(author_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid author ID format")

        return await self.repository.create_post(author_uuid, post_data.title, post_data.content)

    async def get_posts(self, page: int = 1, limit: int = 10) -> dict:
        posts, total = await self.repository.get_posts(page, limit)
        total_pages = math.ceil(total / limit) if limit > 0 else 0
        return {
            "items": posts,
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages
        }

    async def get_posts_feed(self, limit: int = 10, cursor: Optional[str] = None) -> dict:
        cursor_created_at = None
        cursor_id = None
        if cursor:
            cursor_created_at, cursor_id = decode_cursor(cursor)

        items, has_more = await self.repository.get_posts_feed(
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
            limit=limit
        )

        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = encode_cursor(last_item["created_at"], last_item["id"])

        return {
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more
        }

    async def get_post_by_id(self, post_id: int) -> dict:
        post = await self.repository.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return post

    async def get_post_detail(self, post_id: int) -> dict:
        post = await self.repository.get_post_with_comments(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return post

    async def update_post(self, post_id: int, user_id: str, post_data: PostUpdate) -> dict:
        # First, ensure the post exists and the user owns it
        post = await self.get_post_by_id(post_id)
        
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        if post["author_id"] != user_uuid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this post")

        updated_post = await self.repository.update_post(post_id, post_data.title, post_data.content)
        if not updated_post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
            
        return updated_post

    async def delete_post(self, post_id: int, user_id: str) -> bool:
        # First, ensure the post exists and the user owns it
        post = await self.get_post_by_id(post_id)
        
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        if post["author_id"] != user_uuid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this post")

        deleted = await self.repository.delete_post(post_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
            
        return True
