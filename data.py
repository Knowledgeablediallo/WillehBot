# ==========================================
# FILE: data.py
# ==========================================

import contextlib
import io
import json
import random
import time
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd
import yfinance as yf

from config import get_config_value


CACHE_SECONDS = 60
_market_cache = {}


def _cache_key(symbol, market):
    return f"{market}:{symbol}"


def _remember(key, data):
    _market_cache[key] = {
        "time": time.time(),
        "data": data.copy()
    }

    return data


def _cached(key):
    cached = _market_cache.get(key)

    if cached and time.time() - cached["time"] < CACHE_SECONDS:
        return cached["data"].copy()

    return None


def _fallback_data():
    prices = []
    price = 1.1000

    for _ in range(100):
        price += random.uniform(-0.0010, 0.0010)
        prices.append(price)

    data = pd.DataFrame({
        "Close": prices
    })
    data.attrs["source"] = "fallback"
    data.attrs["is_fallback"] = True

    return data


def _clean_forex_symbol(symbol):
    symbol = symbol.replace("OTC_", "").replace("=X", "").replace("-", "/")

    if "/" in symbol:
        left, right = symbol.split("/", 1)
        return left.upper(), right.upper()

    if len(symbol) == 6:
        return symbol[:3].upper(), symbol[3:].upper()

    if len(symbol) == 3:
        return "USD", symbol.upper()

    return "EUR", "USD"


def _to_yfinance_forex_symbol(symbol):
    base, quote = _clean_forex_symbol(symbol)
    return f"{base}{quote}=X"


def _to_binance_symbol(symbol):
    symbol = symbol.upper().replace("-", "").replace("/", "")

    if symbol.endswith("USD"):
        symbol = f"{symbol[:-3]}USDT"

    if not symbol.endswith("USDT"):
        symbol = f"{symbol}USDT"

    return symbol


def _standard_close_frame(values):
    if isinstance(values, pd.DataFrame) and "Close" in values.columns:
        return values

    return pd.DataFrame({
        "Close": values
    })


def _mark_source(data, source):
    data = data.copy()
    data.attrs["source"] = source
    data.attrs["is_fallback"] = False

    return data


def _download_yfinance(symbol):
    buffer = io.StringIO()

    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        data = yf.download(
            symbol,
            period="1d",
            interval="1m",
            progress=False,
            threads=False
        )

    if data.empty:
        raise RuntimeError("No market data returned")

    return _mark_source(data, "yfinance")


def get_binance_data(symbol):
    binance_symbol = _to_binance_symbol(symbol)
    params = urlencode({
        "symbol": binance_symbol,
        "interval": "1m",
        "limit": 100
    })
    url = f"https://api.binance.com/api/v3/klines?{params}"

    with urlopen(url, timeout=10) as response:
        candles = json.loads(response.read().decode("utf-8"))

    closes = [float(candle[4]) for candle in candles]
    return _mark_source(_standard_close_frame(closes), "binance")


def get_forex_data(symbol):
    base, quote = _clean_forex_symbol(symbol)
    pair = f"{base}/{quote}"

    try:
        api_key = get_config_value("TWELVEDATA_API_KEY")

        if api_key:
            from twelvedata import TDClient

            td = TDClient(apikey=api_key)
            data = td.time_series(
                symbol=pair,
                interval="1min",
                outputsize=100
            ).as_pandas()

            return _mark_source(
                _standard_close_frame(data["close"].astype(float)),
                "twelvedata"
            )
    except Exception:
        pass

    try:
        api_key = get_config_value("ALPHA_VANTAGE_API_KEY")

        if api_key:
            from alpha_vantage.foreignexchange import ForeignExchange

            fx = ForeignExchange(key=api_key)
            data, _meta = fx.get_currency_exchange_daily(
                from_symbol=base,
                to_symbol=quote
            )
            closes = [
                float(values["4. close"])
                for values in data.values()
            ]

            return _mark_source(
                _standard_close_frame(list(reversed(closes[-100:]))),
                "alpha_vantage"
            )
    except Exception:
        pass

    return _download_yfinance(_to_yfinance_forex_symbol(symbol))


def get_stock_data(symbol):
    try:
        return _download_yfinance(symbol)
    except Exception:
        pass

    try:
        api_key = get_config_value("FINNHUB_API_KEY")

        if api_key:
            import finnhub

            client = finnhub.Client(api_key=api_key)
            quote = client.quote(symbol)
            price = quote.get("c")

            if price:
                return _mark_source(
                    _standard_close_frame([float(price)] * 100),
                    "finnhub"
                )
    except Exception:
        pass

    raise RuntimeError("No stock data returned")


def get_market_data(symbol, market="auto"):
    key = _cache_key(symbol, market)
    cached = _cached(key)

    if cached is not None:
        return cached

    try:
        if market == "crypto" or (market == "auto" and "BTC" in symbol.upper()):
            return _remember(key, get_binance_data(symbol))

        if market == "forex" or (
            market == "auto"
            and ("/" in symbol or symbol.endswith("=X") or len(symbol.replace("OTC_", "")) == 6)
        ):
            return _remember(key, get_forex_data(symbol))

        return _remember(key, get_stock_data(symbol))

    except Exception:
        return _remember(key, _fallback_data())
