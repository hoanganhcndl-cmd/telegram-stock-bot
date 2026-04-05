import os, csv, httpx, asyncio, threading, codecs, logging
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

# Link CSV của Alex
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

async def fetch_csv(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=30.0, follow_redirects=True)
            if res.status_code != 200: return []
            
            # Dùng utf-8-sig để XÓA KÝ TỰ BOM (Lỗi làm bot không thấy mã)
            content = res.content.decode('utf-8-sig')
            f = StringIO(content)
            
            # File của Alex dùng dấu phẩy (,)
            reader = csv.reader(f, delimiter=',')
            return list(reader)
    except Exception as e:
        logging.error(f"Lỗi: {e}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    # Lấy mã, xóa cách, viết hoa. Đổi '-' thành '_' cho khớp SSI_NN
    user_input = str(update.message.text).strip().upper().replace('-', '_')
    
    wait_msg = await update.message.reply_text(f"🔍 Đang quét dữ liệu cho mã: {user_input}...")

    buy_data = await fetch_csv(BUY_URL)
    sell_data = await fetch_csv(SELL_URL)

    def find_ticker(rows, ticker):
        results = []
        if not rows: return []
        for r in rows:
            if len(r) >= 5:
                # Xóa mọi khoảng trắng ẩn trong tên mã ở file
                row_ticker = str(r[0]).strip().upper()
                
                # Tìm kiếm (Ví dụ gõ SSI vẫn ra SSI_NN)
                if ticker in row_ticker:
                    date = r[1]
                    price = r[4]
                    results.append(f"🔹 {row_ticker} | {date} | Giá: {price}")
        return results[-10:]

    buy_list = find_ticker(buy_data, user_input)
    sell_list = find_ticker(sell_data, user_input)

    if not buy_list and not sell_list:
        # Nếu không thấy, liệt kê 5 mã đầu tiên bot ĐANG THỰC SỰ ĐỌC ĐƯỢC
        sample_codes = [str(r[0]).strip() for r in buy_data[1:6] if len(r) > 0]
        msg = f"❌ Không tìm thấy dữ liệu cho mã: {user_input}\n\n"
        msg += f"📍 Danh sách mã bot thấy trong file: {', '.join(sample_codes)}"
        await wait_msg.edit_text(msg)
        return

    response = f"📌 **KẾT QUẢ: {user_input}**\n\n"
    if buy_list:
        response += "🟩 **LỆNH MUA:**\n" + "\n".join(buy_list)
    if sell_list:
        response += "\n\n🟥 **LỆNH BÁN:**\n" + "\n".join(sell_list)
    
    await wait_msg.edit_text(response, parse_mode="Markdown")

# --- PHẦN SERVER RENDER ---
app_flask = Flask(__name__)
@app_flask.route('/')
def index(): return "Bot is running"

def run_flask():
    app_flask.run(host='0.0.0.0', port=10000)

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    threading.Thread(target=run_flask, daemon=True).start()
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
