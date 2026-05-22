# ==========================================
# FILE: strategy.py
# ==========================================

import random


def calculate_rsi(data, period=14):

    close = _close_prices(data)

    delta = close.diff()

    gain = delta.where(delta > 0, 0)

    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()

    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi


def _close_prices(data):

    close = data["Close"]

    if hasattr(close, "columns"):
        close = close.iloc[:, 0]

    return close.astype(float)


def generate_signal(data, bias=0, learning=None):

    if data.attrs.get("is_fallback"):
        return "HOLD", 0, 0

    if len(data) < 50:
        return "HOLD", 0, 0

    data = data.copy()
    data["Close"] = _close_prices(data)

    # ======================================
    # EMA
    # ======================================

    data["ema_fast"] = (
        data["Close"]
        .ewm(span=9)
        .mean()
    )

    data["ema_slow"] = (
        data["Close"]
        .ewm(span=21)
        .mean()
    )

    # ======================================
    # RSI
    # ======================================

    data["rsi"] = calculate_rsi(data)

    # ======================================
    # MACD
    # ======================================

    ema12 = data["Close"].ewm(span=12).mean()

    ema26 = data["Close"].ewm(span=26).mean()

    data["macd"] = ema12 - ema26

    data["signal_line"] = (
        data["macd"]
        .ewm(span=9)
        .mean()
    )

    # ======================================
    # CURRENT VALUES
    # ======================================

    ema_fast = data["ema_fast"].iloc[-1]

    ema_slow = data["ema_slow"].iloc[-1]

    rsi = data["rsi"].iloc[-1]

    macd = data["macd"].iloc[-1]

    signal_line = data["signal_line"].iloc[-1]

    if any(
        value != value
        for value in [ema_fast, ema_slow, rsi, macd, signal_line]
    ):
        return "HOLD", 0, 0

    # ======================================
    # CANDLE MOMENTUM
    # ======================================

    last_candle = (
        data["Close"].iloc[-1]
        -
        data["Close"].iloc[-2]
    )

    confidence = random.randint(80, 95)

    expiry = random.choice([2, 3, 5])

    # ======================================
    # BUY CONDITIONS
    # ======================================

    buy_signal = (

        ema_fast > ema_slow + bias

        and rsi > 52

        and macd > signal_line

        and last_candle > 0

    )

    # ======================================
    # SELL CONDITIONS
    # ======================================

    sell_signal = (

        ema_fast < ema_slow - bias

        and rsi < 48

        and macd < signal_line

        and last_candle < 0

    )

    # ======================================
    # FINAL SIGNAL
    # ======================================

    if buy_signal:

        signal = "BUY"

    elif sell_signal:

        signal = "SELL"

    else:

        return "HOLD", 0, 0

    if learning:

        if learning.get("block"):
            return "HOLD", 0, 0

        confidence += learning.get("confidence_adjustment", 0)
        confidence = max(50, min(98, confidence))

    return signal, expiry, confidence
