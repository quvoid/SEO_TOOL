# ── Build ────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# ── Runtime ──────────────────────────────────────────────────────────────────
# Cloud Run injects PORT env var (default 8080)
ENV PORT=8080

EXPOSE 8080

# Streamlit needs headless mode; address 0.0.0.0 so Cloud Run can reach it
CMD ["python", "-m", "streamlit", "run", "app.py", \
     "--server.port=8080", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=true"]
