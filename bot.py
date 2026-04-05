import os
import csv
import httpx
import asyncio
import threading
import codecs
from io import StringIO, BytesIO
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
# 2. HÀM TẢI DỮ LIỆU SẠCH
# ===========================

async def fetch_csv_data(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=15.0)
            res.raise_for_status()
            
            # Xử lý ký tự lạ (BOM) ở đầu file CSV từ Google
            content = res.content
            if content.startswith(codecs.BOM_UTF8):
                content = content[len(codecs.BOM_UTF8):]
            
            decoded_content = content.decode('utf-8')
            f = StringIO(decoded_content)
            reader = csv.DictReader(f)
            # Làm sạch tiêu đề cột
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
            return list(reader)
    except Exception as e:
        print(f"Lỗi: {e}")
        return []

# ===========================
# 3. HANDLERS
# ===========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Chào Alex! Nhập mã (VD: SSI, FPT) để xem lệnh mua/bán.")

async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Chuẩn hóa mã người dùng nhập: Xóa dấu cách, in hoa
    user_input = str(update.message.text).strip().upper()
    waiting_msg = await update.message.reply_text(f"🔍 Đang tìm khớp 100% mã: {user_input}...")

    buy_data = await fetch_csv_data(BUY_URL)
    sell_data = await fetch_csv_data(SELL_URL)

    def get_history(data, symbol):
        history = []
        for r in data:
            # Làm sạch mã trong Sheets trước khi so sánh
            # Tìm cột có tên 'Ticker', nếu không thấy thì thử tìm cột đầu tiên
            raw_ticker = str(r.get("Ticker") or next(iter(r.values()), "")).strip().upper()
            
            # SO KHỚP TUYỆT ĐỐI
            if raw_ticker == symbol:
                # Lấy dữ liệu theo tên cột trong hình của bạn
                date_val = str(r.get("Date/Time", "N/A")).strip()
                price_val = str(r.get("Giá", "0")).strip()
                history.append(f"🔹 {raw_ticker} | {date_val} | Giá: {price_val}")
        
        return history[-MAX_ROWS:]

    buy_list = get_history(buy_data, user_input)
    sell_list = get_history(sell_data, user_input)

    if not buy_list and not sell_list:
        # Nếu vẫn không thấy, gửi thêm thông báo gợi ý
        await waiting_msg.edit_text(f"❌ Không thấy mã: {user_input}\n\nHãy kiểm tra lại cột 'Ticker' trong Sheets xem có đúng chữ '{user_input}' không nhé!")
        return

    msg = f"📌 **KẾT QUẢ: {user_input}**\n\n"
    if buy_list:
        msg += "🟩 **MUA:**\n" + "\n".join(buy_list)
    if sell_list:
        msg += "\n\n🟥 **BÁN:**\n" + "\n".join(sell_list)
    
    await waiting_msg.edit_text(msg, parse_mode="Markdown")

# ===========================
# 4. SERVER & CHẠY
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
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
