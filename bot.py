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

            text = content.decode("utf-8")

            # Auto detect delimiter
            dialect = csv.Sniffer().sniff(text[:2000]) if ',' in text[:100] or ';' in text[:100] else None
            delimiter = dialect.delimiter if dialect else ','

            f = StringIO(text)
            return list(csv.reader(f, delimiter=delimiter))
    except:
        return []


def filter_data(rows, symbol):
    results = []
    if not rows or len(rows) < 2:
        return results

    headers = rows[0]
    col_ticker = 0
    col_time = 1
    col_price = 3 if len(headers) > 3 else -1
    col_nn = None

    # Tìm cột NN đúng
    for i, h in enumerate(headers):
        if h.strip().upper() == "NN":
            col_nn = i
            break

    for r in rows[1:]:
        if len(r) < 3:
            continue

        db_ticker = str(r[col_ticker]).strip().upper()

        # MATCH MÃ
        if db_ticker != symbol:
            continue

        # --- LOẠI BỎ MÃ CÓ NN ---
        if col_nn is not None and col_nn < len(r):
            raw_nn = str(r[col_nn])

            # Xóa toàn bộ khoảng trắng, tab, ký tự ẩn
            nn_clean = "".join(raw_nn.split()).upper()

            # Nếu ô NN thực sự có chữ → LOẠI
            if nn_clean not in ["", "NO"]:
                continue

        # Lấy giá
        p = r[col_price] if len(r) > 3 else r[-1]

        results.append(f"🔹 {db_ticker} | {r[col_time]} | Giá: {p}")

    return results[-10:]  # 10 dòng mới nhất


async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip().upper()
    wait = await update.message.reply_text(f"🔍 Đang tìm mã: {user_input}...")

    buy_raw = await fetch_csv(BUY_URL)
    sell_raw = await fetch_csv(SELL_URL)

    buy_list = filter_data(buy_raw, user_input)
    sell_list = filter_data(sell_raw, user_input)

    if not buy_list and not sell_list:
        # Thử hiển thị 10 mã đầu tiên đang đọc được
        all_codes = []
        if buy_raw and len(buy_raw) > 1:
            all_codes = list(set([str(r[0]).strip() for r in buy_raw[1:15]]))

        await wait.edit_text(
            f"❌ Không thấy mã: {user_input}\n\n"
            f"📍 10 mã Bot nhìn thấy trong file:\n`{', '.join(all_codes)}`"
        )
        return

    msg = (
        f"📌 **KẾT QUẢ: {user_input}**\n\n"
        f"🟩 **MUA:**\n" + ("\n".join(buy_list) if buy_list else "Không có") +
        f"\n\n🟥 **BÁN:**\n" + ("\n".join(sell_list) if sell_list else "Không có")
    )

    await wait.edit_text(msg, parse_mode="Markdown")


# --- SERVER & RUN ---
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
