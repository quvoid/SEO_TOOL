# Backend container for Railway / Render / Cloud Run
FROM python:3.11-slim

WORKDIR /app

# Install backend deps
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the whole repo so the backend can import analysis.py/connectors.py/demo_data.py
COPY . .

WORKDIR /app/backend

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT}"]
