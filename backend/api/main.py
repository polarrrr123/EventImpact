# backend/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys, os

# 把專案根目錄和 backend 都加進 path
ROOT    = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
BACKEND = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, BACKEND)

from api.intent_parser import parse_intent, generate_followup_question
from api.conversation_manager import ConversationManager
from pipeline import run_pipeline
from database import init_db
from api.route.auth_routes import router as auth_router
from api.route.portfolio_routes import router as portfolio_router
from api.route.alert_routes import router as alert_router
app = FastAPI(title="EventImpact API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化資料庫
init_db()

# 註冊路由
app.include_router(auth_router)
app.include_router(portfolio_router)
app.include_router(alert_router)
# 每個 session_id 對應一個 ConversationManager
sessions: dict[str, ConversationManager] = {}

def get_session(session_id: str) -> ConversationManager:
    if session_id not in sessions:
        sessions[session_id] = ConversationManager()
    return sessions[session_id]


# ── Models ────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message:    str

class ResetRequest(BaseModel):
    session_id: str


# ── Routes ────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "EventImpact API is running"}


@app.post("/chat")
async def chat(req: ChatRequest):
    manager = get_session(req.session_id)
    result  = manager.chat(req.message)

    # 資訊齊全，觸發分析
    if result["ready"]:
        try:
            analysis = run_pipeline(result["context"])
            manager.state = "done"
            return {
                "type":    "analysis",
                "reply":   result["reply"],
                "context": result["context"],
                "data":    analysis,
            }
        except Exception as e:
            return {
                "type":  "error",
                "reply": f"分析過程發生錯誤：{str(e)}",
            }

    # 還在收集資訊或確認中
    return {
        "type":    result["state"],
        "reply":   result["reply"],
        "context": result["context"],
        "data":    None,
    }


@app.post("/reset")
def reset(req: ResetRequest):
    manager = get_session(req.session_id)
    manager.reset()
    return {"status": "ok", "message": "對話已重置"}


@app.get("/health")
def health():
    return {"status": "ok"}