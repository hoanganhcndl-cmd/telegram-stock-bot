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
# 1. CẤU HÌNH (CONFIG)
# ===========================
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"
MAX_ROWS = 15

# ===========================
# 2. CÁC HÀM XỬ LÝ (PHẢI ĐỂ Ở TRÊN)
# ===========================

# Hàm tải dữ liệu từ Google Sheets (Async để không làm treo bot)
async def fetch_csv_data(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=15.0)
            res.raise_for_status()
            f = StringIO(res.text)
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"❌ Lỗi tải CSV: {e}")
        return []

# Hàm xử lời chào /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Chào Alex! Bot chứng khoán đã sẵn sàng.\nNhập mã chứng khoán (VD: FPT, SSI) để xem lệnh mua/bán mới nhất.")

# Hàm xử lý khi người dùng nhập mã chứng khoán
async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.upper().strip()
    
    # Gửi thông báo đang xử lý
    waiting_msg = await update.message.reply_text(f"🔍 Đang kiểm tra mã {ticker}, đợi xíu nhé...")

    # Tải dữ liệu mới nhất
    buy_data = await fetch_csv_data(BUY_URL)
    sell_data = await fetch_csv_data(SELL_URL)

    # Lọc dữ liệu theo mã chứng khoán
    buy_list = [r for r in buy_data if r.get("Ticker") == ticker][-MAX_ROWS:]
    sell_list = [r for r in sell_data if r.get("Ticker") == ticker][-MAX_ROWS:]
    
    buy_list.reverse()
    sell_list.reverse()

    if not buy_list and not sell_list:
        await waiting_msg.edit_text(f"❌ Không tìm thấy dữ liệu cho mã: {ticker}")
        return

    msg = f"📌 **LỊCH SỬ GIAO DỊCH {ticker}**\n\n"
    if buy_list:
        msg += "🟩 **BUY (Mua):**\n" + "\n".join(f"- {r['Time']} | Giá {r['Price']} | KL {r['Volume']}" for r in buy_list)
    if sell_list:
        msg += "\n\n🟥 **SELL (Bán):**\n" + "\n".join(f"- {r['Time']} | Giá {r['Price']} | KL {r['Volume']}" for r in sell_list)
    
    await waiting_msg.edit_text(msg, parse_mode="Markdown")

# ===========================
# 3. WEB SERVER (Để Render không tắt bot)
# ===========================
server = Flask(__name__)

@server.route("/")
def home():
    return "Bot is alive and running!"

def run_flask():
    # Render yêu cầu chạy trên cổng PORT do họ cung cấp
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)

# ===========================
# 4. KHỞI CHẠY BOT (MAIN)
# ===========================
def main():
    # Lấy Token từ Environment Variable (Đã cài trên Render)
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        print("❌ LỖI: BOT_TOKEN chưa được thiết lập!")
        return

    # Khởi tạo Application
    app = ApplicationBuilder().token(TOKEN).build()

    # Đăng ký các lệnh (Hàm start và search_ticker đã được định nghĩa ở trên nên sẽ không lỗi)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))

    # Chạy Flask Web Server ở luồng phụ (Thread)
    threading.Thread(target=run_flask, daemon=True).start()

    print("🚀 Bot đang bắt đầu lắng nghe tin nhắn...")
    
    # Chạy Bot ở luồng chính (Main)
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
