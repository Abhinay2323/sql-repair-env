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

# Create non-root user required by HuggingFace Spaces, then transfer ownership
# Must happen AFTER uv sync so .venv is owned by appuser from the start
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Enable the Gradio web UI served at /web by openenv-core.
# Without this the root "/" returns 404 (plain FastAPI has no root route).
ENV ENABLE_WEB_INTERFACE=true

EXPOSE 7860

USER appuser

# Use venv's uvicorn directly — avoids uv trying to re-install the project
# at runtime as non-root (which caused the Permission Denied error on HF Spaces)
CMD ["/app/.venv/bin/uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
