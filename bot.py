import os
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from flask import Flask
import threading

# ... (Giữ nguyên phần fetch_csv và các hàm xử lý start, search_ticker) ...

# ===========================
# FLASK WEB (Giữ Render không ngủ)
# ===========================
server = Flask(__name__)

@server.route("/")
def home():
    return "Bot is running!"

def run_flask():
    # Render cung cấp biến PORT, mặc định là 10000
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)

# ===========================
# CHẠY BOT (Cấu hình chuẩn v20.6)
# ===========================
async def run_bot():
    # Lấy TOKEN từ Environment Variable trên Render
    TOKEN = os.getenv("BOT_TOKEN")
    
    # Khởi tạo Application thay vì Updater
    app = ApplicationBuilder().token(TOKEN).build()

    # Thêm các handler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ticker))

    print("🚀 Bot Telegram đang bắt đầu polling...")
    
    # Chạy bot
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        # Giữ bot chạy vô tận
        await asyncio.Event().wait()

if __name__ == "__main__":
    # 1. Chạy Flask trong một luồng riêng (Background Thread)
    threading.Thread(target=run_flask, daemon=True).start()

    # 2. Chạy Bot Telegram trong luồng chính (Main Async Loop)
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        pass
