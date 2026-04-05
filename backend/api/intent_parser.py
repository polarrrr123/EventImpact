# backend/api/intent_parser.py
from groq import Groq
from dotenv import load_dotenv
import os
import json
import re

load_dotenv(dotenv_path="../../.env")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
你是一個台灣股市分析助理的語意解析器。
使用者會用自然語言描述他想分析的事件與股票。

只回傳 JSON，不要有任何其他文字或 markdown：

{
  "event": "事件關鍵字（例如：美中關稅、颱風、升息）。沒有則填 null",
  "ticker": "台股代號加.TW（例如：2330.TW）。沒有則填 null",
  "company": "公司中文名稱。沒有則填 null",
  "days": 預測天數（數字，預設為5）,
  "intent": "prediction 或 analysis"
}

常見股票對照：
- 台積電 = 2330.TW
- 鴻海 = 2317.TW
- 聯發科 = 2454.TW
- 台灣50 / 大盤 / 整體市場 = 0050.TW
"""

def parse_intent(user_message: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message}
        ],
        temperature=0.1
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "event": None,
            "ticker": None,
            "company": None,
            "days": 5,
            "intent": "prediction",
        }

    # ✅ 不信任 LLM 的 missing，改由 Python 自己算
    missing = []
    if not result.get("event"):
        missing.append("event")
    if not result.get("ticker"):
        missing.append("ticker")
    result["missing"] = missing

    return result


def generate_followup_question(missing: list) -> str:
    """
    根據缺少的欄位，產生追問句
    """
    questions = {
        "ticker": "你想分析哪支股票或哪個產業？（例如：台積電、鴻海、科技類股）",
        "event":  "你想分析什麼事件對股票的影響？（例如：美中關稅、升息、颱風）",
    }
    # 回傳第一個缺少的問題
    for field in missing:
        if field in questions:
            return questions[field]
    return None


if __name__ == "__main__":
    test_cases = [
        "美中關稅對台積電未來5天會有什麼影響？",
        "颱風來了對大盤有影響嗎",
        "我想看升息的影響",          # 缺 ticker
        "鴻海最近怎麼樣",            # 缺 event
    ]

    for msg in test_cases:
        print(f"\n輸入：{msg}")
        result = parse_intent(msg)
        print(f"解析：{json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result.get("missing"):
            q = generate_followup_question(result["missing"])
            print(f"追問：{q}")