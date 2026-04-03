import os
import asyncio
import threading
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
    asyncio.run_coroutine_threadsafe(tg_app.process_update(update), tg_app.loop)
    return "ok", 200

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot webhook Render đang chạy!")

tg_app.add_handler(CommandHandler("start", start))

# Chạy PTB bot trong thread riêng
def start_bot():
    asyncio.run(tg_app.initialize())
    asyncio.run(tg_app.start())

threading.Thread(target=start_bot).start()
