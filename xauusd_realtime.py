#!/usr/bin/env python3
"""Realtime XAU/USD (gold) price reader using the Twelve Data API.

Usage:
    export TWELVEDATA_API_KEY="your_key_here"
    python xauusd_realtime.py            # ambil harga sekali
    python xauusd_realtime.py --watch    # update terus tiap 10 detik
    python xauusd_realtime.py --watch --interval 5

Dapatkan API key gratis di: https://twelvedata.com (Account -> API Keys)
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import json

SYMBOL = "XAU/USD"
BASE_URL = "https://api.twelvedata.com/quote"


def get_api_key() -> str:
    key = os.environ.get("TWELVEDATA_API_KEY")
    if not key:
        sys.exit(
            "ERROR: environment variable TWELVEDATA_API_KEY belum di-set.\n"
            'Jalankan: export TWELVEDATA_API_KEY="your_key_here"'
        )
    return key


def fetch_quote(api_key: str) -> dict:
    url = f"{BASE_URL}?symbol={SYMBOL.replace('/', '%2F')}&apikey={api_key}"
    try:
        with urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        sys.exit(f"HTTP error {e.code}: {e.reason}")
    except URLError as e:
        sys.exit(f"Network error: {e.reason}")

    # Twelve Data mengembalikan {"status":"error","message":...} saat gagal
    if isinstance(data, dict) and data.get("status") == "error":
        sys.exit(f"Twelve Data error: {data.get('message')}")
    return data


def print_quote(q: dict) -> None:
    price = q.get("close") or q.get("price")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    change = q.get("change", "")
    pct = q.get("percent_change", "")
    print(
        f"[{now}] XAU/USD = {price}  "
        f"(change {change}, {pct}%)  "
        f"high {q.get('high','-')} low {q.get('low','-')}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Realtime XAU/USD price (Twelve Data)")
    parser.add_argument("--watch", action="store_true", help="poll terus-menerus")
    parser.add_argument("--interval", type=int, default=10, help="detik antar update (default 10)")
    args = parser.parse_args()

    api_key = get_api_key()

    if not args.watch:
        print_quote(fetch_quote(api_key))
        return

    print(f"Watching {SYMBOL} setiap {args.interval}s (Ctrl+C untuk berhenti)...")
    try:
        while True:
            print_quote(fetch_quote(api_key))
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nBerhenti.")


if __name__ == "__main__":
    main()
