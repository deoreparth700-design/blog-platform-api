from typing import List
from fastapi import APIRouter, Depends, status, HTTPException, Query
import asyncpg
from src.schemas.post import PostCreate, PostUpdate, PostResponse, PaginatedPostResponse
from src.services.post_service import PostService
from src.config.db import get_pool
from src.middleware.auth import get_current_user

router = APIRouter()

def get_post_service(pool: asyncpg.Pool = Depends(get_pool)) -> PostService:
    return PostService(pool)

@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    current_user: dict = Depends(get_current_user),
    service: PostService = Depends(get_post_service)
):
    user_id = current_user.get("userId")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token")
    
    return await service.create_post(user_id, post_data)

@router.get("/", response_model=PaginatedPostResponse)
async def get_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    service: PostService = Depends(get_post_service)
):
    return await service.get_posts(page, limit)

@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    service: PostService = Depends(get_post_service)
):
    return await service.get_post_by_id(post_id)

@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: dict = Depends(get_current_user),
    service: PostService = Depends(get_post_service)
):
    user_id = current_user.get("userId")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token")
        
    return await service.update_post(post_id, user_id, post_data)

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: dict = Depends(get_current_user),
    service: PostService = Depends(get_post_service)
):
    user_id = current_user.get("userId")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token")
        
    await service.delete_post(post_id, user_id)
