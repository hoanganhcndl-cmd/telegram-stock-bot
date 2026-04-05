import os, csv, httpx, asyncio, threading, codecs
from io import StringIO
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

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
            
            # autodetect delimiter
            try:
                dialect = csv.Sniffer().sniff(text[:2000])
                delimiter = dialect.delimiter
            except:
                delimiter = ","
            
            f = StringIO(text)
            return list(csv.reader(f, delimiter=delimiter))
    except:
        return []

# === CHỈ SỬA CHỖ NÀY — FILTER_DATA ===
def filter_data(rows, symbol):
    results = []
    if not rows or len(rows) < 2:
        return []

    symbol = symbol.upper()

    for r in rows[1:]:
        if len(r) < 5:
            continue

        db_ticker = str(r[0]).strip().upper()

        # ❌ Loại bỏ mã NN
        if db_ticker.endswith("_NN"):
            continue

        # ✔ Khớp chính xác mã người dùng
        if db_ticker == symbol:
            price = r[4]  # lấy từ cột "Giá"
            date = r[1]
            results.append(f"🔹 {db_ticker} | {date} | Giá: {price}")

    return results[-10:]

async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = str(update.message.text).strip().upper()
    wait = await update.message.reply_text(f"🔍 Đang tìm mã: {user_input}...")

    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    buy_list = filter_data(buy_raw, user_input)
    sell_list = filter_data(sell_raw, user_input)

    if not buy_list and not sell_list:
        all_codes = []
        if buy_raw and len(buy_raw) > 1:
            all_codes = list(set([str(r[0]).strip() for r in buy_raw[1:15]]))
        
        await wait.edit_text(
            f"❌ Không thấy mã: {user_input}\n\n"
            f"📍 10 mã bot đọc được:\n`{', '.join(all_codes)}`"
        )
        return

    msg = (
        f"📌 **KẾT QUẢ: {user_input}**\n\n"
        f"🟩 **MUA:**\n" + ("\n".join(buy_list) or "Không có") +
        "\n\n🟥 **BÁN:**\n" + ("\n".join(sell_list) or "Không có")
    )

    await wait.edit_text(msg, parse_mode="Markdown")

# --- SERVER ---
server = Flask(__name__)

@server.route("/")
def home():
    return "OK"

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))

    threading.Thread(
        target=lambda: server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))),
        daemon=True
    ).start()

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
