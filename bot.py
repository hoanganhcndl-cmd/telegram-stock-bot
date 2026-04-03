import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# Flask app
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

# Telegram bot (không run_webhook!)
tg_app = ApplicationBuilder().token(TOKEN).build()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)

    # Đẩy update vào PTB để xử lý async
    asyncio.get_event_loop().create_task(tg_app.process_update(update))

    return "ok", 200

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot webhook Render hoạt động OK!")

tg_app.add_handler(CommandHandler("start", start))

# Khởi động application (không run_webhook)
async def run_bot():
    await tg_app.initialize()
    await tg_app.start()
    print("PTB bot started!")

# Bắt đầu ptb worker trong thread asyncio
asyncio.get_event_loop().create_task(run_bot())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
