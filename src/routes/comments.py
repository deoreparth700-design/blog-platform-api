from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
import asyncpg
from src.schemas.comment import CommentCreate, CommentUpdate, CommentResponse
from src.services.comment_service import CommentService
from src.config.db import get_pool
from src.middleware.auth import get_current_user

router = APIRouter()

def get_comment_service(pool: asyncpg.Pool = Depends(get_pool)) -> CommentService:
    return CommentService(pool)

@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    comment_data: CommentCreate,
    current_user: dict = Depends(get_current_user),
    service: CommentService = Depends(get_comment_service)
):
    user_id = current_user.get("userId")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token")
    
    return await service.create_comment(post_id, user_id, comment_data)

@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
async def get_comments(
    post_id: int,
    service: CommentService = Depends(get_comment_service)
):
    return await service.get_comments_by_post_id(post_id)

@router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: int,
    comment_data: CommentUpdate,
    current_user: dict = Depends(get_current_user),
    service: CommentService = Depends(get_comment_service)
):
    user_id = current_user.get("userId")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token")
        
    return await service.update_comment(comment_id, user_id, comment_data)

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    current_user: dict = Depends(get_current_user),
    service: CommentService = Depends(get_comment_service)
):
    user_id = current_user.get("userId")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token")
        
    await service.delete_comment(comment_id, user_id)
