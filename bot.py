import os
import csv
import requests
from io import StringIO
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ================================
#        CONFIG
# ================================
BUY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=0&single=true&output=csv"
SELL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6Xwxi0HpFNQWZiXg72eJfa2b1kaU3r2Be7B1I_hjj42k0NkAKJe0W3vM56KewYW52bkUIFLsvbn66/pub?gid=968456620&single=true&output=csv"

MAX_ROWS = 20


# ================================
#     READ CSV FUNCTION
# ================================
def get_sheet_data(url):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        f = StringIO(res.text)
        return list(csv.DictReader(f))
    except Exception as e:
        print("Error loading sheet:", e)
        return []


# ================================
#     TELEGRAM BOT HANDLERS
# ================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Chào bạn!\n"
        "Nhập mã chứng khoán để xem lịch sử BUY/SELL (tối đa 20 dòng).\n"
        "Ví dụ: **FPT**, **VIC**, **SSI**"
    )


async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.upper().strip()

    buy_data = get_sheet_data(BUY_URL)
    sell_data = get_sheet_data(SELL_URL)

    # Lọc dữ liệu
    buy_list = [row for row in buy_data if row.get("Ticker") == ticker][-MAX_ROWS:]
    sell_list = [row for row in sell_data if row.get("Ticker") == ticker][-MAX_ROWS:]

    # Đảo ngược để mới nhất lên đầu
    buy_list.reverse()
    sell_list.reverse()

    if not buy_list and not sell_list:
        await update.message.reply_text(f"❌ Không có giao dịch cho {ticker}.")
        return

    msg = f"📌 **LỊCH SỬ GIAO DỊCH {ticker}**\n"

    # BUY
    if buy_list:
        msg += "\n🟩 **BUY gần nhất:**\n"
        for row in buy_list:
            msg += f"- {row.get('Time')} | Giá: {row.get('Price')} | KL: {row.get('Volume')}\n"
    else:
        msg += "\n🟩 BUY: Không có dữ liệu\n"

    # SELL
    if sell_list:
        msg += "\n🟥 **SELL gần nhất:**\n"
        for row in sell_list:
            msg += f"- {row.get('Time')} | Giá: {row.get('Price')} | KL: {row.get('Volume')}\n"
    else:
        msg += "\n🟥 SELL: Không có dữ liệu\n"

    await update.message.reply_text(msg)


# ================================
#            MAIN
# ================================
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise ValueError("❌ Thiếu BOT_TOKEN trong Environment!")

    app = ApplicationBuilder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))

    # Text message = ticker
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))

    print("🚀 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
