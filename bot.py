import os
import requests
import csv
from io import StringIO
from flask import Flask, request

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

MAX_ROWS = 20

app = Flask(__name__)
telegram_app = None  # sẽ gán sau


def get_sheet_data(url):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        f = StringIO(res.text)
        return list(csv.DictReader(f))
    except Exception as e:
        print("Error loading sheet:", e)
        return []


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Nhập mã cổ phiếu để xem lịch sử giao dịch.")


async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.upper().strip()

    buy_data = get_sheet_data(BUY_URL)
    sell_data = get_sheet_data(SELL_URL)

    buy_list = [row for row in buy_data if row.get("Ticker") == ticker][-MAX_ROWS:]
    sell_list = [row for row in sell_data if row.get("Ticker") == ticker][-MAX_ROWS:]

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


@app.post("/webhook")
async def webhook():
    try:
        data = request.get_json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
        return "OK", 200
    except Exception as e:
        print("WEBHOOK ERROR:", e)
        return "ERROR", 500


def main():
    global telegram_app

    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        raise ValueError("Thiếu BOT_TOKEN")

    telegram_app = Application.builder().token(TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))

    # Set webhook URL
    url = "https://telegram-stock-bot-q9bi.onrender.com/webhook"

    # Chạy Flask + webhook chung 1 port
    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=url
    )


if __name__ == "__main__":
    main()
