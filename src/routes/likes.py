from fastapi import APIRouter, Depends, status, HTTPException
import asyncpg
from src.schemas.like import LikeCountResponse
from src.services.like_service import LikeService
from src.config.db import get_pool
from src.middleware.auth import get_current_user

router = APIRouter()

def get_like_service(pool: asyncpg.Pool = Depends(get_pool)) -> LikeService:
    return LikeService(pool)

@router.post("/posts/{post_id}/like", status_code=status.HTTP_201_CREATED)
async def like_post(
    post_id: int,
    current_user: dict = Depends(get_current_user),
    service: LikeService = Depends(get_like_service)
):
    user_id = current_user.get("userId")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token")
    
    return await service.like_post(post_id, user_id)

@router.delete("/posts/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def unlike_post(
    post_id: int,
    current_user: dict = Depends(get_current_user),
    service: LikeService = Depends(get_like_service)
):
    user_id = current_user.get("userId")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token")
        
    await service.unlike_post(post_id, user_id)

@router.get("/posts/{post_id}/likes", response_model=LikeCountResponse, status_code=status.HTTP_200_OK)
async def get_like_count(
    post_id: int,
    service: LikeService = Depends(get_like_service)
):
    return await service.get_like_count(post_id)
