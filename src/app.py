import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.middleware.auth import get_current_user
from src.routes.posts import router as posts_router
from src.routes.comments import router as comments_router
from src.routes.likes import router as likes_router
from src.config.db import close_pool
from src.config.redis import close_redis_client

FRONTEND_PATH = Path("frontend/index.html")
if not FRONTEND_PATH.exists():
    FRONTEND_PATH = Path(__file__).resolve().parent.parent / "frontend" / "index.html"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: lazy initialization is preserved
    yield
    # Shutdown: clean up DB connection pool and Redis client reference
    await close_pool()
    await close_redis_client()


def parse_allowed_origins(raw_origins: str | None) -> list[str]:
    """Parse comma-separated origins, stripping whitespace and filtering empty entries."""
    if not raw_origins:
        return []
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


def create_app(allowed_origins: list[str] | None = None) -> FastAPI:
    """Application factory configuring routes and strict CORS policies."""
    app = FastAPI(lifespan=lifespan)

    if allowed_origins is None:
        raw_origins = os.environ.get("ALLOWED_ORIGINS")
        allowed_origins = parse_allowed_origins(raw_origins)

    # Never combine wildcard "*" with allow_credentials=True
    allow_credentials = bool(allowed_origins and "*" not in allowed_origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health_check():
        return {
            "status": "ok",
            "message": "Blog Platform API is running"
        }

    @app.get("/app", response_class=FileResponse)
    def serve_frontend():
        return FileResponse(FRONTEND_PATH, media_type="text/html")

    @app.get("/api/auth-test")
    def auth_test(user: dict = Depends(get_current_user)):
        return {
            "authenticated": True,
            "userId": user.get("userId")
        }

    app.include_router(posts_router, prefix="/api/posts", tags=["posts"])
    app.include_router(comments_router, prefix="/api", tags=["comments"])
    app.include_router(likes_router, prefix="/api", tags=["likes"])

    return app


app = create_app()
