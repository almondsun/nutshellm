FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/app/data/nutshellm.sqlite3
WORKDIR /app
RUN addgroup --system nutshellm && adduser --system --ingroup nutshellm nutshellm
COPY pyproject.toml README.md ./
COPY backend/ backend/
RUN pip install --no-cache-dir .
COPY --from=web /web/dist frontend/dist
COPY docker-entrypoint.sh /usr/local/bin/nutshellm-entrypoint
RUN mkdir -p /app/data && chown -R nutshellm:nutshellm /app
RUN chmod 0755 /usr/local/bin/nutshellm-entrypoint
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)"
ENTRYPOINT ["/usr/local/bin/nutshellm-entrypoint"]
CMD ["uvicorn", "nutshellm.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
