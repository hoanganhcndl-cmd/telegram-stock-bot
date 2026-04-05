import os
import csv
import httpx
import logging
import asyncio
import codecs
from io import StringIO
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH ---
logging.basicConfig(level=logging.INFO)
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

# --- KHỞI TẠO FLASK & BOT ---
app = Flask(__name__)
TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") # Render tự cấp biến này

# Khởi tạo Application của Telegram
tg_app = Application.builder().token(TOKEN).build()

# --- HÀM TẢI DỮ LIỆU ---
async def fetch_csv(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=15.0)
            res.raise_for_status()
            # Xử lý lỗi font/ký tự lạ từ Google Sheets
            text = res.content.decode('utf-8-sig')
            f = StringIO(text)
            # Tự dò dấu phẩy hoặc chấm phẩy
            try:
                dialect = csv.Sniffer().sniff(text[:1000])
                return list(csv.reader(f, dialect))
            except:
                return list(csv.reader(f))
    except Exception as e:
        logging.error(f"Lỗi tải dữ liệu: {e}")
        return []

# --- XỬ LÝ TIN NHẮN ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    ticker = update.message.text.strip().upper()
    wait_msg = await update.message.reply_text(f"🔍 Đang quét dữ liệu mã: {ticker}...")

    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    def get_data(rows, symbol):
        results = []
        if not rows: return []
        for r in rows:
            if not r: continue
            # r[0] là Mã, r[1] là Ngày, r[3] là Giá (Theo cấu trúc của Alex)
            db_ticker = str(r[0]).strip().upper()
            if db_ticker == symbol:
                date_val = r[1] if len(r) > 1 else "N/A"
                price_val = r[3] if len(r) > 3 else (r[-1] if len(r) > 1 else "0")
                results.append(f"🔹 {db_ticker} | {date_val} | Giá: {price_val}")
        return results[-10:]

    buy_list = get_data(buy_raw, ticker)
    sell_list = get_data(sell_raw, ticker)

    if not buy_list and not sell_list:
        # Debug nếu không thấy mã
        sample = [str(r[0]).strip() for r in buy_raw[1:6] if r]
        await wait_msg.edit_text(f"❌ Không khớp mã: {ticker}\n\nMã bot thấy trong Sheet là: {', '.join(sample)}")
        return

    msg = f"📌 **KẾT QUẢ: {ticker}**\n\n🟩 **MUA:**\n" + "\n".join(buy_list) + "\n\n🟥 **BÁN:**\n" + "\n".join(sell_list)
    await wait_msg.edit_text(msg, parse_mode="Markdown")

# --- WEBHOOK ROUTE ---
@app.route(f"/{TOKEN}", methods=['POST'])
async def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), tg_app.bot)
        await tg_app.process_update(update)
        return "OK", 200

@app.route("/")
def index():
    return "Bot is running with Webhook!", 200

# --- ĐĂNG KÝ HANDLER ---
tg_app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Chào Alex! Nhập mã CK để xem lệnh.")))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- CHẠY SERVER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    
    # Thiết lập Webhook với Telegram
    async def set_webhook():
        await tg_app.bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
        logging.info(f"Webhook set to: {RENDER_URL}/{TOKEN}")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    
    # Chạy Flask app
    app.run(host="0.0.0.0", port=port)
