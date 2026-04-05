import os, csv, httpx, asyncio, threading, codecs, logging
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH ---
logging.basicConfig(level=logging.INFO)
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

# --- HÀM TẢI DỮ LIỆU ---
async def fetch_csv(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=20.0)
            res.raise_for_status()
            text = res.content.decode('utf-8-sig') # Xử lý ký tự lạ
            f = StringIO(text)
            # Tự dò dấu phẩy hoặc chấm phẩy
            try:
                dialect = csv.Sniffer().sniff(text[:1000])
                return list(csv.reader(f, dialect))
            except:
                return list(csv.reader(f))
    except Exception as e:
        logging.error(f"Lỗi tải CSV: {e}")
        return []

# --- XỬ LÝ TIN NHẮN ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    ticker = update.message.text.strip().upper()
    wait = await update.message.reply_text(f"🔍 Đang tìm mã: {ticker}...")

    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    def filter_logic(rows, symbol):
        results = []
        if not rows or len(rows) < 2: return []
        for r in rows:
            if len(r) < 2: continue
            # So khớp cột đầu tiên (Ticker)
            if str(r[0]).strip().upper() == symbol:
                # Lấy cột 2 (Ngày) và cột 4 (Giá) theo dữ liệu của Alex
                p = r[3] if len(r) > 3 else r[-1]
                results.append(f"🔹 {r[0]} | {r[1]} | Giá: {p}")
        return results[-10:]

    buy_list = filter_logic(buy_raw, ticker)
    sell_list = filter_logic(sell_raw, ticker)

    if not buy_list and not sell_list:
        # Gợi ý mã nếu không tìm thấy
        samples = [str(r[0]).strip() for r in buy_raw[1:6] if r]
        await wait.edit_text(f"❌ Không thấy mã: {ticker}\n\nMã bot thấy: {', '.join(samples)}")
        return

    msg = f"📌 **KẾT QUẢ: {ticker}**\n\n🟩 **MUA:**\n" + "\n".join(buy_list) + "\n\n🟥 **BÁN:**\n" + "\n".join(sell_list)
    await wait.edit_text(msg, parse_mode="Markdown")

# --- SERVER ĐỂ RENDER KHÔNG NGẮT ---
server = Flask(__name__)
@server.route("/")
def home(): return "Bot is Alive"

def run_flask():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# --- CHẠY CHÍNH ---
def main():
    token = os.getenv("BOT_TOKEN")
    if not token: return
    
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("Chào Alex! Nhập mã CK.")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Chạy Web Server ở luồng riêng
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Chạy Polling và tự động xóa Webhook cũ (Fix lỗi không phản hồi)
    print("🚀 Bot đang chạy...")
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
