FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
COPY data/csv ./data/csv
COPY data/ground_truth ./data/ground_truth
ENV PATH="/app/.venv/bin:${PATH}" PORT=8000 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 routeiq
USER routeiq
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/health',timeout=2)" || exit 1
CMD ["sh", "-c", "uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
