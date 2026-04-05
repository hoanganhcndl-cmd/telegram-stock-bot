import os, csv, httpx, asyncio, threading, logging, time
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
        # Thêm tham số thời gian để ép Google Sheets không dùng cache cũ
        cache_buster = f"&t={int(time.time())}"
        async with httpx.AsyncClient() as client:
            res = await client.get(url + cache_buster, timeout=30.0, follow_redirects=True)
            if res.status_code != 200: return []
            content = res.content.decode('utf-8-sig')
            f = StringIO(content)
            return list(csv.reader(f, delimiter=','))
    except Exception as e:
        logging.error(f"Lỗi tải file: {e}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    # 1. Lấy mã Alex gõ (VD: HPG)
    user_input = str(update.message.text).strip().upper()
    wait_msg = await update.message.reply_text(f"🔍 Đang rà soát dữ liệu: {user_input}...")

    buy_data = await fetch_csv(BUY_URL)
    sell_data = await fetch_csv(SELL_URL)

    def find_ticker(rows, ticker):
        results = []
        if not rows: return []
        for r in reversed(rows):
            if len(r) >= 4:
                row_ticker = str(r[0]).strip().upper()
                
                # LỌC SIÊU SẠCH: 
                # - Khớp 100% (gõ HPG chỉ ra HPG)
                # - Bỏ qua NN, TD, và các mã phái sinh C...
                if row_ticker == ticker:
                    if "_NN" not in row_ticker and "TD" not in row_ticker and not row_ticker.startswith("C"):
                        date = r[1]
                        price = r[3]
                        results.append(f"🔹 {row_ticker} | {date} | Giá: {price}")
        if len(results) >= 10:
                break
                
        return results

    buy_list = find_ticker(buy_data, user_input)
    sell_list = find_ticker(sell_data, user_input)

    if not buy_list and not sell_list:
        await wait_msg.edit_text(f"❌ Không tìm thấy dữ liệu khớp chính xác cho mã: {user_input}")
        return

    response = f"📌 **KẾT QUẢ: {user_input}**\n\n"
    if buy_list: response += "🟩 **LỆNH MUA:**\n" + "\n".join(buy_list)
    if sell_list: response += "\n\n🟥 **LỆNH BÁN:**\n" + "\n".join(sell_list)
    
    await wait_msg.edit_text(response, parse_mode="Markdown")

# --- SERVER FLASK ---
app_flask = Flask(__name__)
@app_flask.route('/')
def index(): 
    return "Bot status: Active"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    threading.Thread(target=run_flask, daemon=True).start()
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
