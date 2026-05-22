# ==========================================
# FILE: main.py
# ==========================================

import asyncio
import math
import sys
import time

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from telegram.error import NetworkError, TimedOut
from telegram.request import HTTPXRequest

from data import get_market_data
from strategy import generate_signal
from memory import get_learning_adjustment, get_profile, update_feedback
from config import get_bot_token, missing_token_message

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

# ==========================================
# BOT TOKEN
# ==========================================

# Type or paste your Telegram bot token between these quotes.
# Example: BOT_TOKEN = "1234567890:ABC-your-token-here"
BOT_TOKEN = ""

TOKEN = BOT_TOKEN.strip() or get_bot_token()

TELEGRAM_CONNECT_TIMEOUT = 30.0
TELEGRAM_READ_TIMEOUT = 30.0
TELEGRAM_WRITE_TIMEOUT = 30.0
TELEGRAM_POOL_TIMEOUT = 10.0
TELEGRAM_RETRY_DELAY = 15

# ==========================================
# ACTIVE SIGNALS
# ==========================================

active_signals = {}

LOSS_REASONS = {
    "reversal": "Trend reversed",
    "late": "Late entry",
    "choppy": "Choppy market",
    "news": "News spike",
    "weak": "Weak momentum"
}

# ==========================================
# START COMMAND
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [

        [
            InlineKeyboardButton(
                "📈 Trade",
                callback_data="trade"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 Stats",
                callback_data="stats"
            )
        ],

        [
            InlineKeyboardButton(
                "ℹ Help",
                callback_data="help"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🤖 Welcome To AI Trading Signal Bot\n\n"
        "Choose an option below:",
        reply_markup=reply_markup
    )

# ==========================================
# BUTTON HANDLER
# ==========================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    data = query.data

    # ======================================
    # TRADE MENU
    # ======================================

    if data == "trade":

        keyboard = [

            [
                InlineKeyboardButton(
                    "💱 Live Forex",
                    callback_data="currency"
                )
            ],

            [
                InlineKeyboardButton(
                    "🌙 OTC Pairs",
                    callback_data="otc"
                )
            ],

            [
                InlineKeyboardButton(
                    "📉 Assets",
                    callback_data="assets"
                )
            ]
        ]

        await query.message.reply_text(
            "📊 Select Market Type:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ======================================
    # LIVE FOREX
    # ======================================

    elif data == "currency":

        keyboard = [

            [
                InlineKeyboardButton(
                    "EUR/USD",
                    callback_data="EURUSD=X"
                ),

                InlineKeyboardButton(
                    "GBP/USD",
                    callback_data="GBPUSD=X"
                )
            ],

            [
                InlineKeyboardButton(
                    "USD/JPY",
                    callback_data="JPY=X"
                ),

                InlineKeyboardButton(
                    "AUD/USD",
                    callback_data="AUDUSD=X"
                )
            ],

            [
                InlineKeyboardButton(
                    "USD/CAD",
                    callback_data="CAD=X"
                ),

                InlineKeyboardButton(
                    "USD/CHF",
                    callback_data="CHF=X"
                )
            ],

            [
                InlineKeyboardButton(
                    "NZD/USD",
                    callback_data="NZDUSD=X"
                ),

                InlineKeyboardButton(
                    "EUR/GBP",
                    callback_data="EURGBP=X"
                )
            ],

            [
                InlineKeyboardButton(
                    "EUR/JPY",
                    callback_data="EURJPY=X"
                ),

                InlineKeyboardButton(
                    "GBP/JPY",
                    callback_data="GBPJPY=X"
                )
            ],

            [
                InlineKeyboardButton(
                    "AUD/JPY",
                    callback_data="AUDJPY=X"
                ),

                InlineKeyboardButton(
                    "EUR/AUD",
                    callback_data="EURAUD=X"
                )
            ]
        ]

        await query.message.reply_text(
            "💱 Select Live Currency Pair:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ======================================
    # OTC PAIRS
    # ======================================

    elif data == "otc":

        keyboard = [

            [
                InlineKeyboardButton(
                    "EUR/USD OTC",
                    callback_data="OTC_EURUSD"
                ),

                InlineKeyboardButton(
                    "GBP/USD OTC",
                    callback_data="OTC_GBPUSD"
                )
            ],

            [
                InlineKeyboardButton(
                    "USD/JPY OTC",
                    callback_data="OTC_USDJPY"
                ),

                InlineKeyboardButton(
                    "AUD/USD OTC",
                    callback_data="OTC_AUDUSD"
                )
            ],

            [
                InlineKeyboardButton(
                    "USD/CAD OTC",
                    callback_data="OTC_USDCAD"
                ),

                InlineKeyboardButton(
                    "USD/CHF OTC",
                    callback_data="OTC_USDCHF"
                )
            ],

            [
                InlineKeyboardButton(
                    "NZD/USD OTC",
                    callback_data="OTC_NZDUSD"
                ),

                InlineKeyboardButton(
                    "EUR/GBP OTC",
                    callback_data="OTC_EURGBP"
                )
            ]
        ]

        await query.message.reply_text(
            "🌙 Select OTC Pair:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ======================================
    # ASSETS
    # ======================================

    elif data == "assets":

        keyboard = [

            [
                InlineKeyboardButton(
                    "Bitcoin",
                    callback_data="BTC-USD"
                ),

                InlineKeyboardButton(
                    "Ethereum",
                    callback_data="ETH-USD"
                )
            ],

            [
                InlineKeyboardButton(
                    "Gold",
                    callback_data="GC=F"
                ),

                InlineKeyboardButton(
                    "Silver",
                    callback_data="SI=F"
                )
            ],

            [
                InlineKeyboardButton(
                    "Oil",
                    callback_data="CL=F"
                ),

                InlineKeyboardButton(
                    "Natural Gas",
                    callback_data="NG=F"
                )
            ],

            [
                InlineKeyboardButton(
                    "Apple",
                    callback_data="AAPL"
                ),

                InlineKeyboardButton(
                    "Tesla",
                    callback_data="TSLA"
                )
            ],

            [
                InlineKeyboardButton(
                    "NVIDIA",
                    callback_data="NVDA"
                ),

                InlineKeyboardButton(
                    "Amazon",
                    callback_data="AMZN"
                )
            ]
        ]

        await query.message.reply_text(
            "📉 Select Asset Pair:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ======================================
    # STATS
    # ======================================

    elif data == "stats":

        profile = get_profile(query.from_user.id)

        wins = profile["wins"]

        losses = profile["losses"]

        total = wins + losses

        if total > 0:
            win_rate = round((wins / total) * 100, 2)
        else:
            win_rate = 0

        await query.message.reply_text(
            f"📊 Your Trading Stats\n\n"
            f"✅ Wins: {wins}\n"
            f"❌ Losses: {losses}\n"
            f"🎯 Win Rate: {win_rate}%"
        )

    # ======================================
    # HELP
    # ======================================

    elif data == "help":

        await query.message.reply_text(
            "📖 HOW TO USE\n\n"
            "1. Click Trade\n"
            "2. Select Market\n"
            "3. Select Pair\n"
            "4. Receive Signal\n"
            "5. Wait For Countdown\n"
            "6. Submit Result\n"
            "7. Bot Learns Over Time"
        )

    # ======================================
    # GENERATE SIGNAL
    # ======================================

    else:

        symbol = data

        otc_mode = False

        if "OTC_" in symbol:

            otc_mode = True

            symbol_name = symbol.replace("OTC_", "") + " OTC"

            market_symbol = "EURUSD=X"

        else:

            symbol_name = symbol

            market_symbol = symbol

        profile = get_profile(query.from_user.id)

        bias = profile["bias"]

        market_data = get_market_data(market_symbol)

        if market_data.attrs.get("is_fallback"):

            await query.message.reply_text(
                "Market data is temporarily unavailable or rate limited.\n"
                "No signal was generated. Try again in a minute, or add an API key."
            )

            return

        signal, expiry, confidence = generate_signal(
            market_data,
            bias
        )

        if signal == "HOLD":

            await query.message.reply_text(
                "⏸ No Strong Signal Available"
            )

            return

        learning = get_learning_adjustment(
            profile,
            symbol_name,
            signal
        )

        if learning["block"]:

            await query.message.reply_text(
                "Signal skipped because this setup has lost too often before.\n"
                f"Pair: {symbol_name}\n"
                f"Signal: {signal}\n"
                f"Common loss reason: {learning['reason'] or 'Unknown'}"
            )

            return

        confidence += learning["confidence_adjustment"]

        if confidence < 65:

            await query.message.reply_text(
                "Signal skipped because your past results lowered confidence for this setup.\n"
                f"Pair: {symbol_name}\n"
                f"Signal: {signal}\n"
                f"Common loss reason: {learning['reason'] or 'Unknown'}"
            )

            return

        confidence = min(98, confidence)

        signal_id = str(time.time())

        active_signals[signal_id] = {
            "user_id": query.from_user.id,
            "symbol": symbol_name,
            "signal": signal
        }

        sent_message = await query.message.reply_text(
            f"📊 Pair: {symbol_name}\n\n"
            f"📢 Signal: {signal}\n"
            f"⏱ Expiry Time: {expiry} Minute(s)\n"
            f"🎯 Confidence: {confidence}%\n\n"
            f"⏳ Countdown Starting..."
        )

        asyncio.create_task(
            run_countdown(
                context,
                sent_message.chat_id,
                sent_message.message_id,
                signal_id,
                symbol_name,
                signal,
                expiry,
                confidence
            )
        )

# ==========================================
# COUNTDOWN
# ==========================================

async def run_countdown(
    context,
    chat_id,
    message_id,
    signal_id,
    symbol_name,
    signal,
    expiry_minutes,
    win_rate
):

    total_seconds = expiry_minutes * 60
    end_time = time.monotonic() + total_seconds

    while True:

        remaining = max(0, math.ceil(end_time - time.monotonic()))

        if remaining <= 0:
            break

        mins = remaining // 60

        secs = remaining % 60

        text = (
            f"⏳ Trade Running...\n\n"
            f"Pair: {symbol_name}\n"
            f"Signal: {signal}\n\n"
            f"Winning Rate: {win_rate}%\n"
            f"Time Remaining:\n"
            f"{mins:02}:{secs:02}"
        )

        try:

            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text
            )

        except:
            pass

        await asyncio.sleep(min(1, max(0, end_time - time.monotonic())))

    keyboard = [

        [
            InlineKeyboardButton(
                "✅ Profit",
                callback_data=f"profit_{signal_id}"
            ),

            InlineKeyboardButton(
                "❌ Loss",
                callback_data=f"loss_{signal_id}"
            )
        ]
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        text=
        "⏰ Trade Finished\n\n"
        "What was your result?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==========================================
# FEEDBACK
# ==========================================

async def feedback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    data = query.data

    if data.startswith("profit_"):

        signal_id = data.replace("profit_", "", 1)
        signal_record = active_signals.pop(signal_id, {})

        update_feedback(
            query.from_user.id,
            "profit",
            signal_record.get("symbol"),
            signal_record.get("signal")
        )

        await query.message.reply_text(
            "Profit Recorded\n"
            "AI Learning Updated\n"
            "This setup will get a higher winning rate in future signals."
        )

        return

    if data.startswith("loss_"):

        signal_id = data.replace("loss_", "", 1)

        keyboard = [
            [
                InlineKeyboardButton(
                    "Trend reversed",
                    callback_data=f"reason_{signal_id}_reversal"
                ),
                InlineKeyboardButton(
                    "Late entry",
                    callback_data=f"reason_{signal_id}_late"
                )
            ],
            [
                InlineKeyboardButton(
                    "Choppy market",
                    callback_data=f"reason_{signal_id}_choppy"
                ),
                InlineKeyboardButton(
                    "News spike",
                    callback_data=f"reason_{signal_id}_news"
                )
            ],
            [
                InlineKeyboardButton(
                    "Weak momentum",
                    callback_data=f"reason_{signal_id}_weak"
                )
            ]
        ]

        await query.message.reply_text(
            "Loss selected. What caused the loss?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    if data.startswith("reason_"):

        parts = data.split("_", 2)

        if len(parts) < 3:
            await query.message.reply_text("Could not record loss reason.")
            return

        signal_id = parts[1]
        reason_key = parts[2]
        reason = LOSS_REASONS.get(reason_key, reason_key)
        signal_record = active_signals.pop(signal_id, {})

        update_feedback(
            query.from_user.id,
            "loss",
            signal_record.get("symbol"),
            signal_record.get("signal"),
            reason
        )

        await query.message.reply_text(
            "Loss Recorded\n"
            f"Reason: {reason}\n"
            "AI Learning Updated\n"
            "This setup will be lowered or blocked if it keeps losing."
        )

        return
 
    if "profit_" in data:

        update_feedback(
            query.from_user.id,
            "profit"
        )

        await query.message.reply_text(
            "✅ Profit Recorded\n"
            "🧠 AI Learning Updated"
        )

    elif "loss_" in data:

        update_feedback(
            query.from_user.id,
            "loss"
        )

        await query.message.reply_text(
            "❌ Loss Recorded\n"
            "🧠 AI Learning Updated"
        )

# ==========================================
# MAIN
# ==========================================

def build_application():

    request = HTTPXRequest(
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=TELEGRAM_READ_TIMEOUT,
        write_timeout=TELEGRAM_WRITE_TIMEOUT,
        pool_timeout=TELEGRAM_POOL_TIMEOUT,
        connection_pool_size=8
    )

    get_updates_request = HTTPXRequest(
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=45.0,
        write_timeout=TELEGRAM_WRITE_TIMEOUT,
        pool_timeout=TELEGRAM_POOL_TIMEOUT,
        connection_pool_size=8
    )

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .request(request)
        .get_updates_request(get_updates_request)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CallbackQueryHandler(
            feedback_handler,
            pattern="^(profit_|loss_|reason_)"
        )
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    return app


def main():

    if not TOKEN:
        raise RuntimeError(missing_token_message())

    while True:
        asyncio.set_event_loop(asyncio.new_event_loop())

        app = build_application()

        print("🤖 Bot Running...")

        try:
            app.run_polling(
                connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
                read_timeout=TELEGRAM_READ_TIMEOUT,
                write_timeout=TELEGRAM_WRITE_TIMEOUT,
                pool_timeout=TELEGRAM_POOL_TIMEOUT
            )
            break
        except (TimedOut, NetworkError) as error:
            print(
                "Telegram connection timed out. "
                f"Retrying in {TELEGRAM_RETRY_DELAY} seconds... ({error})"
            )
            time.sleep(TELEGRAM_RETRY_DELAY)

# ==========================================

if __name__ == "__main__":
    main()
