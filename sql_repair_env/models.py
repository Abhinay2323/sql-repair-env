from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class SQLAction(BaseModel):
    action_type: Literal["submit_query"] = "submit_query"
    query: str = Field(..., description="The SQL query to submit for evaluation")


class QueryResult(BaseModel):
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    error: Optional[str] = None
    row_count: int = 0

    @classmethod
    def from_error(cls, error: str) -> "QueryResult":
        return cls(error=error, row_count=0)

    def preview(self, max_rows: int = 5) -> str:
        if self.error:
            return f"ERROR: {self.error}"
        if not self.rows:
            return f"(no rows returned) columns: {self.columns}"
        header = " | ".join(self.columns)
        sep = "-" * len(header)
        rows_str = "\n".join(
            " | ".join(str(v) for v in row) for row in self.rows[:max_rows]
        )
        suffix = f"\n... ({self.row_count} rows total)" if self.row_count > max_rows else ""
        return f"{header}\n{sep}\n{rows_str}{suffix}"


class SQLObservation(BaseModel):
    task_id: str
    task_description: str
    schema_info: str
    broken_query: str
    current_query: Optional[str] = None
    last_result: Optional[QueryResult] = None
    last_error: Optional[str] = None
    attempts_used: int = 0
    max_attempts: int = 10
    done: bool = False
    reward: float = 0.0


class StepResult(BaseModel):
    observation: SQLObservation
    reward: float
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)


class ResetRequest(BaseModel):
    task: Optional[str] = None


class StepRequest(BaseModel):
    action_type: str = "submit_query"
    query: Optional[str] = None
