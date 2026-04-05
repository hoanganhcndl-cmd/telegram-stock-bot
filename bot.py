import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ------------------------------
# /start
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Xin chào! Gõ mã cổ phiếu để tra cứu (VD: VNM, FPT, HPG...)."
    )

# ------------------------------
# Hàm tra ticker
# ------------------------------
async def search_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()

    # Demo dữ liệu – bạn thay API thật vào đây
    fake_data = {
        "VNM": "Vinamilk – Giá: 68.500 – +1.2%",
        "FPT": "FPT – Giá: 129.200 – +0.5%",
        "HPG": "Hòa Phát – Giá: 29.900 – -0.3%",
    }

    if text in fake_data:
        await update.message.reply_text(fake_data[text])
    else:
        await update.message.reply_text(f"Không tìm thấy mã: {text}")

# ------------------------------
# MAIN APP
# ------------------------------
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise Exception("Thiếu biến môi trường BOT_TOKEN!!!")

    app = Application.builder().token(token).build()

    # Lệnh /start
    app.add_handler(CommandHandler("start", start))

    # Tất cả tin nhắn TEXT KHÔNG PHẢI LỆNH → search ticker
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))

    # Webhook URL (Render)
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        raise Exception("Thiếu biến môi trường WEBHOOK_URL!!!")

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 10000)),
        webhook_url=webhook_url
    )

# ------------------------------
# RUN
# ------------------------------
if __name__ == "__main__":
    main()
