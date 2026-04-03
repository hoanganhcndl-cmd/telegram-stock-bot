import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# Flask app
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

# Telegram bot
tg_app = ApplicationBuilder().token(TOKEN).build()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    tg_app.update_queue.put(update)
    return "ok", 200

# Command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot đang chạy webhook trên Render OK!")

tg_app.add_handler(CommandHandler("start", start))

# Start notifier only
if __name__ == "__main__":
    tg_app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 10000)),
        webhook_url="https://telegram-stock-bot-q9bi.onrender.com/webhook"
    )
