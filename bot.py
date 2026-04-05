import os
import csv
import requests
from io import StringIO
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===========================
# CONFIG - Google Sheet CSV
# ===========================
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"
MAX_ROWS = 20


# ===========================
# READ CSV
# ===========================
def get_sheet_data(url):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        f = StringIO(res.text)
        return list(csv.DictReader(f))
    except Exception as e:
        print("Error:", e)
        return []


# ===========================
# TELEGRAM HANDLERS
# ===========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Nhập mã chứng khoán để xem giao dịch (FPT, SSI, VIC...)")


async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.upper().strip()

    buy_data = get_sheet_data(BUY_URL)
    sell_data = get_sheet_data(SELL_URL)

    buy_list = [r for r in buy_data if r.get("Ticker") == ticker][-MAX_ROWS:]
    sell_list = [r for r in sell_data if r.get("Ticker") == ticker][-MAX_ROWS:]

    buy_list.reverse()
    sell_list.reverse()

    if not buy_list and not sell_list:
        await update.message.reply_text(f"Không có dữ liệu cho {ticker}")
        return

    msg = f"📌 Lịch sử giao dịch {ticker}\n\n"

    if buy_list:
        msg += "🟩 BUY:\n"
        for r in buy_list:
            msg += f"- {r['Time']} | Giá {r['Price']} | KL {r['Volume']}\n"

    if sell_list:
        msg += "\n🟥 SELL:\n"
        for r in sell_list:
            msg += f"- {r['Time']} | Giá {r['Price']} | KL {r['Volume']}\n"

    await update.message.reply_text(msg)


# ===========================
# RUN TELEGRAM BOT (THREAD)
# ===========================
def run_bot():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise Exception("Thiếu BOT_TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))

    print("🚀 Telegram Bot is running...")
    app.run_polling()


# ===========================
# FLASK WEB SERVER (Render cần PORT)
# ===========================
server = Flask(__name__)

@server.route("/")
def home():
    return "Bot is running on Render!"


# ===========================
# MAIN
# ===========================
if __name__ == "__main__":
    # Chạy bot song song
    Thread(target=run_bot).start()

    # Chạy Flask server
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)
