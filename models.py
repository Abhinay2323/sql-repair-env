"""
Data Models for the SQL Repair Environment

These models extend `openenv-core` base classes, enabling automatic
generation of endpoints such as:
    - /schema
    - /metadata
    - /mcp

They define the interaction contract between the agent and environment.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field
from openenv.core.env_server.types import Action, Observation


# ---------------------------------------------------------------------------
# Action Model
# ---------------------------------------------------------------------------

class SQLRepairAction(Action):
    """
    Action representing a SQL query submission.

    The agent submits a corrected SQL query, which is then executed
    against an in-memory SQLite database for evaluation.
    """

    query: str = Field(
        ...,
        description="SQL query submitted by the agent for evaluation"
    )


# ---------------------------------------------------------------------------
# Query Result Model
# ---------------------------------------------------------------------------

class QueryResultModel(BaseModel):
    """
    Represents the result of executing a SQL query.

    Attributes:
        columns: Column names returned by the query
        rows: Result rows (list of records)
        error: Error message (if execution failed)
        row_count: Total number of rows returned
    """

    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    error: Optional[str] = None
    row_count: int = 0

    def preview(self, max_rows: int = 5) -> str:
        """
        Generate a human-readable preview of the query result.

        Args:
            max_rows: Maximum number of rows to display

        Returns:
            Formatted string representation of the result
        """
        if self.error:
            return f"ERROR: {self.error}"

        if not self.rows:
            return f"(no rows) columns: {self.columns}"

        header = " | ".join(self.columns)
        separator = "-" * max(len(header), 10)

        preview_rows = "\n".join(
            " | ".join(str(value) for value in row)
            for row in self.rows[:max_rows]
        )

        suffix = (
            f"\n... ({self.row_count} rows total)"
            if self.row_count > max_rows
            else ""
        )

        return f"{header}\n{separator}\n{preview_rows}{suffix}"


# ---------------------------------------------------------------------------
# Observation Model
# ---------------------------------------------------------------------------

class SQLRepairObservation(Observation):
    """
    Observation returned after each environment interaction.

    Includes:
        - Task metadata
        - Database schema
        - Broken query
        - Agent's latest submission
        - Execution results
        - Reward and completion status (inherited)

    Note:
        The base `Observation` class already provides:
            - done: bool
            - reward: Optional[float]
    """

    task_id: str = Field(
        default="",
        description="Unique identifier for the task"
    )

    task_description: str = Field(
        default="",
        description="Description of the expected query result"
    )

    schema_info: str = Field(
        default="",
        description="Database schema provided to the agent"
    )

    broken_query: str = Field(
        default="",
        description="Initial incorrect SQL query to be repaired"
    )

    current_query: Optional[str] = Field(
        default=None,
        description="Most recent query submitted by the agent"
    )

    last_result: Optional[QueryResultModel] = Field(
        default=None,
        description="Result of the last query execution"
    )

    last_error: Optional[str] = Field(
        default=None,
        description="Error message from the last failed execution"
    )

    attempts_used: int = Field(
        default=0,
        description="Number of attempts made so far"
    )

    max_attempts: int = Field(
        default=10,
        description="Maximum number of allowed attempts"
    )