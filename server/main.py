"""
FastAPI server for the SQL Repair Environment.

Endpoints
---------
POST /reset   — Start a new episode (optionally specify task name in JSON body)
POST /step    — Submit a SQL query action
GET  /state   — Inspect current observation
GET  /tasks   — List available tasks
GET  /health  — Liveness probe
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from sql_repair_env import SQLRepairEnv, SQLAction
from sql_repair_env.models import ResetRequest, StepRequest
from sql_repair_env.tasks import TASK_NAMES, TASKS

app = FastAPI(
    title="SQL Repair Environment",
    description=(
        "OpenEnv-compliant environment where agents debug and fix broken SQL queries. "
        "Three tasks: fix_syntax (easy), fix_logic (medium), complex_analytics (hard)."
    ),
    version="1.0.0",
)

# Single global session (sufficient for sequential evaluation)
_env = SQLRepairEnv()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ResetBody(BaseModel):
    task: Optional[str] = None


class StepBody(BaseModel):
    action_type: str = "submit_query"
    query: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
    <html><head><title>SQL Repair Environment</title></head>
    <body style="font-family:sans-serif;max-width:700px;margin:60px auto;padding:0 20px">
      <h1>🔧 SQL Repair Environment</h1>
      <p>An OpenEnv-compliant environment where AI agents debug and fix broken SQL queries.</p>
      <h3>Tasks</h3>
      <ul>
        <li><b>fix_syntax</b> — Easy: fix 3 typos in a SELECT query</li>
        <li><b>fix_logic</b> — Medium: fix a wrong JOIN condition</li>
        <li><b>complex_analytics</b> — Hard: fix 3 bugs in a CTE analytics query</li>
      </ul>
      <h3>API Endpoints</h3>
      <ul>
        <li><code>POST /reset</code> — Start new episode</li>
        <li><code>POST /step</code> — Submit a SQL query</li>
        <li><code>GET  /state</code> — Current observation</li>
        <li><code>GET  /tasks</code> — List all tasks</li>
      </ul>
      <p><a href="/docs">📖 Interactive API Docs (Swagger)</a></p>
    </body></html>
    """


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/tasks")
def list_tasks() -> Dict[str, Any]:
    return {
        "tasks": [
            {
                "name": t["name"],
                "difficulty": t["difficulty"],
                "max_steps": t["max_steps"],
            }
            for t in TASKS.values()
        ]
    }


@app.post("/reset")
def reset(body: ResetBody = ResetBody()) -> Dict[str, Any]:
    """
    Start a new episode.

    Body (optional JSON):
        { "task": "fix_syntax" | "fix_logic" | "complex_analytics" }

    If task is omitted, a random task is selected.
    """
    try:
        obs = _env.reset(task=body.task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "observation": obs.model_dump(),
        "info": {
            "task": obs.task_id,
            "difficulty": TASKS[obs.task_id]["difficulty"],
            "max_steps": obs.max_attempts,
            "valid_tasks": TASK_NAMES,
        },
    }


@app.post("/step")
def step(body: StepBody) -> Dict[str, Any]:
    """
    Submit a SQL query.

    Body:
        { "action_type": "submit_query", "query": "<your SQL here>" }
    """
    if body.action_type != "submit_query":
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action_type '{body.action_type}'. Only 'submit_query' is supported.",
        )
    if not body.query or not body.query.strip():
        raise HTTPException(status_code=400, detail="'query' field is required and must not be empty.")

    try:
        result = _env.step(SQLAction(action_type="submit_query", query=body.query))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "observation": result.observation.model_dump(),
        "reward": result.reward,
        "done": result.done,
        "info": result.info,
    }


@app.get("/state")
def state() -> Dict[str, Any]:
    """Return the current observation without advancing the episode."""
    try:
        obs = _env.state()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"observation": obs.model_dump()}
