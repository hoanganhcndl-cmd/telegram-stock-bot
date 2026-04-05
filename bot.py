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
            f = StringIO(content.decode('utf-8'))
            return list(csv.reader(f)) # Dùng reader thường để lấy theo chỉ số cột (0, 1, 2)
    except: return []

async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = str(update.message.text).strip().upper()
    wait = await update.message.reply_text(f"🔍 Đang tìm mã: {user_input}...")

    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    def filter_data(rows, symbol):
        results = []
        if not rows or len(rows) < 2: return []
        # Bỏ qua hàng tiêu đề (rows[0]), duyệt từ hàng 1
        for r in rows[1:]:
            if len(r) < 3: continue
            # r[0] là cột Ticker, r[1] là Date/Time, r[2] là Giá
            db_ticker = str(r[0]).strip().upper()
            if db_ticker == symbol:
                results.append(f"🔹 {db_ticker} | {r[1]} | Giá: {r[2]}")
        return results[-10:]

    buy_list = filter_data(buy_raw, user_input)
    sell_list = filter_data(sell_raw, user_input)

    if not buy_list and not sell_list:
        # Nếu vẫn không thấy, liệt kê 3 mã đầu tiên bot thấy trong sheet để kiểm tra
        sample = [str(r[0]).strip() for r in buy_raw[1:4]] if len(buy_raw) > 1 else ["Trống"]
        await wait.edit_text(f"❌ Không khớp mã: {user_input}\nMã trong Sheets bot thấy là: {', '.join(sample)}")
        return

    msg = f"📌 **KẾT QUẢ: {user_input}**\n\n🟩 **MUA:**\n" + "\n".join(buy_list) + "\n\n🟥 **BÁN:**\n" + "\n".join(sell_list)
    await wait.edit_text(msg, parse_mode="Markdown")

# --- PHẦN SERVER GIỮ NGUYÊN ---
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
