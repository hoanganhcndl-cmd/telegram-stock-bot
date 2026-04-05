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
            # Dùng reader thường để lấy dữ liệu theo vị trí cột 0, 1, 2, 3...
            return list(csv.reader(f)) 
    except: return []

async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Người dùng gõ "AST", bot sẽ tìm đúng "AST" và bỏ qua "AST_NN"
    user_input = str(update.message.text).strip().upper()
    wait = await update.message.reply_text(f"🔍 Đang tìm chính xác mã: {user_input}...")

    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    def filter_data(rows, symbol):
        results = []
        if not rows or len(rows) < 2: return []
        
        for r in rows[1:]: # Bỏ qua dòng tiêu đề
            if len(r) < 4: continue 
            
            # Dựa theo dữ liệu bạn gửi:
            # r[0] = Ticker (Mã)
            # r[1] = Date/Time (Ngày)
            # r[3] = Giá (Cột thứ 4 trong file của bạn)
            
            db_ticker = str(r[0]).strip().upper()
            
            # SO KHỚP TUYỆT ĐỐI (Chỉ lấy AST, ko lấy AST_NN)
            if db_ticker == symbol:
                date_val = r[1]
                price_val = r[3] # Lấy cột thứ 4 là cột Giá
                results.append(f"🔹 {db_ticker} | {date_val} | Giá: {price_val}")
        
        return results[-10:]

    buy_list = filter_data(buy_raw, user_input)
    sell_list = filter_data(sell_raw, user_input)

    if not buy_list and not sell_list:
        # Nếu ko thấy, liệt kê các mã đang có trong Sheet để Alex xem
        all_codes = list(set([str(r[0]).strip() for r in buy_raw[1:10] if len(r) > 0]))
        await wait.edit_text(f"❌ Không thấy mã khớp 100%: {user_input}\n\nMã bot thấy trong Sheet là: {', '.join(all_codes)}")
        return

    msg = f"📌 **KẾT QUẢ: {user_input}**\n\n🟩 **MUA:**\n" + "\n".join(buy_list) + "\n\n🟥 **BÁN:**\n" + "\n".join(sell_list)
    await wait.edit_text(msg, parse_mode="Markdown")

# --- SERVER ---
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
