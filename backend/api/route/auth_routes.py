# backend/api/routes/auth_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from database import get_db, User
from api.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    username: str
    email:    str
    password: str

@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="帳號已存在")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email 已被使用")

    user = User(
        username        = req.username,
        email           = req.email,
        hashed_password = hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "註冊成功", "username": user.username}

@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "email": current_user.email}