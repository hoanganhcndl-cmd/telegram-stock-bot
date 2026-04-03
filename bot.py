import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# Flask app (Render cần để giữ web alive)
app = Flask(__name__)

# Telegram app
tg_app = ApplicationBuilder().token(TOKEN).build()

# ===== ROUTE WEBHOOK =====
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    update = Update.de_json(data, tg_app.bot)
    tg_app.update_queue.put(update)
    return "ok"

# ===== COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot hoạt động OK!")

tg_app.add_handler(CommandHandler("start", start))

# ===== CHẠY WEBHOOK =====
if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 10000))

    # KHÔNG CHẠY Flask bằng app.run() ⛔
    # Thay bằng gunicorn xử lý Flask

    tg_app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url="https://telegram-stock-bot-q9bi.onrender.com/webhook",
    )
