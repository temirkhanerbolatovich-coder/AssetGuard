FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend /app/backend
COPY frontend /app/frontend
RUN pip install --no-cache-dir "torch>=2.5,<3.0" --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir "/app/backend[vision]"
WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic -c alembic.ini upgrade head && python -m uvicorn assetguard.app:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
