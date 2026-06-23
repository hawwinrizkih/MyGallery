#!/usr/bin/env python3
"""Generator SCALP SIGNAL XAU/USD (Twelve Data).

Menghasilkan sinyal actionable bergaya scalping: arah (BUY/SELL), grade,
entry area, SL, TP1/TP2, plus konfluens (daily bias, struktur 15m,
failed-breakout, RSI, ADX). SL/TP dihitung dari ATR + struktur swing.

    export TWELVEDATA_API_KEY="your_key"
    python xauusd_signal.py

⚠️ Analisa teknikal otomatis, BUKAN saran finansial.
"""

import sys

from xauusd_analyzer import _get, _last_value, get_api_key

LOOKBACK = 12          # jumlah bar 15m untuk struktur swing
ATR_SL = 0.6           # buffer SL di atas/bawah swing (x ATR)
ATR_TP1 = 1.5          # jarak TP1 (x ATR)
ATR_TP2 = 3.0          # jarak TP2 (x ATR)


def fetch_signal_data(api_key: str) -> dict:
    """~6 credit Twelve Data."""
    quote = _get("quote", api_key)
    ts = _get("time_series", api_key, interval="15min", outputsize=LOOKBACK + 1)
    rsi = _last_value(_get("rsi", api_key, interval="15min", outputsize=1), "rsi")
    adx = _last_value(_get("adx", api_key, interval="15min", outputsize=1), "adx")
    atr = _last_value(_get("atr", api_key, interval="15min", outputsize=1), "atr")
    ema_d = _last_value(
        _get("ema", api_key, interval="1day", time_period=20, outputsize=1), "ema"
    )
    bars = ts.get("values", [])
    return {"quote": quote, "bars": bars, "rsi": rsi, "adx": adx,
            "atr": atr, "ema20_daily": ema_d}


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def build_signal(d: dict) -> str:
    q = d["quote"]
    price = _f(q.get("close"))
    bars = d["bars"]
    atr = d["atr"] or 1.0
    rsi = d["rsi"]
    adx = d["adx"]
    ema_d = d["ema20_daily"]

    if not bars or price is None:
        return "⚠️ Data tidak lengkap dari Twelve Data, coba lagi."

    # bars[0] = bar terbaru (mungkin masih terbentuk); pakai bar[1..] utk struktur
    closed = bars[1:LOOKBACK + 1] if len(bars) > 1 else bars
    highs = [_f(b["high"]) for b in closed]
    lows = [_f(b["low"]) for b in closed]
    swing_high = max(highs)
    swing_low = min(lows)
    last = bars[0]
    last_close = _f(last["close"])
    last_high = _f(last["high"])
    last_low = _f(last["low"])

    # --- Daily bias ---
    if ema_d and price < ema_d:
        daily = "BEARISH"
    elif ema_d and price > ema_d:
        daily = "BULLISH"
    else:
        daily = "NETRAL"

    # --- Deteksi failed breakout / breakdown pada bar terakhir ---
    failed_up = last_high > swing_high and last_close < swing_high   # bull trap
    failed_down = last_low < swing_low and last_close > swing_low     # bear trap

    # --- Tentukan arah & kumpulkan konfluens (per-arah) ---
    sell_conf, buy_conf = [], []
    sell_score = buy_score = 0

    if daily == "BEARISH":
        sell_score += 1
        sell_conf.append(f"Daily BEARISH (harga di bawah EMA20 {ema_d:.0f})")
    elif daily == "BULLISH":
        buy_score += 1
        buy_conf.append(f"Daily BULLISH (harga di atas EMA20 {ema_d:.0f})")

    if rsi is not None:
        if rsi < 50:
            sell_score += 1
            sell_conf.append(f"RSI {rsi:.0f} <50")
        else:
            buy_score += 1
            buy_conf.append(f"RSI {rsi:.0f} >50")

    if adx is not None and adx >= 25:
        # tren kuat: perkuat arah daily
        if daily == "BEARISH":
            sell_score += 1
            sell_conf.append(f"ADX {adx:.0f} (tren kuat)")
        elif daily == "BULLISH":
            buy_score += 1
            buy_conf.append(f"ADX {adx:.0f} (tren kuat)")

    if failed_up:
        sell_score += 2
        sell_conf.append(f"failed breakout {swing_high:.0f} (bull trap)")
    if failed_down:
        buy_score += 2
        buy_conf.append(f"failed breakdown {swing_low:.0f} (bear trap)")

    # breakdown/breakout struktur murni
    if not failed_up and not failed_down:
        if price < swing_low:
            sell_score += 1
            sell_conf.append(f"breakdown support {swing_low:.0f}")
        elif price > swing_high:
            buy_score += 1
            buy_conf.append(f"breakout resist {swing_high:.0f}")

    direction = "SELL" if sell_score >= buy_score else "BUY"
    score = sell_score if direction == "SELL" else buy_score
    conf = sell_conf if direction == "SELL" else buy_conf
    if not conf:
        conf = ["sinyal lemah / tidak ada konfluens jelas"]

    aligned = (direction == "SELL" and daily == "BEARISH") or \
              (direction == "BUY" and daily == "BULLISH")

    # --- Grade ---
    if score >= 5:
        grade = "A"
    elif score >= 4:
        grade = "B"
    else:
        grade = "C"
    if not aligned and grade == "A":
        grade = "B"  # counter-trend tak boleh Grade A

    # --- Entry / SL / TP berbasis ATR + struktur ---
    if direction == "SELL":
        emoji = "🔴"
        entry_lo = round(price - 0.3 * atr)
        entry_hi = round(price + 0.5 * atr)
        sl = round(swing_high + ATR_SL * atr)
        tp1 = round(price - ATR_TP1 * atr)
        tp2 = round(price - ATR_TP2 * atr)
    else:
        emoji = "🟢"
        entry_lo = round(price - 0.5 * atr)
        entry_hi = round(price + 0.3 * atr)
        sl = round(swing_low - ATR_SL * atr)
        tp1 = round(price + ATR_TP1 * atr)
        tp2 = round(price + ATR_TP2 * atr)

    setup = ""
    if direction == "SELL" and failed_up:
        setup = " (failed breakout)"
    elif direction == "BUY" and failed_down:
        setup = " (failed breakdown)"
    elif aligned:
        setup = " (continuation)"

    rsi_dir = "turun" if (rsi is not None and rsi < 50) else "naik"
    align_txt = (f"searah Daily {daily}" if aligned
                 else f"LAWAN tren Daily {daily} (hati-hati)")
    warn = ("⚠️ SELL searah tren utama." if (direction == "SELL" and aligned)
            else "⚠️ BUY searah tren utama." if (direction == "BUY" and aligned)
            else "⚠️ Counter-trend — risiko lebih tinggi, perketat risk.")

    lines = [
        f"[SCALP] {emoji} GOLD — {direction} · Grade {grade}{setup}",
        f"Entry area: {entry_lo}–{entry_hi} (harga skrg {price:.0f})",
        f"SL {sl} · TP1 {tp1} · TP2 {tp2}",
        f"📊 RSI ~{rsi:.0f} {rsi_dir} · ADX ~{adx:.0f}" if rsi is not None and adx is not None
            else "📊 indikator parsial",
        f"Bias: {align_txt} | Konfluens: " + " + ".join(conf),
        warn,
        "⚠️ analisa teknikal, bukan saran finansial",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        print(build_signal(fetch_signal_data(get_api_key())))
    except Exception as e:
        sys.exit(f"ERROR: {e}")
