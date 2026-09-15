from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from src.middleware.auth import get_current_user

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
