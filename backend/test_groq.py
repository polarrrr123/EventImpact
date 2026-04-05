# backend/test_groq.py
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="../.env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[
        {
            "role": "system",
            "content": "你是一個台灣股市分析助理，請用繁體中文回答。"
        },
        {
            "role": "user",
            "content": "美中關稅對台積電會有什麼影響？"
        }
    ]
)

print(response.choices[0].message.content)