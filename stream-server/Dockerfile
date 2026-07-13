# Shah-Stream sync server — production image (single-file FastAPI WebSocket relay).
FROM python:3.12-slim

# Run as an unprivileged user, never root.
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

# Install dependencies first so this layer caches across server.py edits.
COPY requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt

# Copy the single-file server.
COPY server.py ./

USER appuser

# Fixed port, matching the server and the client default.
EXPOSE 8765

# Liveness probe against the built-in /health endpoint (no curl needed in slim).
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=3).status == 200 else 1)"

# Single process/worker: room state is in-memory. Bind all interfaces on the fixed port.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8765", "--no-access-log"]
