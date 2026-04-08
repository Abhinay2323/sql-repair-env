FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Copy source before full sync so the project package installs cleanly
COPY models.py tasks.py graders.py openenv.yaml inference.py README.md ./
COPY server/ ./server/

# Full install including the project itself (runs as root during build = no permission issues)
RUN uv sync --frozen --no-dev

EXPOSE 7860

CMD ["uv", "run", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
