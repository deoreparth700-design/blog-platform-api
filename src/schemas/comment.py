from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class CommentUpdate(BaseModel):
    content: Optional[str] = Field(default=None, min_length=1, max_length=2000)

class CommentResponse(BaseModel):
    id: int
    post_id: int
    author_id: UUID
    content: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
