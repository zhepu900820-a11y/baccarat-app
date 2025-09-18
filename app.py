# app.py
import os
import hmac
import hashlib
from flask import Flask, request, abort, jsonify

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# ==== 讀環境變數 ====
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
PUSH_KEY = os.getenv("PUSH_KEY", "")  # 你自訂的推播祕鑰
TARGET_USER_ID = os.getenv("TARGET_USER_ID", "")  # 你要接收推播的人 (先放你自己)

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise RuntimeError("請在環境變數設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

app = Flask(__name__)

# ---- Health Check ----
@app.route("/", methods=["GET"])
def root():
    return "OK", 200

# ---- LINE Webhook ----
@app.route("/callback", methods=['POST'])
def callback():
    # 取出 LINE 簽章
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    # 為了除錯看 Log
    print("Request body:", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature.")
        abort(400)

    return 'OK'


# 收到使用者文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event: MessageEvent):
    user_id = event.source.user_id
    user_text = event.message.text.strip()

    # **重要**：把 userId 印到 Log，去 Render Logs 就能看到
    print(f"[LINE] user_id={user_id}, msg={user_text}")

    # 簡單回覆 (回聲)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"你說：{user_text}")
    )


# ---- 外部推播 API ----
# 你用 HTTP 呼叫這個端點，就能讓 Bot 主動推播給 TARGET_USER_ID
# 需要帶上正確的 PUSH_KEY 才會通過
@app.route("/push", methods=["POST"])
def push():
    # 支援 JSON 或 form
    data = request.get_json(silent=True) or request.form
    key = (data.get("key") or "").strip()
    text = (data.get("text") or "").strip()

    if not key or not text:
        return jsonify({"ok": False, "error": "缺少 key 或 text"}), 400

    # 簡單比對祕鑰（如需更高安全性可改用 HMAC）
    if key != PUSH_KEY:
        return jsonify({"ok": False, "error": "key 錯誤"}), 403

    if not TARGET_USER_ID:
        return jsonify({"ok": False, "error": "尚未設定 TARGET_USER_ID"}), 400

    try:
        line_bot_api.push_message(TARGET_USER_ID, TextSendMessage(text=text))
        return jsonify({"ok": True}), 200
    except Exception as e:
        print("Push error:", e)
        return jsonify({"ok": False, "error": str(e)}), 500


# ---- 可選：HMAC 驗證的範例（若你要用更嚴謹的簽章驗證）----
def verify_hmac(message: str, key: str, signature_hex: str) -> bool:
    """若你未來改為以 HMAC 驗簽，可用這個工具函數。"""
    dig = hmac.new(key.encode("utf-8"), msg=message.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(dig, signature_hex.lower())


if __name__ == "__main__":
    # 本地除錯時用；在 Render 會由 gunicorn 啟動
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
