FROM python:3.12-slim
ARG ASSETGUARD_INSTALL_VISION=1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend /app/backend
COPY frontend /app/frontend
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core tesseract-ocr tesseract-ocr-rus tesseract-ocr-kaz tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir /app/backend \
    && if [ "$ASSETGUARD_INSTALL_VISION" = "1" ]; then \
         pip install --no-cache-dir "torch>=2.5,<3.0" --index-url https://download.pytorch.org/whl/cpu \
         && pip install --no-cache-dir "/app/backend[vision]"; \
       fi
WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic -c alembic.ini upgrade head && python -m uvicorn assetguard.app:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
