import os, csv, httpx, asyncio, threading, codecs, logging
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

# --- TẢI CSV ---
async def fetch_csv(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=20.0)
            res.raise_for_status()
            text = res.text.replace("\ufeff", "")  # loại ký tự ẩn
            f = StringIO(text)
            try:
                dialect = csv.Sniffer().sniff(text[:1000])
                return list(csv.reader(f, dialect))
            except:
                return list(csv.reader(f))
    except Exception as e:
        logging.error(f"Lỗi tải CSV: {e}")
        return []

# --- XỬ LÝ TÌM KIẾM ---
def filter_logic(rows, symbol):
    results = []
    if not rows or len(rows) < 2:
        return []

    for r in rows[1:]:  # bỏ header
        if len(r) < 2:
            continue

        raw_ticker = str(r[0]).strip().upper().replace("\ufeff", "")

        # ❌ bỏ hoàn toàn mã NN
        if raw_ticker.endswith("_NN"):
            continue

        # ✔ khớp chính xác
        if raw_ticker == symbol:
            price = r[3] if len(r) > 3 else r[-1]
            results.append(f"🔹 {raw_ticker} | {r[1]} | Giá: {price}")

    return results[-10:]

# --- BOT ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    ticker = update.message.text.strip().upper()
    wait = await update.message.reply_text(f"🔍 Đang tìm mã: {ticker}...")

    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    buy_list = filter_logic(buy_raw, ticker)
    sell_list = filter_logic(sell_raw, ticker)

    if not buy_list and not sell_list:
        samples = [str(r[0]).strip() for r in buy_raw[1:6] if r]
        await wait.edit_text(f"❌ Không thấy mã: {ticker}\n\nMã bot thấy: {', '.join(samples)}")
        return

    msg = f"📌 **KẾT QUẢ: {ticker}**\n\n🟩 **MUA:**\n" + \
          "\n".join(buy_list) + "\n\n🟥 **BÁN:**\n" + \
          "\n".join(sell_list)

    await wait.edit_text(msg, parse_mode="Markdown")

# --- FLASK ĐỂ RENDER ---
server = Flask(__name__)
@server.route("/")
def home():
    return "Bot is Alive"

def run_flask():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# --- RUN ---
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    threading.Thread(target=run_flask, daemon=True).start()

    print("🚀 Bot đang chạy...")
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
