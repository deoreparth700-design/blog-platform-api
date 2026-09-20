from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
import asyncpg
from src.repositories.comment_repository import CommentRepository
from src.repositories.post_repository import PostRepository
from src.schemas.comment import CommentCreate, CommentUpdate

class CommentService:
    def __init__(self, pool: asyncpg.Pool):
        self.repository = CommentRepository(pool)
        self.post_repository = PostRepository(pool)

    async def create_comment(self, post_id: int, user_id: str, comment_data: CommentCreate) -> dict:
        post = await self.post_repository.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
            
        try:
            author_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        return await self.repository.create_comment(post_id, author_uuid, comment_data.content)

    async def get_comments_by_post_id(self, post_id: int) -> List[dict]:
        post = await self.post_repository.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
            
        return await self.repository.get_comments_by_post_id(post_id)

    async def get_comment_by_id(self, comment_id: int) -> dict:
        comment = await self.repository.get_comment_by_id(comment_id)
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        return comment

    async def update_comment(self, comment_id: int, user_id: str, comment_data: CommentUpdate) -> dict:
        comment = await self.get_comment_by_id(comment_id)
        
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        if comment["author_id"] != user_uuid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this comment")

        updated_comment = await self.repository.update_comment(comment_id, comment_data.content)
        if not updated_comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
            
        return updated_comment

    async def delete_comment(self, comment_id: int, user_id: str) -> bool:
        comment = await self.get_comment_by_id(comment_id)
        
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        if comment["author_id"] != user_uuid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this comment")

        deleted = await self.repository.delete_comment(comment_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
            
        return True
