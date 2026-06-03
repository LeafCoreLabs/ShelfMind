FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-render.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-render.txt \
    && (pip install --no-cache-dir prophet==1.1.6 cmdstanpy==1.2.5 || echo "Prophet skipped — fallback forecasts enabled")

COPY . .

RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh \
    && sed -i 's/\r$//' /app/celery-entrypoint.sh && chmod +x /app/celery-entrypoint.sh \
    && sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "-w", "1", "--timeout", "120"]
