#!/usr/bin/env python3
"""Lapisan AI untuk bot XAU/USD — menjawab pertanyaan teks bebas pakai Claude.

Mengambil data pasar XAU/USD live dari Twelve Data, menyuntikkannya sebagai
konteks, lalu meminta Claude (claude-opus-4-8) menjawab pertanyaan user dalam
bahasa natural (default: Bahasa Indonesia).

    export TWELVEDATA_API_KEY="..."
    export ANTHROPIC_API_KEY="sk-ant-..."
    python xauusd_ai.py "gold sekarang gimana, layak buy?"

Butuh: pip install anthropic
"""

import sys

try:
    import anthropic
except ImportError:  # biar bot tetap jalan walau anthropic belum diinstall
    anthropic = None

from xauusd_analyzer import get_api_key
from xauusd_signal import build_signal, fetch_signal_data

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = (
    "Kamu adalah asisten analis pasar XAU/USD (emas) yang ramah dan ringkas. "
    "Jawab dalam Bahasa Indonesia kecuali user bertanya dalam bahasa lain. "
    "Kamu DIBERI data pasar XAU/USD real-time di bawah; gunakan itu sebagai dasar "
    "jawaban — jangan mengarang angka di luar data yang diberikan. "
    "Jika user menanyakan harga/kondisi/sinyal, jawab berdasarkan data tersebut. "
    "Selalu ingatkan secara singkat bahwa ini bukan saran finansial bila user "
    "minta keputusan beli/jual. Jawab to the point, maksimal beberapa kalimat."
)


def build_context(api_key: str) -> str:
    """Rangkai data pasar live menjadi konteks teks untuk Claude."""
    data = fetch_signal_data(api_key)
    q = data["quote"]
    signal = build_signal(data)
    parts = [
        "=== DATA PASAR XAU/USD (LIVE, Twelve Data) ===",
        f"Harga (close): {q.get('close')}",
        f"Perubahan: {q.get('change')} ({q.get('percent_change')}%)",
        f"High hari ini: {q.get('high')} | Low: {q.get('low')}",
        f"Open: {q.get('open')} | Previous close: {q.get('previous_close')}",
        f"RSI 15m: {data.get('rsi')}",
        f"ADX 15m: {data.get('adx')}",
        f"ATR 15m: {data.get('atr')}",
        f"EMA20 daily: {data.get('ema20_daily')}",
        "",
        "=== SINYAL SCALP OTOMATIS ===",
        signal,
    ]
    return "\n".join(str(p) for p in parts)


def ask(question: str, td_key: str | None = None) -> str:
    """Jawab pertanyaan teks bebas user berdasarkan data XAU/USD live."""
    if anthropic is None:
        return ("(AI nonaktif: paket 'anthropic' belum terinstall. "
                "Jalankan: pip install anthropic)")

    td_key = td_key or get_api_key()

    # 1) Ambil data pasar (Twelve Data) — tangani rate limit free tier
    try:
        context = build_context(td_key)
    except RuntimeError as e:
        if "429" in str(e):
            return ("⚠️ Data pasar lagi kena rate limit Twelve Data "
                    "(free tier 8/menit). Coba lagi sebentar ya.")
        return f"⚠️ Gagal ambil data pasar: {e}"

    # 2) Tanya ke Claude — tangani error billing/rate limit dengan pesan ramah
    client = anthropic.Anthropic()  # baca ANTHROPIC_API_KEY dari environment
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"{context}\n\n=== PERTANYAAN USER ===\n{question}",
                }
            ],
        )
    except anthropic.AuthenticationError:
        return "⚠️ ANTHROPIC_API_KEY tidak valid. Cek lagi key-nya."
    except anthropic.BadRequestError as e:
        if "credit balance" in str(e).lower():
            return ("⚠️ Saldo kredit Anthropic habis. Isi dulu di "
                    "console.anthropic.com → Plans & Billing.")
        return f"⚠️ Permintaan AI ditolak: {e}"
    except anthropic.RateLimitError:
        return "⚠️ AI lagi kena rate limit. Coba lagi sebentar."
    except anthropic.APIError as e:
        return f"⚠️ Error AI: {e}"

    return "".join(b.text for b in response.content if b.type == "text").strip()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Pakai: python xauusd_ai.py "pertanyaanmu di sini"')
    print(ask(" ".join(sys.argv[1:])))
