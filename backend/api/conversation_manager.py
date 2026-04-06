# backend/api/conversation_manager.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from api.intent_parser import parse_intent, generate_followup_question

class ConversationManager:
    def __init__(self):
        self.reset()

    def reset(self):
        self.history   = []   # 對話歷史
        self.context   = {    # 累積收集到的資訊
            "event":   None,
            "ticker":  None,
            "company": None,
            "days":    5,
            "intent":  "prediction",
        }
        self.state = "collecting"  # collecting → confirming → analyzing → done

    def _merge_context(self, parsed: dict):
        """把新解析到的欄位合併進 context，不覆蓋已有的值"""
        for key in ["event", "ticker", "company", "days", "intent"]:
            if parsed.get(key) is not None:
                self.context[key] = parsed[key]

    def _context_missing(self) -> list:
        missing = []
        if not self.context["event"]:
            missing.append("event")
        if not self.context["ticker"]:
            missing.append("ticker")
        return missing

    def _confirmation_message(self) -> str:
        c = self.context
        company_str = f"（{c['company']}）" if c["company"] else ""
        return (
            f"好的，我來幫你分析：\n"
            f"📌 事件：{c['event']}\n"
            f"📈 股票：{c['ticker']}{company_str}\n"
            f"📅 預測天數：{c['days']} 天\n\n"
            f"確認開始分析嗎？（是 / 不對，我要修改）"
        )

    def chat(self, user_message: str) -> dict:
        """
        主對話函式
        回傳：{
            "reply": 系統回應文字,
            "state": 目前狀態,
            "context": 目前收集到的資訊,
            "ready": 是否可以開始分析
        }
        """
        self.history.append({"role": "user", "content": user_message})

        # 使用者確認階段
        if self.state == "confirming":
            if any(w in user_message for w in ["是", "好", "對", "確認", "開始", "yes", "ok"]):
                self.state = "analyzing"
                reply = "⏳ 開始分析中，請稍候..."
                self.history.append({"role": "assistant", "content": reply})
                return {
                    "reply": reply,
                    "state": self.state,
                    "context": self.context,
                    "ready": True
                }
            else:
                # 使用者說不對，重新收集
                self.state = "collecting"
                reply = "好的，請重新描述你想分析的內容。"
                self.history.append({"role": "assistant", "content": reply})
                return {
                    "reply": reply,
                    "state": self.state,
                    "context": self.context,
                    "ready": False
                }

        # 收集資訊階段
        parsed = parse_intent(user_message)
        self._merge_context(parsed)
        missing = self._context_missing()

        if missing:
            # 還有缺少的資訊，繼續追問
            reply = generate_followup_question(missing)
            self.history.append({"role": "assistant", "content": reply})
            return {
                "reply": reply,
                "state": self.state,
                "context": self.context,
                "ready": False
            }
        else:
            # 資訊齊全，進入確認階段
            self.state = "confirming"
            reply = self._confirmation_message()
            self.history.append({"role": "assistant", "content": reply})
            return {
                "reply": reply,
                "state": self.state,
                "context": self.context,
                "ready": False
            }


# ── 測試用：模擬對話 ──────────────────────────────────────────
if __name__ == "__main__":
    manager = ConversationManager()

    scenarios = [
        # 情境一：資訊完整，一次到位
        ["美中關稅對台積電未來5天會有什麼影響？", "是"],
        # 情境二：缺 ticker，需要追問
        ["我想看升息的影響", "台積電", "是"],
        # 情境三：缺 event，需要追問
        ["鴻海最近怎麼樣", "美中關稅", "是"],
    ]

    for i, messages in enumerate(scenarios):
        print(f"\n{'='*50}")
        print(f"情境 {i+1}")
        print('='*50)
        manager.reset()

        for msg in messages:
            print(f"\n使用者：{msg}")
            result = manager.chat(msg)
            print(f"系統：{result['reply']}")
            print(f"狀態：{result['state']} | ready={result['ready']}")
            if result["ready"]:
                print(f"→ 觸發分析：{json.dumps(result['context'], ensure_ascii=False)}")
                break