from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from src.middleware.auth import get_current_user
from src.routes.posts import router as posts_router
from src.routes.comments import router as comments_router
from src.routes.likes import router as likes_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Blog Platform API is running"
    }

@app.get("/api/auth-test")
def auth_test(user: dict = Depends(get_current_user)):
    return {
        "authenticated": True,
        "userId": user.get("userId")
    }

app.include_router(posts_router, prefix="/api/posts", tags=["posts"])
app.include_router(comments_router, prefix="/api", tags=["comments"])
app.include_router(likes_router, prefix="/api", tags=["likes"])
