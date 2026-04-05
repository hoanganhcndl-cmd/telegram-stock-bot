import os, csv, httpx, asyncio, threading, codecs
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- LINK ĐÃ KIỂM TRA CHUẨN ---
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

async def fetch_csv(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=25.0, follow_redirects=True)
            if res.status_code != 200: return []
            
            # Xử lý ký tự lạ đầu file (BOM)
            text = res.content.decode('utf-8-sig')
            f = StringIO(text)
            
            # Dữ liệu của Alex dùng dấu chấm phẩy (;) để phân tách
            # Chúng ta dùng delimiter=';' để cắt cột chính xác
            return list(csv.reader(f, delimiter=';'))
    except Exception as e:
        print(f"Lỗi tải file: {e}")
        return []

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
            # Kiểm tra nếu dòng có dữ liệu và cột 0 khớp với mã người dùng nhập
            if len(r) > 0 and str(r[0]).strip().upper() == symbol:
                # Dựa trên file của Alex: r[0]=Ticker, r[1]=Date/Time, r[3]=Giá
                date_val = r[1] if len(r) > 1 else "N/A"
                price_val = r[3] if len(r) > 3 else (r[-1] if len(r) > 1 else "0")
                results.append(f"🔹 {symbol} | {date_val} | Giá: {price_val}")
        return results[-10:] # Lấy 10 lệnh mới nhất

    buy_list = filter_data(buy_raw, ticker)
    sell_list = filter_data(sell_raw, ticker)

    if not buy_list and not sell_list:
        # Nếu không thấy, liệt kê các mã đang có trong file để đối chiếu
        samples = []
        if buy_raw:
            # Lấy thử các mã ở cột đầu tiên (bỏ qua tiêu đề)
            samples = list(set([str(r[0]).strip() for r in buy_raw[1:10] if len(r) > 0]))
        
        await wait.edit_text(
            f"❌ Không thấy mã: {ticker}\n\n"
            f"📍 Danh sách mã bot đang thấy:\n`{', '.join(samples[:15])}`"
        )
        return

    msg = f"📌 **KẾT QUẢ: {ticker}**\n\n"
    if buy_list:
        msg += "🟩 **LỆNH MUA:**\n" + "\n".join(buy_list)
    if sell_list:
        msg += "\n\n🟥 **LỆNH BÁN:**\n" + "\n".join(sell_list)
    
    await wait.edit_text(msg, parse_mode="Markdown")

# --- PHẦN SERVER GIỮ NGUYÊN ---
server = Flask(__name__)
@server.route("/")
def home(): return "OK"

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    threading.Thread(target=lambda: server.run(host="0.0.0.0", port=10000), daemon=True).start()
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
