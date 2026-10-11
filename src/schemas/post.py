from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=20000)

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1, max_length=20000)

from src.schemas.comment import CommentResponse

class PostResponse(PostBase):
    id: int
    author_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PostDetailResponse(PostResponse):
    comments: list[CommentResponse] = []

class PaginatedPostResponse(BaseModel):
    items: list[PostResponse]
    page: int
    limit: int
    total: int
    total_pages: int

class CursorPaginatedPostResponse(BaseModel):
    items: list[PostResponse]
    next_cursor: Optional[str] = None
    has_more: bool
