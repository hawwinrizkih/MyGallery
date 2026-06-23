#!/usr/bin/env python3
"""Lapisan AI untuk bot XAU/USD — menjawab pertanyaan teks bebas.

Mengambil data pasar XAU/USD live dari Twelve Data, menyuntikkannya sebagai
konteks, lalu meminta AI menjawab pertanyaan user dalam bahasa natural
(default: Bahasa Indonesia).

Provider AI dipilih otomatis dari environment variable:
  - GEMINI_API_KEY     -> Google Gemini (AI Studio) — punya FREE TIER
  - ANTHROPIC_API_KEY  -> Claude (berbayar per token)
Kalau keduanya ada, GEMINI dipakai duluan. Atur paksa via AI_PROVIDER=gemini|claude.

    export TWELVEDATA_API_KEY="..."
    export GEMINI_API_KEY="AIza..."          # gratis dari aistudio.google.com
    python xauusd_ai.py "gold sekarang gimana, layak buy?"

Gemini tidak butuh dependency tambahan (pakai REST). Claude butuh: pip install anthropic
"""

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import anthropic
except ImportError:  # biar bot tetap jalan walau anthropic belum diinstall
    anthropic = None

from xauusd_analyzer import get_api_key
from xauusd_signal import build_signal, fetch_signal_data

CLAUDE_MODEL = "claude-opus-4-8"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

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
    """Rangkai data pasar live menjadi konteks teks untuk AI."""
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


def _choose_provider() -> str:
    forced = os.environ.get("AI_PROVIDER", "").lower()
    if forced in ("gemini", "claude"):
        return forced
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    return "none"


def _ask_gemini(prompt: str) -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return "⚠️ GEMINI_API_KEY belum di-set."
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={key}"
    )
    body = json.dumps({
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.4},
    }).encode()
    req = Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        if e.code in (401, 403):
            return "⚠️ GEMINI_API_KEY tidak valid / ditolak. Cek lagi key-nya."
        if e.code == 429:
            return "⚠️ Gemini kena rate limit (free tier). Coba lagi sebentar."
        return f"⚠️ Gemini HTTP {e.code}: {detail[:200]}"
    except URLError as e:
        return f"⚠️ Gemini network error: {e.reason}"

    candidates = data.get("candidates", [])
    if not candidates:
        fb = data.get("promptFeedback", {})
        return f"⚠️ Gemini tidak memberi jawaban (mungkin difilter): {fb}"
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    return text or "⚠️ Gemini mengembalikan jawaban kosong."


def _ask_claude(prompt: str) -> str:
    if anthropic is None:
        return ("(Claude nonaktif: paket 'anthropic' belum terinstall. "
                "Jalankan: pip install anthropic)")
    client = anthropic.Anthropic()  # baca ANTHROPIC_API_KEY dari environment
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
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


def ask(question: str, td_key: str | None = None) -> str:
    """Jawab pertanyaan teks bebas user berdasarkan data XAU/USD live."""
    provider = _choose_provider()
    if provider == "none":
        return ("(AI nonaktif: set GEMINI_API_KEY (gratis) atau ANTHROPIC_API_KEY "
                "untuk mengaktifkan fitur tanya bebas.)")

    td_key = td_key or get_api_key()
    try:
        context = build_context(td_key)
    except RuntimeError as e:
        if "429" in str(e):
            return ("⚠️ Data pasar lagi kena rate limit Twelve Data "
                    "(free tier 8/menit). Coba lagi sebentar ya.")
        return f"⚠️ Gagal ambil data pasar: {e}"

    prompt = f"{context}\n\n=== PERTANYAAN USER ===\n{question}"
    if provider == "gemini":
        return _ask_gemini(prompt)
    return _ask_claude(prompt)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Pakai: python xauusd_ai.py "pertanyaanmu di sini"')
    print(f"[provider: {_choose_provider()}]")
    print(ask(" ".join(sys.argv[1:])))
