from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
import asyncpg
from src.repositories.post_repository import PostRepository
from src.schemas.post import PostCreate, PostUpdate

class PostService:
    def __init__(self, pool: asyncpg.Pool):
        self.repository = PostRepository(pool)

    async def create_post(self, author_id: str, post_data: PostCreate) -> dict:
        try:
            author_uuid = UUID(author_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid author ID format")

        return await self.repository.create_post(author_uuid, post_data.title, post_data.content)

    async def get_posts(self, skip: int = 0, limit: int = 100) -> List[dict]:
        return await self.repository.get_posts(skip, limit)

    async def get_post_by_id(self, post_id: int) -> dict:
        post = await self.repository.get_post_by_id(post_id)
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
