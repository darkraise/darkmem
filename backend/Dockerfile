FROM python:3.12-slim AS base

WORKDIR /app

# Install pinned dependencies from the lockfile first (reproducible images,
# cache-friendly), then the package itself without re-resolving deps.
COPY pyproject.toml requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini .
COPY entrypoint.sh .
RUN pip install --no-cache-dir --no-deps . && chmod +x entrypoint.sh

EXPOSE 8000

# Liveness/readiness: /health returns 503 when pgvector is down.
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=5).status==200 else 1)"

RUN addgroup --system app && adduser --system --ingroup app app && chown -R app:app /app
USER app

CMD ["./entrypoint.sh"]
