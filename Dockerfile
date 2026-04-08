FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Non-root user for HuggingFace Spaces
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (no project itself yet)
RUN uv sync --frozen --no-install-project --no-dev

# Copy source
COPY models.py tasks.py graders.py openenv.yaml inference.py README.md ./
COPY server/ ./server/

# HuggingFace Spaces default port
EXPOSE 7860

USER appuser

CMD ["uv", "run", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
