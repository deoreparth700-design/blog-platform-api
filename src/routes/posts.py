from typing import List
from fastapi import APIRouter, Depends, status, HTTPException, Query, Response
import asyncpg
import logging
from src.schemas.post import PostCreate, PostUpdate, PostResponse, PaginatedPostResponse
from src.services.post_service import PostService
from src.services.cache_service import CacheService
from src.config.db import get_pool
from src.config.redis import get_redis_client
from src.middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

def get_post_service(pool: asyncpg.Pool = Depends(get_pool)) -> PostService:
    return PostService(pool)

def get_cache_service() -> CacheService:
    """
    Create a CacheService wrapping the singleton Redis client.
    If Redis credentials are missing, this will raise ValueError
    at startup — which is intentional (fail-fast on misconfiguration).
    """
    return CacheService(get_redis_client())

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
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    service: PostService = Depends(get_post_service),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Cache-aside pattern for paginated post listing.
    
    1. Check Redis for cached result using page+limit as the cache key.
    2. If HIT: return cached data, set X-Cache: HIT.
    3. If MISS: fetch from PostgreSQL, store in cache, set X-Cache: MISS.
    
    Redis failures fall back gracefully to PostgreSQL.
    """
    cache_key = CacheService.build_posts_list_key(page, limit)

    # Step 1: Try cache
    cached = await cache.get(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    # Step 2: Cache miss — fetch from PostgreSQL
    result = await service.get_posts(page, limit)

    # Step 3: Store in cache (fire-and-forget style; failure is non-blocking)
    await cache.set(cache_key, result)

    response.headers["X-Cache"] = "MISS"
    return result

@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    response: Response,
    service: PostService = Depends(get_post_service),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Cache-aside pattern for individual post retrieval.
    
    1. Check Redis for cached post by ID.
    2. If HIT: return cached data, set X-Cache: HIT.
    3. If MISS: fetch from PostgreSQL (raises 404 if not found),
       store in cache, set X-Cache: MISS.
    
    404 responses are NOT cached — only successful results.
    Redis failures fall back gracefully to PostgreSQL.
    """
    cache_key = CacheService.build_post_item_key(post_id)

    # Step 1: Try cache
    cached = await cache.get(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    # Step 2: Cache miss — fetch from PostgreSQL (raises 404 if not found)
    result = await service.get_post_by_id(post_id)

    # Step 3: Store in cache (only reached if post exists)
    await cache.set(cache_key, result)

    response.headers["X-Cache"] = "MISS"
    return result

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
