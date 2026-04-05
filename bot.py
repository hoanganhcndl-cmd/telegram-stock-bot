import os, csv, httpx, asyncio, threading, codecs, logging
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- LINK DỮ LIỆU CỦA ALEX ---
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

# --- HÀM TẢI DỮ LIỆU ---
async def fetch_csv(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=25.0, follow_redirects=True)
            if res.status_code != 200: return []
            
            # Xử lý ký tự lạ đầu file (BOM) và dùng dấu chấm phẩy (;)
            text = res.content.decode('utf-8-sig')
            f = StringIO(text)
            return list(csv.reader(f, delimiter=';'))
    except Exception as e:
        logging.error(f"Lỗi tải file: {e}")
        return []

# --- XỬ LÝ TIN NHẮN ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    ticker = update.message.text.strip().upper()
    wait = await update.message.reply_text(f"🔍 Đang lọc lệnh cho mã: {ticker}...")

    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    def filter_data(rows, symbol):
        results = []
        if not rows: return []
        for r in rows:
            # Kiểm tra mã khớp tuyệt đối ở cột đầu tiên
            if len(r) > 0 and str(r[0]).strip().upper() == symbol:
                # Cấu trúc: r[0]=Mã, r[1]=Ngày, r[3]=Giá
                date_val = r[1] if len(r) > 1 else "N/A"
                price_val = r[3] if len(r) > 3 else (r[-1] if len(r) > 1 else "0")
                results.append(f"🔹 {symbol} | {date_val} | Giá: {price_val}")
        return results[-10:]

    buy_list = filter_data(buy_raw, ticker)
    sell_list = filter_data(sell_raw, ticker)

    if not buy_list and not sell_list:
        # Lấy danh sách mã thực tế bot đang thấy để Alex đối chiếu
        samples = list(set([str(r[0]).strip() for r in buy_raw[1:15] if len(r) > 0 and r[0] != "Ticker"]))
        await wait.edit_text(
            f"❌ Không thấy mã: {ticker}\n\n"
            f"📍 Danh sách mã bot đang đọc được:\n`{', '.join(samples)}`"
        )
        return

    msg = f"📌 **KẾT QUẢ: {ticker}**\n\n"
    if buy_list:
        msg += "🟩 **LỆNH MUA:**\n" + "\n".join(buy_list)
    if sell_list:
        msg += "\n\n🟥 **LỆNH BÁN:**\n" + "\n".join(sell_list)
    
    await wait.edit_text(msg, parse_mode="Markdown")

# --- WEB SERVER ĐỂ DUY TRÌ RENDER ---
server = Flask(__name__)
@server.route("/")
def home(): return "Bot is Online"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)

# --- CHẠY CHÍNH ---
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        logging.error("Chưa cấu hình BOT_TOKEN!")
        return
    
    # Khởi tạo Application
    app = ApplicationBuilder().token(token).build()
    
    # Đăng ký xử lý tin nhắn
    app.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("Chào Alex! Nhập mã chứng khoán để xem lệnh.")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Chạy Flask ở luồng riêng
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Chạy Polling - drop_pending_updates=True để xóa lỗi Conflict
    logging.info("🚀 Bot đang khởi động...")
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
