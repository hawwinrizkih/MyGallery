# XAU/USD Realtime & Analyzer (Twelve Data)

Tool untuk membaca harga emas (XAU/USD) realtime + analisa teknikal otomatis,
dengan opsi kirim ke bot Telegram tiap 5 menit.

## File
| File | Fungsi |
|------|--------|
| `xauusd_realtime.py` | Baca harga XAU/USD realtime (single-shot / `--watch`) |
| `xauusd_analyzer.py` | Ambil quote + RSI/MACD/EMA, hasilkan analisa bias market |
| `xauusd_signal.py` | **Scalp signal** actionable: arah, grade, entry/SL/TP, konfluens, failed-breakout |
| `xauusd_ai.py` | **AI (Claude)**: jawab pertanyaan teks bebas pakai data XAU/USD live |
| `telegram_signal_bot.py` | Bot on-demand: `/signal`, `/price`, **+ tanya bebas dijawab AI** |
| `telegram_xauusd_bot.py` | Kirim scalp signal ke Telegram (single / `--loop` tiap 5 menit) |

## AI (tanya bebas)
Bot bisa menjawab pertanyaan bahasa natural (mis. _"gold sekarang gimana, layak buy?"_)
memakai **Claude (`claude-opus-4-8`)** + data XAU/USD live. Perlu API key Anthropic:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
pip install -r requirements.txt
python telegram_signal_bot.py     # /signal, /price, dan tanya bebas (AI)
python xauusd_ai.py "gold layak buy gak sekarang?"   # tes CLI
```

## Setup
```bash
export TWELVEDATA_API_KEY="your_twelvedata_key"
# untuk bot Telegram:
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
export TELEGRAM_CHAT_ID="123456789"
```

## Pakai
```bash
python xauusd_realtime.py --watch            # harga live tiap 10 detik
python xauusd_analyzer.py                     # cetak analisa ke terminal
python telegram_xauusd_bot.py                 # kirim 1x ke Telegram (tes)
python telegram_xauusd_bot.py --loop          # kirim analisa tiap 5 menit
python telegram_xauusd_bot.py --loop --interval 900   # tiap 15 menit
```

## Cara dapat `chat_id`
1. Buat bot lewat **@BotFather** → dapat **bot token**.
2. Kirim pesan apa saja ke bot kamu.
3. Buka `https://api.telegram.org/bot<TOKEN>/getUpdates`, cari `"chat":{"id": ...}`.

## ⚠️ Rate limit
Twelve Data free tier = **8 credit/menit, 800 credit/hari**. Tiap analisa
memakai ~5 credit. Loop 5-menit ≈ 1.440 credit/hari → **melebihi kuota free**.
Untuk jalan 24/7 pakai interval lebih besar (10–15 menit) atau plan berbayar.

Hanya butuh Python 3 (standard library, tanpa `pip install`).
