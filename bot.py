import os
import csv
import requests
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import threading
import time

# ===========================
# CONFIG
# ===========================
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"
MAX_ROWS = 20
CACHE_TIME = 300  # 5 phút

# ===========================
# GLOBAL CACHE
# ===========================
buy_data_cache = []
sell_data_cache = []
last_update = 0

# ===========================
# READ CSV
# ===========================
def fetch_csv(url):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        f = StringIO(res.text)
        return list(csv.DictReader(f))
    except:
        return []

def update_cache():
    global buy_data_cache, sell_data_cache, last_update
    while True:
        buy_data_cache = fetch_csv(BUY_URL)
        sell_data_cache = fetch_csv(SELL_URL)
        last_update = time.time()
        print("🟢 CSV cache updated")
        time.sleep(CACHE_TIME)

# ===========================
# TELEGRAM HANDLERS
# ===========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Nhập mã chứng khoán để xem giao dịch (FPT, SSI, VIC...)")

async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.upper().strip()
    buy_list = [r for r in buy_data_cache if r.get("Ticker") == ticker][-MAX_ROWS:]
    sell_list = [r for r in sell_data_cache if r.get("Ticker") == ticker][-MAX_ROWS:]
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
# RUN BOT
# ===========================
def run_bot():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("Thiếu BOT_TOKEN")
        return
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))
    print("🚀 Telegram Bot is running...")
    app.run_polling()  # blocking

# ===========================
# FLASK WEB
# ===========================
server = Flask(__name__)

@server.route("/")
def home():
    return "Bot is running on Render!"

# ===========================
# MAIN
# ===========================
if __name__ == "__main__":
    threading.Thread(target=update_cache, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)
