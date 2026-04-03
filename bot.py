import os
import gspread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Google Sheet
SHEET_ID = "1gtik6y2TFILQ5B4R9FMrMzNviRcyGfX-GkjmvOd4xPs"

gc = gspread.Client(auth=None)
sheet_buy = gc.open_by_key(SHEET_ID).worksheet("Buy")
sheet_sell = gc.open_by_key(SHEET_ID).worksheet("Sell")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Nhập mã cổ phiếu để xem lịch sử giao dịch.")

async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.upper().strip()

    buy_data = sheet_buy.get_all_records()
    sell_data = sheet_sell.get_all_records()

    buy_list = [row for row in buy_data if row.get("Ticker") == ticker]
    sell_list = [row for row in sell_data if row.get("Ticker") == ticker]

    if not buy_list and not sell_list:
        await update.message.reply_text(f"Không có giao dịch cho {ticker}.")
        return

    result = f"📌 LỊCH SỬ GIAO DỊCH: {ticker}\n\n"

    if buy_list:
        result += "🟢 MUA:\n"
        for row in buy_list:
            result += f"- {row.get('Date/Time')} | SL {row.get('Mua')} | Giá {row.get('Giá')}\n"
        result += "\n"

    if sell_list:
        result += "🔴 BÁN:\n"
        for row in sell_list:
            result += f"- {row.get('Date/Time')} | SL {row.get('Bán')} | Giá {row.get('Giá')}\n"

    await update.message.reply_text(result)

def main():
    import os
    TOKEN = os.getenv("BOT_TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))

    app.run_polling()

main()
