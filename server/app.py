"""
FastAPI application for the SQL Repair Environment.

Uses openenv-core's create_app() which automatically provides:
  POST /reset    — start a new episode
  POST /step     — submit a query action
  GET  /state    — current observation
  GET  /schema   — action / observation / state schemas
  GET  /metadata — environment name and description
  GET  /health   — liveness probe  {"status": "healthy"}
  POST /mcp      — JSON-RPC MCP endpoint
  WS   /ws       — WebSocket for persistent sessions

Usage
-----
  # Development
  uvicorn server.app:app --reload --host 0.0.0.0 --port 7860

  # Or via pyproject.toml script
  uv run server --port 7860
"""

from __future__ import annotations

import os
import sys

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from openenv.core.env_server.http_server import create_app
except ImportError as exc:
    raise ImportError(
        "openenv-core is required. Install with: pip install openenv-core"
    ) from exc

try:
    from models import SQLRepairAction, SQLRepairObservation
    from server.sql_repair_env_environment import SQLRepairEnvEnvironment
except ModuleNotFoundError:
    from models import SQLRepairAction, SQLRepairObservation  # type: ignore
    from sql_repair_env_environment import SQLRepairEnvEnvironment  # type: ignore


app = create_app(
    SQLRepairEnvEnvironment,
    SQLRepairAction,
    SQLRepairObservation,
    env_name="sql-repair-env",
    max_concurrent_envs=1,
)


def main(host: str = "0.0.0.0", port: int = 7860) -> None:
    """
    Entry point for direct execution via uv run or python -m.

        uv run server
        uv run server --port 7860
        python -m server.app
    """
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    main()  # delegates to uvicorn with defaults
