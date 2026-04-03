from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask, request
import os

TOKEN = os.getenv("BOT_TOKEN")

# Flask app
app = Flask(__name__)

# Telegram bot app
tg_app = ApplicationBuilder().token(TOKEN).build()

# Webhook route
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    tg_app.update_queue.put(update)
    return "ok", 200

# Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot hoạt động OK!")

tg_app.add_handler(CommandHandler("start", start))

# Start webhook
if __name__ == "__main__":
    tg_app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 10000)),
        webhook_url="https://telegram-stock-bot-q9bi.onrender.com/webhook"
    )
