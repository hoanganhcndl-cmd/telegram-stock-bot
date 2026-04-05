import os, csv, httpx, asyncio, threading, codecs, logging
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

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
            
            # TỰ ĐỘNG NHẬN DIỆN DẤU PHẨY HOẶC CHẤM PHẨY
            dialect = csv.Sniffer().sniff(text[:2000]) if (',' in text[:100] or ';' in text[:100]) else None
            delimiter = dialect.delimiter if dialect else ','
            
            return list(csv.reader(f, delimiter=delimiter))
    except: return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_input = str(update.message.text).strip().upper()
    wait = await update.message.reply_text(f"🔍 Đang tìm mã: {user_input}...")

    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    def process_rows(rows, symbol):
        found = []
        if not rows: return []
        for r in rows:
            if len(r) > 1:
                # Xóa sạch khoảng trắng của mã trong file
                db_ticker = str(r[0]).strip().upper()
                
                # SO KHỚP TUYỆT ĐỐI
                if db_ticker == symbol:
                    date_val = r[1]
                    # Lấy cột 4 (Giá) theo đúng file Alex gửi
                    price_val = r[4] if len(r) > 4 else r[-1]
                    found.append(f"🔹 {db_ticker} | {date_val} | Giá: {price_val}")
        return found[-10:]

    buy_list = process_rows(buy_raw, user_input)
    sell_list = process_rows(sell_raw, user_input)

    if not buy_list and not sell_list:
        # Gợi ý mã Bot đang thấy thực tế
        samples = list(set([str(r[0]).strip() for r in buy_raw[1:11] if len(r) > 0]))
        await wait.edit_text(f"❌ Không thấy mã: {user_input}\n\nMã bot thấy trong Sheet: {', '.join(samples)}")
        return

    msg = f"📌 **KẾT QUẢ: {user_input}**\n\n🟩 **MUA:**\n" + "\n".join(buy_list) + "\n\n🟥 **BÁN:**\n" + "\n".join(sell_list)
    await wait.edit_text(msg, parse_mode="Markdown")

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
