import asyncio

import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import get_bot_token, missing_token_message
from strategy import generate_signal

TOKEN = get_bot_token()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Signal Bot is running...")


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = context.args[0] if context.args else "EURUSD=X"

    data = yf.download(symbol, period="1d", interval="5m", progress=False)
    signal_name, expiry, confidence = generate_signal(data)

    await update.message.reply_text(
        f"Asset: {symbol}\n"
        f"Signal: {signal_name}\n"
        f"Expiry: {expiry} minute(s)\n"
        f"Confidence: {confidence}%"
    )


def main():
    if not TOKEN:
        raise RuntimeError(missing_token_message())

    asyncio.set_event_loop(asyncio.new_event_loop())

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))
    app.run_polling()


if __name__ == "__main__":
    main()
