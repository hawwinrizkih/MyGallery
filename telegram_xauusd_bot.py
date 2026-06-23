#!/usr/bin/env python3
"""Bot Telegram yang mengirim analisa XAU/USD setiap 5 menit.

Setup (sekali saja):
    1. Buat bot via @BotFather di Telegram -> dapat BOT TOKEN.
    2. Chat dulu ke bot kamu, lalu ambil chat_id (lihat catatan di bawah).
    3. Set environment variables:
         export TWELVEDATA_API_KEY="your_twelvedata_key"
         export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
         export TELEGRAM_CHAT_ID="123456789"

Jalankan:
    python telegram_xauusd_bot.py            # kirim sekali (tes)
    python telegram_xauusd_bot.py --loop     # kirim tiap 5 menit
    python telegram_xauusd_bot.py --loop --interval 300

Cara dapat chat_id: kirim pesan apa saja ke bot kamu, lalu buka
    https://api.telegram.org/bot<TOKEN>/getUpdates
dan lihat "chat":{"id": ...}.

Catatan rate limit Twelve Data (free tier = 8 credit/menit, 800/hari):
  Tiap kirim memakai ~5 credit. Loop 5-menit = ~1440 credit/hari,
  melebihi kuota free 800/hari. Untuk 24/7 gunakan interval lebih besar
  (mis. 10-15 menit) atau plan berbayar.
"""

import argparse
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen, Request

from xauusd_analyzer import get_api_key
from xauusd_signal import build_signal, fetch_signal_data


def send_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urlencode({"chat_id": chat_id, "text": text}).encode()
    req = Request(url, data=payload)
    try:
        with urlopen(req, timeout=20) as resp:
            resp.read()
    except HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"Telegram HTTP {e.code}: {body}")
    except URLError as e:
        raise RuntimeError(f"Telegram network error: {e.reason}")


def require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        sys.exit(f"ERROR: environment variable {name} belum di-set.")
    return val


def run_once(api_key: str, token: str, chat_id: str) -> None:
    message = build_signal(fetch_signal_data(api_key))
    send_telegram(token, chat_id, message)
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), "Terkirim ke Telegram.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot Telegram analisa XAU/USD")
    parser.add_argument("--loop", action="store_true", help="kirim berulang")
    parser.add_argument("--interval", type=int, default=300, help="detik antar kirim (default 300 = 5 menit)")
    args = parser.parse_args()

    api_key = get_api_key()
    token = require_env("TELEGRAM_BOT_TOKEN")
    chat_id = require_env("TELEGRAM_CHAT_ID")

    if not args.loop:
        run_once(api_key, token, chat_id)
        return

    print(f"Bot aktif: kirim analisa XAU/USD tiap {args.interval}s (Ctrl+C berhenti).")
    while True:
        try:
            run_once(api_key, token, chat_id)
        except Exception as e:  # jangan mati gara-gara 1 error sementara
            print("WARN:", e)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
