"""
SQL Repair Environment — core Environment implementation.

Inherits from openenv.core.env_server.interfaces.Environment so that
create_app() can wrap it with all required HTTP endpoints.
"""

from __future__ import annotations

import random
import sys
import os
from typing import Optional
from uuid import uuid4

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

from graders import grade
from models import QueryResultModel, SQLRepairAction, SQLRepairObservation
from tasks import TASK_NAMES, TASKS

SOLVED_THRESHOLD = 0.95


class SQLRepairEnvEnvironment(Environment):
    """
    SQL Query Repair Environment.

    The agent receives a broken SQL query and must fix it by submitting
    corrected queries.  Each submission is executed against a deterministic
    in-memory SQLite database and scored against the expected results.

    Episode lifecycle
    -----------------
    reset(task)  — choose a task, return initial observation
    step(action) — submit a query, get scored observation
    state        — inspect current observation without advancing

    Reward signal (all in [0.0, 1.0])
    ----------------------------------
    0.00 : query fails to execute (syntax/runtime error)
    0.20 : executes, columns match expected but rows are wrong
    0.20–1.00 : F1 score on row sets weighted 80%, column overlap 20%
    1.00 : exact match — episode ends (done=True)
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = False

    def __init__(self) -> None:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._obs: Optional[SQLRepairObservation] = None
        self._task_cfg: Optional[dict] = None
        self._best_score: float = 0.0

    # ------------------------------------------------------------------
    # OpenEnv interface
    # ------------------------------------------------------------------

    def reset(
        self,
        task: Optional[str] = None,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs,
    ) -> SQLRepairObservation:
        """
        Start a new episode.

        Parameters
        ----------
        task : str, optional
            One of 'fix_syntax', 'fix_logic', 'complex_analytics'.
            If omitted, a task is chosen randomly.
        seed : int, optional
            Random seed (passed by framework; used to seed task choice).
        episode_id : str, optional
            Custom episode identifier.
        """
        if seed is not None:
            random.seed(seed)

        if task is None:
            task = random.choice(TASK_NAMES)
        if task not in TASKS:
            # Fall back to random rather than crashing
            task = random.choice(TASK_NAMES)

        cfg = TASKS[task]
        self._task_cfg = cfg
        self._best_score = 0.0
        self._state = State(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
        )

        self._obs = SQLRepairObservation(
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

    def step(self, action: SQLRepairAction) -> SQLRepairObservation:  # type: ignore[override]
        """
        Submit a SQL query and receive scored feedback.

        Parameters
        ----------
        action : SQLRepairAction
            Must have a non-empty `query` field.

        Returns
        -------
        SQLRepairObservation
            Updated observation with reward, done flag, and last result.
        """
        if self._obs is None or self._task_cfg is None:
            # Auto-reset to a random task if not yet initialised
            self.reset()

        assert self._obs is not None
        assert self._task_cfg is not None

        if self._obs.done:
            # Episode already finished — return current state unchanged
            return self._obs

        cfg = self._task_cfg
        query = (action.query or "").strip()

        score, result, _ = grade(
            submitted_query=query,
            expected_query=cfg["expected_query"],
            db_setup=cfg["db_setup"],
        )

        self._state.step_count += 1
        self._obs.attempts_used += 1
        self._obs.current_query = query
        self._obs.reward = score
        self._obs.last_error = result.error
        self._obs.last_result = result if not result.error else None

        if score > self._best_score:
            self._best_score = score

        done = score >= SOLVED_THRESHOLD or self._obs.attempts_used >= self._obs.max_attempts
        self._obs.done = done

        return self._obs

    @property
    def state(self) -> State:
        """Return the internal State object (episode_id, step_count)."""
        return self._state
