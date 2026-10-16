FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 BOT_DATA_DIR=/data
COPY bot.py /app/bot.py
CMD ["python", "-u", "/app/bot.py"]
