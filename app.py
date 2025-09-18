# app.py
import os
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 從環境變數讀取機密（建議做法）
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# 也可暫時直接寫死測試（不建議；請改成你的值）
# CHANNEL_SECRET = "你的 Channel secret"
# CHANNEL_ACCESS_TOKEN = "你的 Channel access token"

if CHANNEL_SECRET is None or CHANNEL_ACCESS_TOKEN is None:
    raise RuntimeError("請設定環境變數 LINE_CHANNEL_SECRET 與 LINE_CHANNEL_ACCESS_TOKEN")

app = Flask(__name__)

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.get("/")
def health():
    return "OK", 200

@app.post("/webhook")
def webhook():
    # 取得 LINE 簽章
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK", 200

# 收到文本就原樣回覆（Echo），先確認 webhook 正常
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event: MessageEvent):
    msg = event.message.text.strip()
    reply = f"你說：{msg}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

# （選用）提供一個簡單 push API：POST /push  { "to":"<user_or_group_id>", "text":"內容" }
# 之後你的 Python 腳本可呼叫這個端點，把訊息轉送到 LINE
@app.post("/push")
def push():
    data = request.get_json(force=True, silent=True) or {}
    to = data.get("to")
    text = data.get("text")
    if not to or not text:
        return {"error": "need 'to' and 'text'"}, 400
    line_bot_api.push_message(to, TextSendMessage(text=text))
    return {"status": "ok"}, 200

if __name__ == "__main__":
    # 本地或 Render/Heroku 皆可用
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
