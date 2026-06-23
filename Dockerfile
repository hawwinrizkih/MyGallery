# Bot Telegram XAU/USD (mode /signal + tanya bebas AI) — long-polling 24/7
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bot interaktif: /signal, /price, dan tanya bebas (AI)
CMD ["python", "telegram_signal_bot.py"]
