import os
import csv
from io import StringIO
import threading
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Bot token
TOKEN = os.getenv("BOT_TOKEN")

# CSV link (ví dụ)
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

MAX_ROWS = 20

app = Flask(__name__)

# Telegram bot
tg_app = ApplicationBuilder().token(TOKEN).build()

# ---- Flask routes ----
@app.route("/")
def home():
    return "Bot is running!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    # Push update vào PTB async
    asyncio.run_coroutine_threadsafe(tg_app.process_update(update), tg_app.loop)
    return "ok", 200

# ---- Bot commands ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot webhook Render đang chạy!")

tg_app.add_handler(CommandHandler("start", start))

# ---- Ticker search command ----
async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.upper().strip()

    # Lấy dữ liệu CSV
    import requests
    def get_csv_data(url):
        try:
            res = requests.get(url, timeout=10)
            f = StringIO(res.text)
            return list(csv.DictReader(f))
        except:
            return []

    buy_data = get_csv_data(BUY_URL)
    sell_data = get_csv_data(SELL_URL)

    buy_list = [r for r in buy_data if r.get("Ticker") == ticker][-MAX_ROWS:]
    sell_list = [r for r in sell_data if r.get("Ticker") == ticker][-MAX_ROWS:]

    buy_list.reverse()
    sell_list.reverse()

    if not buy_list and not sell_list:
        await update.message.reply_text(f"Không có giao dịch cho {ticker}.")
        return

    result = f"📌 LỊCH SỬ GIAO DỊCH: {ticker}\n\n"
    if buy_list:
        result += "🟢 MUA:\n"
        for row in buy_list:
            result += f"- {row.get('Date/Time')} | SL {row.get('Mua')} | Giá {row.get('Giá')}\n"
        result += "\n"
    if sell_list:
        result += "🔴 BÁN:\n"
        for row in sell_list:
            result += f"- {row.get('Date/Time')} | SL {row.get('Bán')} | Giá {row.get('Giá')}\n"

    await update.message.reply_text(result)

tg_app.add_handler(CommandHandler("search", search_ticker))
tg_app.add_handler(
    # Nhận bất kỳ tin nhắn văn bản nào và coi là ticker
    CommandHandler(None, search_ticker)
)

# ---- Chạy bot trong thread riêng ----
def start_bot():
    asyncio.run(tg_app.initialize())
    asyncio.run(tg_app.start())
    print("PTB bot started!")

threading.Thread(target=start_bot, daemon=True).start()
