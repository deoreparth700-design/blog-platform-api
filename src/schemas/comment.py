from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class CommentCreate(BaseModel):
    content: str

class CommentUpdate(BaseModel):
    content: Optional[str] = None

class CommentResponse(BaseModel):
    id: int
    post_id: int
    author_id: UUID
    content: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
