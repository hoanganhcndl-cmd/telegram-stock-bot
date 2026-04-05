import os
import csv
import httpx  # Dùng httpx thay cho requests để chạy async
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
MAX_ROWS = 15

# ===========================
# FETCH DATA FUNCTION (ASYNC)
# ===========================
async def fetch_csv_data(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10.0)
            res.raise_for_status()
            f = StringIO(res.text)
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"❌ Lỗi tải dữ liệu: {e}")
        return []

# ===========================
# TELEGRAM HANDLERS
# ===========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chào Alex! Hãy nhập mã chứng khoán (VD: FPT, SSI) để xem dữ liệu mới nhất.")

async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.upper().strip()
    await update.message.reply_chat_action("typing")

    # Tải dữ liệu mới mỗi khi người dùng hỏi để đảm bảo tính cập nhật
    buy_data = await fetch_csv_data(BUY_URL)
    sell_data = await fetch_csv_data(SELL_URL)

    buy_list = [r for r in buy_data if r.get("Ticker") == ticker][-MAX_ROWS:]
    sell_list = [r for r in sell_data if r.get("Ticker") == ticker][-MAX_ROWS:]
    
    buy_list.reverse()
    sell_list.reverse()

    if not buy_list and not sell_list:
        await update.message.reply_text(f"Không tìm thấy dữ liệu cho mã: {ticker}")
        return

    msg = f"📌 **Lịch sử giao dịch {ticker}**\n\n"
    if buy_list:
        msg += "🟩 **BUY:**\n" + "\n".join(f"- {r['Time']} | Giá {r['Price']} | KL {r['Volume']}" for r in buy_list)
    if sell_list:
        msg += "\n\n🟥 **SELL:**\n" + "\n".join(f"- {r['Time']} | Giá {r['Price']} | KL {r['Volume']}" for r in sell_list)
    
    await update.message.reply_text(msg, parse_mode="Markdown")

# ===========================
# FLASK WEB SERVER (To keep Render alive)
# ===========================
server = Flask(__name__)

@server.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)

# ===========================
# MAIN RUNNER
# ===========================
async def main():
    # Lấy token từ Environment Variable (Khuyến nghị)
    TOKEN = os.getenv("BOT_TOKEN", "8746767158:AAGnKeB3S4zHZO0oZdEex8SLLX7JstDlSTs")
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))

    # Chạy Flask trong thread riêng
    threading.Thread(target=run_flask, daemon=True).start()

    print("🚀 Bot đang khởi động...")
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
