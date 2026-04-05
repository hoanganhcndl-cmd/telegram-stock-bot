import os, csv, httpx, asyncio, threading, codecs
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIG ---
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

async def fetch_csv(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=15.0)
            res.raise_for_status()
            content = res.content
            if content.startswith(codecs.BOM_UTF8):
                content = content[len(codecs.BOM_UTF8):]
            text = content.decode('utf-8')
            
            # TỰ DÒ DẤU PHÂN CÁCH (Dấu phẩy hoặc Dấu chấm phẩy)
            dialect = csv.Sniffer().sniff(text[:2000]) if ',' in text[:100] or ';' in text[:100] else None
            delimiter = dialect.delimiter if dialect else ','
            
            f = StringIO(text)
            return list(csv.reader(f, delimiter=delimiter))
    except: return []

async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = str(update.message.text).strip().upper()
    wait = await update.message.reply_text(f"🔍 Đang tìm mã: {user_input}...")

    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    def filter_data(rows, symbol):
        results = []
        if not rows or len(rows) < 2: return []
        for r in rows[1:]:
            if len(r) < 3: continue
            # r[0] là Ticker, r[1] là Date/Time, r[3] là Giá (như bạn mô tả)
            # Nếu dòng của bạn ngắn hơn, mình sẽ lấy r[-1] làm giá để an toàn
            db_ticker = str(r[0]).strip().upper()
            if db_ticker == symbol:
                p = r[3] if len(r) > 3 else r[-1]
                results.append(f"🔹 {db_ticker} | {r[1]} | Giá: {p}")
        return results[-10:]

    buy_list = filter_data(buy_raw, user_input)
    sell_list = filter_data(sell_raw, user_input)

    if not buy_list and not sell_list:
        # --- BƯỚC QUAN TRỌNG: HIỆN 10 MÃ ĐẦU TIÊN ĐỂ KIỂM TRA ---
        all_codes = []
        if buy_raw and len(buy_raw) > 1:
            all_codes = list(set([str(r[0]).strip() for r in buy_raw[1:15]]))
        
        await wait.edit_text(
            f"❌ Không thấy mã: {user_input}\n\n"
            f"📍 Danh sách 10 mã Bot ĐANG THẤY trong Sheets:\n`{', '.join(all_codes)}`"
        )
        return

    msg = f"📌 **KẾT QUẢ: {user_input}**\n\n🟩 **MUA:**\n" + "\n".join(buy_list) + "\n\n🟥 **BÁN:**\n" + "\n".join(sell_list)
    await wait.edit_text(msg, parse_mode="Markdown")

# --- SERVER & RUN ---
server = Flask(__name__)
@server.route("/")
def home(): return "OK"

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))
    threading.Thread(target=lambda: server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__": main()
