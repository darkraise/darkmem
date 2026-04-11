FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000

RUN addgroup --system app && adduser --system --ingroup app app && chown -R app:app /app
USER app

CMD ["./entrypoint.sh"]
