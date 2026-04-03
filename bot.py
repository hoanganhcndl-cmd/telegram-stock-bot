import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

app = Flask(__name__)

# Telegram bot
tg_app = ApplicationBuilder().token(TOKEN).build()

@app.route("/")
def home():
    return "Bot is running!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    # Đẩy vào PTB async
    asyncio.run_coroutine_threadsafe(tg_app.process_update(update), tg_app.loop)
    return "ok", 200

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot webhook Render hoạt động OK!")

tg_app.add_handler(CommandHandler("start", start))

# Khởi động bot PTB khi Flask start
@app.before_first_request
def start_bot():
    asyncio.get_event_loop().create_task(tg_app.initialize())
    asyncio.get_event_loop().create_task(tg_app.start())

# Không dùng app.run() trực tiếp trên Render, dùng gunicorn
