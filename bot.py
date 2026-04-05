import os, csv, httpx, asyncio, threading, codecs, logging
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH LOG ---
logging.basicConfig(level=logging.INFO)

# --- LINK DỮ LIỆU CỦA ALEX ---
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

async def fetch_csv(url):
    """Tải và đọc file CSV từ Google Sheets"""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=30.0, follow_redirects=True)
            if res.status_code != 200: return []
            
            # Giải mã utf-8-sig để loại bỏ ký tự lạ đầu file
            text = res.content.decode('utf-8-sig')
            f = StringIO(text)
            
            # Dữ liệu thực tế của Alex dùng dấu phẩy (,)
            return list(csv.reader(f, delimiter=','))
    except Exception as e:
        logging.error(f"Lỗi tải dữ liệu: {e}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    # Chuẩn hóa: Viết hoa, xóa cách, đổi '-' thành '_' để khớp SSI_NN
    raw_input = str(update.message.text).strip().upper()
    user_input = raw_input.replace('-', '_')
    
    wait = await update.message.reply_text(f"🔍 Đang tìm dữ liệu cho mã: {user_input}...")

    # Tải dữ liệu từ 2 link
    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    def process_data(rows, symbol):
        found = []
        if not rows: return []
        for r in rows:
            # Kiểm tra dòng có dữ liệu (Ticker ở cột 0, Ngày ở cột 1, Giá ở cột 4)
            if len(r) >= 5:
                db_ticker = str(r[0]).strip().upper()
                
                # Tìm kiếm thông minh: gõ SSI vẫn ra SSI_NN
                if symbol in db_ticker:
                    date_val = r[1]
                    price_val = r[4]
                    found.append(f"🔹 {db_ticker} | {date_val} | Giá: {price_val}")
        return found[-10:] # Lấy 10 lệnh gần nhất

    buy_list = process_data(buy_raw, user_input)
    sell_list = process_data(sell_raw, user_input)

    if not buy_list and not sell_list:
        # Nếu không thấy, hiện 5 mã đầu tiên trong file để Alex đối chiếu
        samples = [str(r[0]).strip() for r in buy_raw[1:6] if len(r) > 0 and r[0] != 'Ticker']
        await wait.edit_text(
            f"❌ Không thấy mã: {user_input}\n\n"
            f"📍 Mã đang có trong file Drive: {', '.join(samples)}\n"
            f"👉 Lưu ý: Bạn cần gõ đúng tên mã ở cột A."
        )
        return

    # Trình bày kết quả
    msg = f"📌 **KẾT QUẢ: {user_input}**\n\n"
    if buy_list:
        msg += "🟩 **LỆNH MUA:**\n" + "\n".join(buy_list)
    if sell_list:
        msg += "\n\n🟥 **LỆNH BÁN:**\n" + "\n".join(sell_list)
    
    await wait.edit_text(msg, parse_mode="Markdown")

# --- SERVER DUY TRÌ TRÊN RENDER ---
server = Flask(__name__)
@server.route("/")
def home(): return "Bot is Online"

def run_flask():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

def main():
    token = os.getenv("BOT_TOKEN")
    if not token: return
    
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Chạy Flask Server
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Chạy Bot Polling
    logging.info("🚀 Bot đang khởi động...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
