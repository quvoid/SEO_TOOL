# Root Dockerfile — builds the FastAPI backend (the project migrated off Streamlit).
# Mirrors backend/Dockerfile so hosts that default to ./Dockerfile still work.
# Python 3.12+ required: analysis.py uses PEP 701 nested f-strings.
FROM python:3.12-slim

WORKDIR /app

# Install backend deps first (layer cached unless requirements change)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the whole repo so the backend can import analysis.py / connectors.py / demo_data.py
COPY . .

WORKDIR /app/backend

ENV PORT=8000
EXPOSE 8000

# Cloud Run / Railway / Render inject $PORT
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT} --timeout 120"]
