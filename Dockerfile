FROM node:22-alpine AS web

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


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

# Pinned dependencies only. The app itself is not installed into the venv:
# it runs from /app/app, which the runtime stage copies.
COPY backend/requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock


FROM python:3.12-slim AS runtime

WORKDIR /app

# Code indexing shells out to the git binary -- RepoManager._run_git runs
# `git clone/fetch/rev-parse/diff` as a subprocess, and no pure-Python git is
# in the lockfile. Without this the image boots, /health answers 200 and the
# healthcheck passes, while every repository operation fails with
# "git: not found"; the only symptom is that indexing never works.
# ca-certificates is already in the base image, so https clones need nothing
# further.
# postgresql-client: the backup_ship job dumps over the stack network, and
# the client major must be >= the server's (pg17); trixie ships 17. age: a
# dump is encrypted before it leaves the host, with an X25519 recipient --
# the identity never enters the image or the database, because a snapshot
# carrying its own decryption key defeats encryption at rest.
# openssh-client + rsync: the ssh destination ships via scp/rsync.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git postgresql-client age openssh-client rsync \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=root:root --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Root-owned, so the `app` user the server runs as cannot rewrite its own code.
# Compiled here because that user cannot write the bytecode at runtime either.
COPY --chown=root:root backend/app/ app/
COPY --chown=root:root backend/migrations/ migrations/
COPY --chown=root:root backend/alembic.ini .
COPY --chown=root:root entrypoint.sh .
# Strip any CR so a Windows-checkout (CRLF) shebang doesn't become
# "#!/bin/sh\r", which the kernel can't exec ("No such file or directory").
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh \
    && python -m compileall -q app migrations

COPY --chown=root:root --from=web /app/dist ./web

# An image whose SPA copy failed boots perfectly: migrations run, /health
# answers 200 and the healthcheck passes, and the only symptom is a UI that
# 404s after cutover. `test -d web/assets` would not catch it -- a directory
# that exists but is empty passes -- so assert the index is non-empty, the
# assets directory is non-empty, and every asset the index references is here.
RUN set -eu; \
    test -s web/index.html; \
    [ -n "$(ls -A web/assets)" ]; \
    for f in $(grep -oE '/assets/[A-Za-z0-9._-]+' web/index.html | sort -u); do \
        test -f "web$f"; \
    done

EXPOSE 8000

# Liveness/readiness: /health returns 503 when pgvector is down.
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=5).status==200 else 1)"

# The paths the app writes, created owned by `app`: a named volume mounted on a
# path the image lacks is created root-owned, and `app` then cannot write it.
RUN addgroup --system app && adduser --system --ingroup app app \
    && install -d -o app -g app /app/data /app/data/attachments /app/data/repositories /dumps
USER app

CMD ["./entrypoint.sh"]
