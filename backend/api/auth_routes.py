# backend/api/route/auth_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from database import get_db, User
from api.auth import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI")
FRONTEND_URL         = os.getenv("FRONTEND_URL", "http://localhost:5173")

# ── Step 1：把使用者導向 Google 登入頁 ────────────────────────
@router.get("/google")
def google_login():
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid email profile"
        "&access_type=offline"
    )
    return RedirectResponse(url=google_auth_url)


# ── Step 2：Google 導回來，拿 code 換 token ───────────────────
@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    # 用 code 換 access_token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code":          code,
                "client_id":     GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri":  GOOGLE_REDIRECT_URI,
                "grant_type":    "authorization_code",
            }
        )
        token_data = token_response.json()

        if "error" in token_data:
            raise HTTPException(status_code=400, detail="Google 驗證失敗")

        # 用 access_token 取得使用者資料
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
        google_user = user_response.json()

    # 查資料庫有沒有這個使用者，沒有就新增
    user = db.query(User).filter(User.google_id == google_user["id"]).first()

    if not user:
        user = User(
            google_id  = google_user["id"],
            email      = google_user["email"],
            username   = google_user["name"],
            avatar_url = google_user.get("picture"), 
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 產生我們自己的 JWT
    access_token = create_access_token({"sub": user.email})

    # 把 token 帶回前端
    return RedirectResponse(
        url=f"{FRONTEND_URL}/auth/callback?token={access_token}"
    )


# ── 取得目前登入使用者資訊 ────────────────────────────────────
@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "username":   current_user.username,
        "email":      current_user.email,
        "avatar_url": current_user.avatar_url,
    }