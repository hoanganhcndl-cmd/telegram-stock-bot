import os, csv, httpx, asyncio, threading, codecs
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- THAY LINK CSV MỚI CỦA BẠN VÀO ĐÂY ---
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

async def fetch_csv(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=20.0, follow_redirects=True)
            if res.status_code != 200: return []
            text = res.content.decode('utf-8-sig')
            
            # Kiểm tra nếu link trả về HTML (trang web) thay vì dữ liệu
            if "<html" in text.lower():
                return "ERROR_LINK"
                
            f = StringIO(text)
            try:
                dialect = csv.Sniffer().sniff(text[:1000])
                return list(csv.reader(f, dialect))
            except:
                return list(csv.reader(f))
    except: return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.strip().upper()
    wait = await update.message.reply_text(f"🔍 Đang kết nối dữ liệu...")

    buy_raw = await fetch_csv(BUY_URL)
    
    if buy_raw == "ERROR_LINK":
        await wait.edit_text("⚠️ LỖI: Link Google Sheets chưa đúng định dạng CSV. Alex hãy vào 'Công bố lên web' và chọn định dạng .csv nhé!")
        return

    if not buy_raw:
        await wait.edit_text("⚠️ LỖI: Không thể tải dữ liệu. Kiểm tra kết nối Internet hoặc Link Sheets.")
        return

    def filter_logic(rows, symbol):
        results = []
        for r in rows:
            # Kiểm tra mã ở cột 0, ngày cột 1, giá cột 3
            if len(r) > 1 and str(r[0]).strip().upper() == symbol:
                p = r[3] if len(r) > 3 else r[-1]
                results.append(f"🔹 {r[0]} | {r[1]} | Giá: {p}")
        return results[-10:]

    buy_list = filter_logic(buy_raw, ticker)
    # Lấy dữ liệu bán tương tự
    sell_raw = await fetch_csv(SELL_URL)
    sell_list = filter_logic(sell_raw, ticker) if sell_raw != "ERROR_LINK" else []

    if not buy_list and not sell_list:
        # Lấy danh sách mã thực tế để đối chiếu
        samples = [str(r[0]).strip() for r in buy_raw[:8] if len(r) > 0 and r[0] != "Ticker"]
        await wait.edit_text(f"❌ Không thấy mã: {ticker}\n\n📍 Các mã bot ĐANG ĐỌC ĐƯỢC: {', '.join(samples)}")
        return

    msg = f"📌 **KẾT QUẢ: {ticker}**\n\n🟩 **MUA:**\n" + "\n".join(buy_list) + "\n\n🟥 **BÁN:**\n" + "\n".join(sell_list)
    await wait.edit_text(msg, parse_mode="Markdown")

# --- SERVER ---
server = Flask(__name__)
@server.route("/")
def home(): return "OK"

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    threading.Thread(target=lambda: server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__": main()
