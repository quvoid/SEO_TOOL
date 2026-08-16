# Backend container for Railway / Render / Cloud Run
# Python 3.12+ required: analysis.py uses PEP 701 nested f-strings.
FROM python:3.12-slim

WORKDIR /app

# Install backend deps
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the whole repo so the backend can import analysis.py/connectors.py/demo_data.py
COPY . .

WORKDIR /app/backend

ENV PORT=8000
EXPOSE 8000

# ONE worker, deliberately: per-module report progress and the duplicate-run
# guard are in-process dicts (see routers/reports.py). A second worker would
# silently break progress polling and let a double-click fire two billable runs.
# --timeout 300 because a full report is a long background job; gunicorn's 30s
# default would reap the worker mid-run.
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 1 --timeout 300 -b 0.0.0.0:${PORT}"]
