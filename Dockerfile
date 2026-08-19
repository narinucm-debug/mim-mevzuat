# MİM MEVZUAT - Production Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Sistem gereksinimleri
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları kopyala ve yükle
COPY requirements.txt requirements-dev.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn httpx

# Kaynak kodları ve testleri kopyala
COPY src/ ./src/
COPY tests/ ./tests/

# Paketi yükle
RUN pip install --no-cache-dir -e .

# Port
EXPOSE 8000

# Web sunucusunu başlat
CMD ["uvicorn", "mim_mevzuat.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
