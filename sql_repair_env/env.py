"""
SQLRepairEnv — core environment class.

Implements the OpenEnv interface:
  reset(task)  → SQLObservation
  step(action) → StepResult
  state()      → SQLObservation
  close()
"""

from __future__ import annotations

import random
from typing import Optional

from .graders import grade
from .models import (
    QueryResult,
    ResetRequest,
    SQLAction,
    SQLObservation,
    StepResult,
)
from .tasks import TASK_NAMES, TASKS

# Score threshold at which we declare the episode solved
SOLVED_THRESHOLD = 0.95


class SQLRepairEnv:
    """
    SQL Query Repair Environment.

    The agent receives a broken SQL query and must fix it by submitting
    corrected queries.  Each submission is executed against a deterministic
    in-memory SQLite database and scored against the expected results.

    Episode lifecycle
    -----------------
    reset(task)  — choose a task, return initial observation
    step(action) — submit a query, get (obs, reward, done, info)
    state()      — inspect current observation without advancing

    Reward signal
    -------------
    0.00 : query fails to execute
    0.05 : executes but no column overlap
    0.05–0.20 : columns partially/fully match
    0.20–1.00 : columns + partial row match (F1 of row sets)
    1.00 : exact match (all columns + all rows)
    """

    def __init__(self) -> None:
        self._obs: Optional[SQLObservation] = None
        self._task_cfg: Optional[dict] = None
        self._best_score: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self, task: Optional[str] = None) -> SQLObservation:
        """
        Start a new episode.

        Parameters
        ----------
        task : str, optional
            One of 'fix_syntax', 'fix_logic', 'complex_analytics'.
            If None a random task is chosen.

        Returns
        -------
        SQLObservation
            Initial observation with the broken query and schema info.
        """
        if task is None:
            task = random.choice(TASK_NAMES)
        if task not in TASKS:
            raise ValueError(
                f"Unknown task '{task}'. Valid tasks: {TASK_NAMES}"
            )

        cfg = TASKS[task]
        self._task_cfg = cfg
        self._best_score = 0.0

        self._obs = SQLObservation(
            task_id=cfg["name"],
            task_description=cfg["task_description"],
            schema_info=cfg["schema_info"],
            broken_query=cfg["broken_query"],
            current_query=None,
            last_result=None,
            last_error=None,
            attempts_used=0,
            max_attempts=cfg["max_steps"],
            done=False,
            reward=0.0,
        )
        return self._obs

    def step(self, action: SQLAction) -> StepResult:
        """
        Submit a SQL query and receive feedback.

        Parameters
        ----------
        action : SQLAction
            action_type must be 'submit_query'; query is the SQL string.

        Returns
        -------
        StepResult
            observation, reward, done, info
        """
        if self._obs is None or self._task_cfg is None:
            raise RuntimeError("Call reset() before step().")
        if self._obs.done:
            raise RuntimeError("Episode is done. Call reset() to start a new one.")

        cfg = self._task_cfg
        query = (action.query or "").strip()

        # Evaluate
        score, result, info = grade(
            submitted_query=query,
            expected_query=cfg["expected_query"],
            db_setup=cfg["db_setup"],
        )

        self._obs.attempts_used += 1
        self._obs.current_query = query
        self._obs.reward = score
        self._obs.last_error = result.error
        self._obs.last_result = result if not result.error else None

        if score > self._best_score:
            self._best_score = score

        done = score >= SOLVED_THRESHOLD or self._obs.attempts_used >= self._obs.max_attempts
        self._obs.done = done

        info["best_score"] = round(self._best_score, 6)
        info["attempts_used"] = self._obs.attempts_used

        return StepResult(
            observation=self._obs,
            reward=score,
            done=done,
            info=info,
        )

    def state(self) -> SQLObservation:
        """Return the current observation without advancing the episode."""
        if self._obs is None:
            raise RuntimeError("Call reset() before state().")
        return self._obs

    def close(self) -> None:
        """Clean up (no-op for in-memory SQLite)."""
        self._obs = None
        self._task_cfg = None
        self._best_score = 0.0
