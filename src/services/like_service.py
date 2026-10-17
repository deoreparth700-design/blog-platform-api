from typing import Any
from fastapi import HTTPException, status
import asyncpg
from src.repositories.like_repository import LikeRepository
from src.repositories.post_repository import PostRepository
from src.utils.user_id import parse_user_id

class LikeService:
    def __init__(self, pool: asyncpg.Pool):
        self.repository = LikeRepository(pool)
        self.post_repository = PostRepository(pool)

    async def like_post(self, post_id: int, user_id: Any) -> dict:
        user_int = parse_user_id(user_id)

        post = await self.post_repository.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        try:
            created = await self.repository.create_like(post_id, user_int)
        except asyncpg.ForeignKeyViolationError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        if not created:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Post already liked")

        return {"message": "Post liked", "post_id": post_id}

    async def unlike_post(self, post_id: int, user_id: Any) -> None:
        user_int = parse_user_id(user_id)

        post = await self.post_repository.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        exists = await self.repository.like_exists(post_id, user_int)
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Like not found")

        await self.repository.delete_like(post_id, user_int)

    async def get_like_count(self, post_id: int) -> dict:
        post = await self.post_repository.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        count = await self.repository.get_like_count(post_id)
        return {"post_id": post_id, "like_count": count}
