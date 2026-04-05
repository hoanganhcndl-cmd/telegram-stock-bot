import os, csv, httpx, asyncio, threading, codecs, logging
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH ---
logging.basicConfig(level=logging.INFO)

# Link CSV từ Google Sheets của Alex (Đã kiểm tra chuẩn CSV)
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

async def fetch_csv(url):
    """Tải dữ liệu và xử lý dấu phân cách chấm phẩy (;) của Alex"""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=25.0, follow_redirects=True)
            if res.status_code != 200: return []
            
            # Xử lý ký tự lạ đầu file (BOM)
            text = res.content.decode('utf-8-sig')
            f = StringIO(text)
            
            # ÉP BUỘC dùng dấu chấm phẩy (;) vì file của Alex dùng dấu này để phân cột
            return list(csv.reader(f, delimiter=';'))
    except Exception as e:
        logging.error(f"Lỗi tải file: {e}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    # Chuẩn hóa mã người dùng nhập (Xóa cách, Viết hoa)
    user_input = str(update.message.text).strip().upper()
    wait = await update.message.reply_text(f"🔍 Đang rà soát dữ liệu mã: {user_input}...")

    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    def process_rows(rows, symbol):
        found = []
        if not rows: return []
        for r in rows:
            if len(r) > 0:
                # Xóa khoảng trắng ẩn trong mã chứng khoán ở cột đầu tiên
                db_ticker = str(r[0]).strip().upper()
                
                if db_ticker == symbol:
                    # r[1]: Ngày, r[3]: Giá (hoặc cột cuối cùng nếu dòng ngắn)
                    date_val = r[1] if len(r) > 1 else "N/A"
                    price_val = r[3] if len(r) > 3 else (r[-1] if len(r) > 1 else "0")
                    found.append(f"🔹 {db_ticker} | {date_val} | Giá: {price_val}")
        return found[-10:] # Lấy 10 lệnh gần nhất

    buy_list = process_rows(buy_raw, user_input)
    sell_list = process_rows(sell_raw, user_input)

    if not buy_list and not sell_list:
        # Lấy 10 mã đầu tiên Bot thấy thực tế để Alex đối chiếu lỗi
        samples = []
        if buy_raw:
            samples = [f"'{str(r[0]).strip()}'" for r in buy_raw[1:11] if len(r) > 0]
        
        await wait.edit_text(
            f"❌ Không tìm thấy mã: {user_input}\n\n"
            f"📍 Các mã Bot đang đọc được trong Sheets:\n{', '.join(samples)}\n\n"
            f"👉 Lưu ý: Nếu danh sách trên hiện ra 'SSI_NN' thì bạn phải gõ đúng 'SSI_NN' mới ra kết quả."
        )
        return

    msg = f"📌 **KẾT QUẢ: {user_input}**\n\n"
    if buy_list:
        msg += "🟩 **LỆNH MUA:**\n" + "\n".join(buy_list)
    if sell_list:
        msg += "\n\n🟥 **LỆNH BÁN:**\n" + "\n".join(sell_list)
    
    await wait.edit_text(msg, parse_mode="Markdown")

# --- WEB SERVER ĐỂ DUY TRÌ RENDER ---
server = Flask(__name__)
@server.route("/")
def home(): return "OK"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)

# --- KHỞI CHẠY BOT ---
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        logging.error("Thiếu BOT_TOKEN!")
        return
    
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("Chào Alex! Nhập mã chứng khoán (VD: HPG, SSI).")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Chạy Web Server luồng riêng
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Chạy Polling - drop_pending_updates=True để xóa lỗi Conflict
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
