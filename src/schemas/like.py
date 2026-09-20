from pydantic import BaseModel

class LikeCountResponse(BaseModel):
    post_id: int
    like_count: int
