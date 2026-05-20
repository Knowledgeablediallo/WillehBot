# ==========================================
# FILE: strategy.py
# ==========================================

import random


def _close_prices(data):
    close = data["Close"]

    if hasattr(close, "columns"):
        close = close.iloc[:, 0]

    return close.astype(float)


def generate_signal(data, bias=0, learning=None):

    if data.attrs.get("is_fallback"):
        return "HOLD", 0, 0

    if len(data) < 20:

        return "HOLD", 0, 0

    data = data.copy()
    data["Close"] = _close_prices(data)

    data["fast_ma"] = (
        data["Close"]
        .rolling(5)
        .mean()
    )

    data["slow_ma"] = (
        data["Close"]
        .rolling(20)
        .mean()
    )

    fast = data["fast_ma"].iloc[-1]

    slow = data["slow_ma"].iloc[-1]

    if data["fast_ma"].isna().iloc[-1] or data["slow_ma"].isna().iloc[-1]:
        return "HOLD", 0, 0

    confidence = random.randint(72, 92)

    expiry = random.choice([1, 2, 3, 5])

    if fast > slow + bias:

        signal = "BUY"

    elif fast < slow - bias:

        signal = "SELL"

    else:
        return "HOLD", 0, 0

    if learning:
        if learning.get("block"):
            return "HOLD", 0, 0

        confidence += learning.get("confidence_adjustment", 0)
        confidence = max(50, min(98, confidence))

    return signal, expiry, confidence
