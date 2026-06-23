# Deploy Bot XAU/USD 24/7

Bot `telegram_signal_bot.py` (perintah `/signal`, `/price`, + tanya bebas AI)
butuh proses yang **nyala terus** (long-polling). Berikut cara deploy-nya.

## Secret yang dibutuhkan (semua platform)
| Nama | Wajib | Untuk |
|------|-------|-------|
| `TWELVEDATA_API_KEY` | ✅ | data pasar + sinyal |
| `TELEGRAM_BOT_TOKEN` | ✅ | bot Telegram |
| `GEMINI_API_KEY` | opsional | fitur tanya-bebas AI — **GRATIS** (aistudio.google.com) |
| `ANTHROPIC_API_KEY` | opsional | alternatif AI (Claude, berbayar per token) |

> Untuk tanya-bebas AI, cukup salah satu: **`GEMINI_API_KEY`** (gratis, disarankan)
> atau `ANTHROPIC_API_KEY`. Kalau dua-duanya diisi, Gemini dipakai duluan
> (atur paksa via `AI_PROVIDER=gemini|claude`). Model Gemini bisa diganti via
> `GEMINI_MODEL` (default `gemini-2.0-flash`).

> `TELEGRAM_CHAT_ID` TIDAK diperlukan untuk bot ini (dia balas ke siapa pun
> yang chat). Itu hanya untuk mode auto-push (`telegram_xauusd_bot.py`).

---

## Opsi A — Fly.io (paling murah / ada alokasi gratis) ⭐
1. Install CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Dari folder repo, buat app (sekali saja): `fly launch --no-deploy --copy-config`
   (pakai `fly.toml` yang sudah ada; ganti nama app kalau bentrok)
4. Set secrets:
   ```bash
   fly secrets set TWELVEDATA_API_KEY=xxx TELEGRAM_BOT_TOKEN=xxx ANTHROPIC_API_KEY=xxx
   ```
5. Deploy: `fly deploy`
6. Lihat log: `fly logs`

## Opsi B — Railway (paling gampang, ada trial $5/bln)
1. Buka railway.app → New Project → Deploy from GitHub repo → pilih `MyGallery`.
2. Railway auto-detect `Procfile` (worker).
3. Tab **Variables** → tambah `TWELVEDATA_API_KEY`, `TELEGRAM_BOT_TOKEN`,
   `ANTHROPIC_API_KEY`.
4. Deploy otomatis. Cek tab **Deployments → Logs**.

## Opsi C — Render (worker berbayar ~$7/bln)
1. Buka render.com → New → **Blueprint** → connect repo `MyGallery`
   (otomatis baca `render.yaml`).
2. Isi env vars saat diminta (3 secret di atas).
3. Deploy. Cek **Logs**.

---

## Verifikasi
Setelah deploy & log menunjukkan `Bot aktif (long-polling)`, kirim `/signal`
ke bot di Telegram — harus langsung dibalas.

## Catatan biaya
- **Twelve Data**: free 800 credit/hari (cukup untuk pemakaian wajar).
- **Anthropic**: tanya-bebas AI perlu kredit API (langganan Claude Max TIDAK
  termasuk API). Tanpa kredit, `/signal` & `/price` tetap jalan; hanya
  tanya-bebas yang nonaktif.
- **Hosting**: Fly.io paling hemat untuk worker always-on; Railway termudah.
