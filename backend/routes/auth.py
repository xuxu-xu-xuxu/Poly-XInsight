from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select

from backend.models.database import User, get_db
from backend.models.schemas import AuthRequest
from backend.services.auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
async def register(request: AuthRequest):
    async for db in get_db():
        result = await db.execute(select(User).where(User.username == request.username))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="用户名已存在")
        user = User(username=request.username, password_hash=hash_password(request.password))
        db.add(user)
        await db.commit()
        token = create_token(user.id, user.username)
        return {"user_id": user.id, "username": user.username, "token": token}


@router.post("/login")
async def login(request: AuthRequest):
    async for db in get_db():
        result = await db.execute(select(User).where(User.username == request.username))
        user = result.scalar_one_or_none()
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        token = create_token(user.id, user.username)
        return {"user_id": user.id, "username": user.username, "token": token}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "username": user.username}
