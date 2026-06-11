FROM python:3.12-slim AS builder

WORKDIR /app

# tree-sitter-cmake publishes no Linux wheel (only a Windows wheel + sdist),
# so it must be compiled from source. Provide a C toolchain here; it stays in
# the builder stage and never ships in the runtime image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Degraded routes to pypi.org (slow international transit) can stretch one
# index fetch past pip's 15s default read timeout, failing the whole build;
# slow down instead of dying.
ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

# Install pinned dependencies from the lockfile first (reproducible images,
# cache-friendly), then the package itself without re-resolving deps.
COPY pyproject.toml requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY app/ app/
RUN pip install --no-cache-dir --no-deps .


FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini .
COPY entrypoint.sh .
# Strip any CR so a Windows-checkout (CRLF) shebang doesn't become
# "#!/bin/sh\r", which the kernel can't exec ("No such file or directory").
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 8000

# Liveness/readiness: /health returns 503 when pgvector is down.
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=5).status==200 else 1)"

RUN addgroup --system app && adduser --system --ingroup app app && chown -R app:app /app
USER app

CMD ["./entrypoint.sh"]
