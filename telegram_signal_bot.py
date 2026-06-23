#!/usr/bin/env python3
"""Bot Telegram on-demand: balas analisa XAU/USD saat user ketik /signal.

Bot ini memakai long-polling (getUpdates), jadi tidak butuh webhook/server
publik. Setiap perintah memicu pengambilan data LIVE dari Twelve Data.

Perintah yang didukung:
    /start  -> info singkat
    /signal -> kirim analisa XAU/USD terbaru
    /price  -> kirim harga XAU/USD saja (cepat)

Setup:
    export TWELVEDATA_API_KEY="your_twelvedata_key"
    export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."

Jalankan:
    python telegram_signal_bot.py
"""

import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen, Request

from xauusd_analyzer import fetch_market, get_api_key
from xauusd_signal import build_signal, fetch_signal_data
from xauusd_ai import ask

API_BASE = "https://api.telegram.org"


def tg_api(token: str, method: str, **params):
    url = f"{API_BASE}/bot{token}/{method}"
    data = urlencode(params).encode() if params else None
    req = Request(url, data=data)
    try:
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"Telegram HTTP {e.code} ({method}): {body}")
    except URLError as e:
        raise RuntimeError(f"Telegram network error ({method}): {e.reason}")


def send(token: str, chat_id, text: str, markdown: bool = True):
    params = dict(chat_id=chat_id, text=text)
    if markdown:
        params["parse_mode"] = "Markdown"
    tg_api(token, "sendMessage", **params)


HELP = (
    "*XAUUSD Signal Bot* 🪙\n"
    "Perintah:\n"
    "/signal — analisa teknikal XAU/USD terbaru\n"
    "/price — harga XAU/USD saat ini\n"
    "Atau ketik pertanyaan bebas (mis. _gold sekarang gimana, layak buy?_) "
    "dan AI akan menjawab pakai data live.\n"
    "Data: Twelve Data + Claude AI. ⚠️ Bukan saran finansial."
)


def handle_command(token: str, api_key: str, chat_id, text: str):
    cmd = text.strip().split()[0].lower().split("@")[0]
    if cmd in ("/start", "/help"):
        send(token, chat_id, HELP)
    elif cmd == "/signal":
        send(token, chat_id, "⏳ Mengambil data XAU/USD...")
        send(token, chat_id, build_signal(fetch_signal_data(api_key)), markdown=False)
    elif cmd == "/price":
        m = fetch_market(api_key)
        q = m["quote"]
        price = float(q.get("close", 0))
        pct = float(q.get("percent_change", 0))
        arrow = "🔴" if pct < 0 else "🟢"
        send(token, chat_id, f"*XAU/USD*: ${price:,.2f}  {arrow} {pct:+.2f}%")
    else:
        send(token, chat_id, "Perintah tidak dikenal. Coba /signal atau /price.")


def main():
    api_key = get_api_key()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("ERROR: set TELEGRAM_BOT_TOKEN dulu.")

    print("Bot aktif (long-polling). Ketik /signal di Telegram. Ctrl+C berhenti.")
    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            resp = tg_api(token, "getUpdates", **params)
            for upd in resp.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("channel_post")
                if not msg:
                    continue
                text = msg.get("text", "")
                chat_id = msg["chat"]["id"]
                if not text:
                    continue
                if text.startswith("/"):
                    try:
                        handle_command(token, api_key, chat_id, text)
                    except Exception as e:
                        send(token, chat_id, f"⚠️ Error ambil data: {e}")
                else:
                    # teks bebas -> dijawab AI (Claude) pakai data live
                    try:
                        tg_api(token, "sendChatAction", chat_id=chat_id, action="typing")
                        send(token, chat_id, ask(text, api_key), markdown=False)
                    except Exception as e:
                        send(token, chat_id, f"⚠️ Error AI: {e}")
        except Exception as e:
            print("WARN:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
