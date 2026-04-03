import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# Flask web server
app = Flask(__name__)

# Telegram Application
tg_app = ApplicationBuilder().token(TOKEN).build()


# ---------- TELEGRAM WEBHOOK ROUTE ----------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    tg_app.update_queue.put(update)
    return "ok", 200


# ---------- BOT COMMAND ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot hoạt động OK!")


tg_app.add_handler(CommandHandler("start", start))


# ---------- RUN BOTH TELEGRAM + FLASK ----------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))

    # Khởi động Webhook Listener
    tg_app.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url="https://telegram-stock-bot-q9bi.onrender.com/webhook"
    )

    # KHỞI ĐỘNG FLASK SERVER (QUAN TRỌNG)
    app.run(host="0.0.0.0", port=port)
