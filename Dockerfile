# Project Samarth — Streamlit on Railway (or any container host)
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501

# Runtime libs for matplotlib / scipy wheels on slim images
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    libfreetype6 \
    libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app.py main.py requirements.txt ./
COPY src ./src

EXPOSE 8501

# Railway sets PORT at runtime; listen on all interfaces (required for public URL).
# CORS/XSRF off avoids some reverse-proxy edge cases.
CMD ["sh", "-c", "exec streamlit run app.py --server.port=\"${PORT:-8501}\" --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false --server.enableCORS=false --server.enableXsrfProtection=false"]
