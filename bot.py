import os
import csv
import requests
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import threading
import asyncio

# ===========================
# CONFIG
# ===========================
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"
MAX_ROWS = 20

# ===========================
# LOAD CSV ON START
# ===========================
def fetch_csv(url):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return list(csv.DictReader(StringIO(res.text)))
    except:
        return []

buy_data = fetch_csv(BUY_URL)
sell_data = fetch_csv(SELL_URL)
print(f"🟢 Loaded {len(buy_data)} buy rows and {len(sell_data)} sell rows")

# ===========================
# TELEGRAM HANDLERS
# ===========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Nhập mã chứng khoán để xem giao dịch (FPT, SSI, VIC...)")

async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.upper().strip()
    buy_list = [r for r in buy_data if r.get("Ticker") == ticker][-MAX_ROWS:]
    sell_list = [r for r in sell_data if r.get("Ticker") == ticker][-MAX_ROWS:]
    buy_list.reverse()
    sell_list.reverse()

    if not buy_list and not sell_list:
        await update.message.reply_text(f"Không có dữ liệu cho {ticker}")
        return

    msg = f"📌 Lịch sử giao dịch {ticker}\n\n"
    if buy_list:
        msg += "🟩 BUY:\n" + "\n".join(f"- {r['Time']} | Giá {r['Price']} | KL {r['Volume']}" for r in buy_list)
    if sell_list:
        msg += "\n🟥 SELL:\n" + "\n".join(f"- {r['Time']} | Giá {r['Price']} | KL {r['Volume']}" for r in sell_list)
    await update.message.reply_text(msg)

# ===========================
# FLASK WEB
# ===========================
server = Flask(__name__)

@server.route("/")
def home():
    return "Bot is running on Render!"

# ===========================
# RUN TELEGRAM BOT ASYNC
# ===========================
async def run_telegram_bot():
    TOKEN = os.getenv("BOT_TOKEN", "8746767158:AAGnKeB3S4zHZO0oZdEex8SLLX7JstDlSTs")
    print("🚀 Starting Telegram Bot...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()  # giữ bot chạy

# ===========================
# ENTRY POINT
# ===========================
if __name__ == "__main__":
    # Flask server trong thread riêng
    threading.Thread(
        target=lambda: server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))),
        daemon=True
    ).start()

    # chạy bot trong main async thread
    asyncio.run(run_telegram_bot())
