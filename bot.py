import os
import csv
import requests
from io import StringIO
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ====== GOOGLE SHEET ======
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

MAX_ROWS = 20

# ====== TELEGRAM ======
TOKEN = "8746767158:AAFEI_XKB-vqjtcTnR0jWCqo1fQPgxvdA-c"
bot = Bot(TOKEN)

# ====== FLASK SERVER ======
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

# ====== LOAD GOOGLE SHEET ======
def get_sheet_data(url):
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        f = StringIO(r.text)
        return list(csv.DictReader(f))
    except:
        return []

# ====== BOT COMMANDS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Nhập mã cổ phiếu để xem lịch sử giao dịch.")

async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.upper().strip()

    buy_data = get_sheet_data(BUY_URL)
    sell_data = get_sheet_data(SELL_URL)

    buy_list = [r for r in buy_data if r.get("Ticker") == ticker][-MAX_ROWS:]
    sell_list = [r for r in sell_data if r.get("Ticker") == ticker][-MAX_ROWS:]

    buy_list.reverse()
    sell_list.reverse()

    if not buy_list and not sell_list:
        await update.message.reply_text(f"Không có giao dịch cho {ticker}.")
        return

    msg = f"📌 LỊCH SỬ GIAO DỊCH: {ticker}\n\n"

    if buy_list:
        msg += "🟢 MUA:\n"
        for r in buy_list:
            msg += f"- {r.get('Date/Time')} | SL {r.get('Mua')} | Giá {r.get('Giá')}\n"
        msg += "\n"

    if sell_list:
        msg += "🔴 BÁN:\n"
        for r in sell_list:
            msg += f"- {r.get('Date/Time')} | SL {r.get('Bán')} | Giá {r.get('Giá')}\n"

    await update.message.reply_text(msg)

# ====== WEBHOOK RECEIVER ======
@app.post("/webhook")
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    app_telegram.bot.process_update(update)
    return "OK", 200


# ====== START BOT + WEBHOOK ======
def main():
    global app_telegram

    app_telegram = ApplicationBuilder().token(TOKEN).build()

    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))

    # URL webhook của Render
    WEBHOOK_URL = "https://telegram-stock-bot-q9bi.onrender.com/webhook"

    # Set webhook
    bot.delete_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

    # Flask chạy trên Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
