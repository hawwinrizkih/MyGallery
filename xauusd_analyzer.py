#!/usr/bin/env python3
"""XAU/USD market analyzer using the Twelve Data API.

Mengambil quote + indikator teknikal (RSI multi-timeframe, MACD, EMA)
lalu menghasilkan ringkasan analisa market emas (XAU/USD).

Dipakai sebagai library oleh telegram_xauusd_bot.py, atau langsung:

    export TWELVEDATA_API_KEY="your_key"
    python xauusd_analyzer.py            # cetak analisa ke terminal
"""

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

SYMBOL = "XAU/USD"
API_BASE = "https://api.twelvedata.com"


def _get(endpoint: str, api_key: str, **params) -> dict:
    params.update({"symbol": SYMBOL, "apikey": api_key})
    url = f"{API_BASE}/{endpoint}?{urlencode(params)}"
    try:
        with urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} dari Twelve Data ({endpoint}): {e.reason}")
    except URLError as e:
        raise RuntimeError(f"Network error ({endpoint}): {e.reason}")
    if isinstance(data, dict) and data.get("status") == "error":
        raise RuntimeError(f"Twelve Data error ({endpoint}): {data.get('message')}")
    return data


def _last_value(data: dict, field: str):
    try:
        return float(data["values"][0][field])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def fetch_market(api_key: str) -> dict:
    """Ambil semua data yang dibutuhkan untuk analisa (5 credit Twelve Data)."""
    quote = _get("quote", api_key)
    rsi_5m = _last_value(_get("rsi", api_key, interval="5min", outputsize=1), "rsi")
    rsi_1h = _last_value(_get("rsi", api_key, interval="1h", outputsize=1), "rsi")
    macd = _get("macd", api_key, interval="15min", outputsize=1)
    ema50 = _last_value(
        _get("ema", api_key, interval="15min", time_period=50, outputsize=1), "ema"
    )
    return {
        "quote": quote,
        "rsi_5m": rsi_5m,
        "rsi_1h": rsi_1h,
        "macd": _last_value(macd, "macd"),
        "macd_signal": _last_value(macd, "macd_signal"),
        "macd_hist": _last_value(macd, "macd_hist"),
        "ema50_15m": ema50,
    }


def _rsi_label(rsi):
    if rsi is None:
        return "n/a"
    if rsi >= 70:
        return "overbought 🔴"
    if rsi <= 30:
        return "oversold 🟢"
    if rsi <= 40:
        return "mendekati oversold 🟢"
    if rsi >= 60:
        return "mendekati overbought 🔴"
    return "netral ⚪"


def analyze(m: dict) -> str:
    """Bangun pesan analisa (Markdown-friendly) dari data market."""
    q = m["quote"]
    price = float(q.get("close", 0))
    pct = float(q.get("percent_change", 0))
    change = float(q.get("change", 0))
    ema = m["ema50_15m"]
    hist = m["macd_hist"]
    macd, signal = m["macd"], m["macd_signal"]

    # Skor bias: gabungan beberapa sinyal sederhana
    score = 0
    reasons = []
    if pct < 0:
        score -= 1
        reasons.append("perubahan harian negatif")
    else:
        score += 1
        reasons.append("perubahan harian positif")

    if ema is not None:
        if price < ema:
            score -= 1
            reasons.append("harga di bawah EMA50 (tren pendek turun)")
        else:
            score += 1
            reasons.append("harga di atas EMA50 (tren pendek naik)")

    if hist is not None:
        if hist > 0:
            score += 1
            reasons.append("MACD histogram positif (momentum naik)")
        else:
            score -= 1
            reasons.append("MACD histogram negatif (momentum turun)")

    if m["rsi_1h"] is not None:
        if m["rsi_1h"] <= 30:
            score += 1
            reasons.append("RSI 1h oversold (potensi pantulan)")
        elif m["rsi_1h"] >= 70:
            score -= 1
            reasons.append("RSI 1h overbought (potensi koreksi)")

    if score >= 2:
        bias = "🟢 BULLISH"
    elif score <= -2:
        bias = "🔴 BEARISH"
    else:
        bias = "⚪ NETRAL / MIXED"

    arrow = "🔴" if pct < 0 else "🟢"
    high = q.get("high", "-")
    low = q.get("low", "-")

    lines = [
        "*📊 Analisa XAU/USD (Gold)*",
        f"Harga: *${price:,.2f}*  {arrow} {pct:+.2f}% ({change:+.2f})",
        f"High {high} · Low {low}",
        "",
        f"RSI 5m: {fmt(m['rsi_5m'])} ({_rsi_label(m['rsi_5m'])})",
        f"RSI 1h: {fmt(m['rsi_1h'])} ({_rsi_label(m['rsi_1h'])})",
        f"MACD 15m: {fmt(macd)} / signal {fmt(signal)} / hist {fmt(hist)}",
        f"EMA50 15m: {fmt(ema)}",
        "",
        f"*Bias: {bias}*",
        "Alasan: " + "; ".join(reasons) + ".",
        "",
        "_⚠️ Bukan saran finansial. Pembacaan teknikal otomatis (Twelve Data)._",
    ]
    return "\n".join(lines)


def fmt(v):
    return f"{v:,.2f}" if isinstance(v, (int, float)) else "n/a"


def get_api_key() -> str:
    key = os.environ.get("TWELVEDATA_API_KEY")
    if not key:
        sys.exit('ERROR: set dulu TWELVEDATA_API_KEY (export TWELVEDATA_API_KEY="...")')
    return key


if __name__ == "__main__":
    market = fetch_market(get_api_key())
    print(analyze(market))
