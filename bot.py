import os
import csv
import httpx
import asyncio
import threading
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===========================
# 1. CONFIG
# ===========================
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"
MAX_ROWS = 10

# ===========================
# 2. XỬ LÝ DỮ LIỆU
# ===========================

async def fetch_csv_data(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=15.0)
            res.raise_for_status()
            return list(csv.DictReader(StringIO(res.text)))
    except:
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot đã sẵn sàng! Nhập mã (VD: SSI, FPT) để xem lệnh mua/bán.")

async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.upper().strip()
    waiting_msg = await update.message.reply_text(f"🔍 Đang lọc đúng mã {user_input}...")

    buy_data = await fetch_csv_data(BUY_URL)
    sell_data = await fetch_csv_data(SELL_URL)

    def get_history(data, symbol):
        history = []
        for r in data:
            # Lấy mã gốc từ Sheets (Ví dụ: "SSI", "SSI_NN")
            raw_ticker = str(r.get("Ticker", "")).upper().strip()
            
            # SO KHỚP TUYỆT ĐỐI: Chỉ lấy nếu bằng đúng mã người dùng gõ
            # Nếu trong sheet là "SSI_NN" và user gõ "SSI" -> False (Bỏ qua)
            if raw_ticker == symbol:
                time_val = r.get("Date/Time", "N/A")
                price_val = r.get("Giá", "0")
                history.append(f"🔹 {raw_ticker} | {time_val} | Giá: {price_val}")
        
        return history[-MAX_ROWS:]

    buy_list = get_history(buy_data, user_input)
    sell_list = get_history(sell_data, user_input)

    if not buy_list and not sell_list:
        await waiting_msg.edit_text(f"❌ Không thấy dữ liệu khớp chính xác với mã: {user_input}")
        return

    msg = f"📌 **KẾT QUẢ: {user_input}**\n\n"
    if buy_list:
        msg += "🟩 **MUA:**\n" + "\n".join(buy_list)
    if sell_list:
        msg += "\n\n🟥 **BÁN:**\n" + "\n".join(sell_list)
    
    await waiting_msg.edit_text(msg, parse_mode="Markdown")

# ===========================
# 3. RUN SERVER
# ===========================
server = Flask(__name__)
@server.route("/")
def home(): return "OK"

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN: return
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))

    threading.Thread(target=lambda: server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
