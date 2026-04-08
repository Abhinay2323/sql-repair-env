"""
Data models for the SQL Repair Environment.

Inherits from openenv-core base classes so the framework auto-generates
/schema, /metadata, /mcp, and all other required endpoints.
"""

from typing import Any, List, Optional
from pydantic import BaseModel, Field
from openenv.core.env_server.types import Action, Observation


class SQLRepairAction(Action):
    """
    Submit a SQL query for evaluation.

    The agent sends a corrected SQL query; the environment executes it
    against an in-memory SQLite database and returns a scored reward.
    """

    query: str = Field(..., description="The SQL query to execute and evaluate")


class QueryResultModel(BaseModel):
    """Result of executing a SQL query (embedded in SQLRepairObservation)."""

    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    error: Optional[str] = None
    row_count: int = 0

    def preview(self, max_rows: int = 5) -> str:
        if self.error:
            return f"ERROR: {self.error}"
        if not self.rows:
            return f"(no rows) columns: {self.columns}"
        header = " | ".join(self.columns)
        sep = "-" * max(len(header), 10)
        rows_str = "\n".join(
            " | ".join(str(v) for v in row) for row in self.rows[:max_rows]
        )
        suffix = f"\n... ({self.row_count} rows total)" if self.row_count > max_rows else ""
        return f"{header}\n{sep}\n{rows_str}{suffix}"


class SQLRepairObservation(Observation):
    """
    Observation returned after each reset() or step().

    Contains the broken query, schema, last execution result, and
    current reward signal. The base Observation already provides
    `done: bool` and `reward: float | None`.
    """

    task_id: str = Field(default="", description="Task identifier")
    task_description: str = Field(default="", description="What the correct query should return")
    schema_info: str = Field(default="", description="Database schema shown to the agent")
    broken_query: str = Field(default="", description="The original broken query to fix")
    current_query: Optional[str] = Field(default=None, description="Agent's last submitted query")
    last_result: Optional[QueryResultModel] = Field(default=None, description="Result of last execution")
    last_error: Optional[str] = Field(default=None, description="Error from last failed execution")
    attempts_used: int = Field(default=0, description="Number of submissions so far")
    max_attempts: int = Field(default=10, description="Maximum allowed submissions")
