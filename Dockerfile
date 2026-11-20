FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 HOME=/tmp
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app.py ./
COPY haq ./haq
COPY data/corpus.jsonl data/corpus.jsonl
COPY data/templates data/templates
ENV PATH="/app/.venv/bin:$PATH"
# Cloud Run injects PORT. Secrets and settings come from the service's env vars, never from the image.
CMD streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false
