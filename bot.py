import os, csv, httpx, asyncio, threading, codecs, logging
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH ---
logging.basicConfig(level=logging.INFO)
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

async def fetch_csv(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=25.0, follow_redirects=True)
            if res.status_code != 200: return []
            text = res.content.decode('utf-8-sig')
            f = StringIO(text)
            # Dữ liệu Alex dùng dấu chấm phẩy (;)
            return list(csv.reader(f, delimiter=';'))
    except: return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    # Xử lý mã người dùng nhập: Viết hoa, xóa cách
    user_input = str(update.message.text).strip().upper()
    wait = await update.message.reply_text(f"🔍 Đang rà soát dữ liệu mã: {user_input}...")

    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    def process_data(rows, symbol):
        found = []
        if not rows: return []
        for r in rows:
            if len(r) < 2: continue
            
            # LẤY MÃ Ở CỘT 0 VÀ XÓA SẠCH KHOẢNG TRẮNG
            db_ticker = str(r[0]).strip().upper()
            
            # SO SÁNH (Dùng == để chính xác tuyệt đối sau khi đã strip)
            if db_ticker == symbol:
                date_val = r[1] if len(r) > 1 else "N/A"
                # Lấy cột giá (thường là cột 3 hoặc cột cuối cùng)
                price_val = r[3] if len(r) > 3 else r[-1]
                found.append(f"🔹 {db_ticker} | {date_val} | Giá: {price_val}")
        return found[-10:]

    buy_list = process_data(buy_raw, user_input)
    sell_list = process_data(sell_raw, user_input)

    if not buy_list and not sell_list:
        # LẤY MẪU ĐỂ ALEX KIỂM TRA (Hiện dấu ngoặc đơn để xem có khoảng trắng không)
        samples = [f"'{str(r[0]).strip()}'" for r in buy_raw[1:10] if len(r) > 0]
        await wait.edit_text(
            f"❌ Không thấy mã: {user_input}\n\n"
            f"📍 Bot đang thấy các mã này trong Sheets:\n{', '.join(samples[:10])}\n\n"
            f"👉 Nếu bạn thấy mã trong dấu nháy đơn có khoảng trắng, hãy kiểm tra lại file gốc nhé!"
        )
        return

    msg = f"📌 **KẾT QUẢ: {user_input}**\n\n"
    if buy_list: msg += "🟩 **MUA:**\n" + "\n".join(buy_list)
    if sell_list: msg += "\n\n🟥 **BÁN:**\n" + "\n".join(sell_list)
    
    await wait.edit_text(msg, parse_mode="Markdown")

# --- PHẦN SERVER ---
server = Flask(__name__)
@server.route("/")
def home(): return "OK"

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    threading.Thread(target=lambda: server.run(host="0.0.0.0", port=10000), daemon=True).start()
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__": main()
