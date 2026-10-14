
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

SYMBOLS = [
    "AMZN", "AVGO", "BE", "CAT", "CIBR", "COHR",
    "CRWD", "DRAM", "FTSM", "GLW", "GOOG", "GRID",
    "GRNY", "GS", "IONQ", "LITE", "LLY", "META",
    "MSFT", "MU", "NVDA", "PLTR", "SNDK","SPCX"
]

OUTPUT = Path("prices.json")
previous = {}

if OUTPUT.exists():
    try:
        previous = json.loads(OUTPUT.read_text()).get("holdings", {})
    except (ValueError, OSError):
        pass

holdings = {}

for symbol in SYMBOLS:
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(
            period="max",
            interval="1d",
            auto_adjust=False,
            actions=False
        )

        if history.empty:
            raise ValueError("No historical prices returned")

        history = history.dropna(subset=["High", "Close"])
        history = history[
            (history["High"] > 0) &
            (history["Close"] > 0)
        ].sort_index()

        if history.empty:
            raise ValueError("No valid daily prices")

        latest = history.iloc[-1]
        price = float(latest["Close"])

        # Calendar 52-week lookback, inclusive of current day.
        end = history.index[-1]
        start = end - pd.Timedelta(days=364)
        trailing = history[history.index >= start]

        # Daily intraday highs, not closing-price highs.
        ath = float(history["High"].max())
        high52 = float(trailing["High"].max())

        def below(high):
            return round(
                max(0.0, (high - price) / high * 100), 4
            )

        if not all(math.isfinite(x) for x in (price,ath,high52)):
            raise ValueError("Nonfinite price value")

        holdings[symbol] = {
            "price": round(price, 4),
            "ath": round(ath, 4),
            "high52": round(high52, 4),
            "belowATH": below(ath),
            "below52": below(high52),
            "priceDate": end.strftime("%Y-%m-%d")
        }
        print(symbol, "OK", holdings[symbol]["belowATH"])

    except Exception as exc:
        print(symbol, "FAILED:", str(exc))
        # Retain previous values, with their original date.
        if symbol in previous:
            holdings[symbol] = previous[symbol]

# Private SpaceX Class A shares:
# Never substitute an unrelated public ticker.
holdings["SPCX"] = {}

if not any("price" in x for x in holdings.values()):
    raise RuntimeError("No usable prices available")

result = {
    "asOf": datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    ),
    "holdings": holdings
}

OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
print("Saved", len(holdings), "holdings")
