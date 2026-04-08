"""
Graders for the SQL Repair Environment.

Each grader:
  1. Creates an in-memory SQLite database from db_setup SQL
  2. Executes the expected query to obtain ground-truth results
  3. Executes the submitted query
  4. Computes a score in [0.0, 1.0] with partial credit

Scoring algorithm (deterministic):
  - Query fails to parse/execute          → 0.00
  - Executes, no columns match            → 0.05
  - Some columns match                    → 0.05 + column_overlap * 0.15
  - Rows partially match (F1 on row sets) → above + 0.80 * row_f1
  - Perfect match (all rows, all values)  → 1.00
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Tuple

from .models import QueryResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_query(conn: sqlite3.Connection, sql: str) -> Tuple[List[str], List[List[Any]], str | None]:
    """Execute *sql* and return (columns, rows, error_or_None)."""
    try:
        cursor = conn.execute(sql)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        rows = [list(r) for r in cursor.fetchall()]
        return cols, rows, None
    except Exception as exc:
        return [], [], str(exc)


def _normalise_value(v: Any) -> str:
    """Stable string representation for comparison (floats rounded to 4 dp)."""
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v) if v is not None else "NULL"


def _row_key(row: List[Any]) -> tuple:
    return tuple(_normalise_value(v) for v in row)


def _col_overlap(actual_cols: List[str], expected_cols: List[str]) -> float:
    if not expected_cols:
        return 1.0
    actual_set = {c.lower() for c in actual_cols}
    expected_set = {c.lower() for c in expected_cols}
    return len(actual_set & expected_set) / len(expected_set)


def _row_f1(actual_rows: List[List[Any]], expected_rows: List[List[Any]]) -> float:
    if not expected_rows and not actual_rows:
        return 1.0
    if not expected_rows or not actual_rows:
        return 0.0

    actual_set = {}
    for r in actual_rows:
        k = _row_key(r)
        actual_set[k] = actual_set.get(k, 0) + 1

    expected_set = {}
    for r in expected_rows:
        k = _row_key(r)
        expected_set[k] = expected_set.get(k, 0) + 1

    # Multiset intersection count
    common = sum(
        min(actual_set.get(k, 0), cnt)
        for k, cnt in expected_set.items()
    )

    precision = common / len(actual_rows) if actual_rows else 0.0
    recall = common / len(expected_rows) if expected_rows else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def grade(
    submitted_query: str,
    expected_query: str,
    db_setup: str,
) -> Tuple[float, QueryResult, Dict[str, Any]]:
    """
    Grade *submitted_query* against *expected_query* on a fresh in-memory DB.

    Returns
    -------
    score : float
        Value in [0.0, 1.0].
    result : QueryResult
        The result of executing *submitted_query* (or error info).
    info : dict
        Diagnostic metadata (expected_rows, actual_rows, col_overlap, row_f1).
    """
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")

    try:
        conn.executescript(db_setup)
    except Exception as exc:
        conn.close()
        return 0.0, QueryResult.from_error(f"DB setup error: {exc}"), {}

    # Ground-truth results
    exp_cols, exp_rows, exp_err = _run_query(conn, expected_query)
    if exp_err:
        conn.close()
        return 0.0, QueryResult.from_error(f"Expected query error: {exp_err}"), {}

    # Submitted query
    act_cols, act_rows, act_err = _run_query(conn, submitted_query)
    conn.close()

    if act_err:
        return 0.0, QueryResult.from_error(act_err), {"execution_error": act_err}

    result = QueryResult(
        columns=act_cols,
        rows=act_rows,
        row_count=len(act_rows),
    )

    # --- Score calculation ---
    col_ov = _col_overlap(act_cols, exp_cols)
    rf1 = _row_f1(act_rows, exp_rows)

    # Perfect match shortcut
    if act_cols == exp_cols and _row_key(act_rows) == _row_key(exp_rows):
        score = 1.0
    else:
        # 0.20 for columns, 0.80 for rows
        score = 0.20 * col_ov + 0.80 * rf1
        # Clamp
        score = min(max(score, 0.0), 1.0)
        # Round to avoid floating-point drift
        score = round(score, 6)

    info: Dict[str, Any] = {
        "expected_rows": len(exp_rows),
        "actual_rows": len(act_rows),
        "expected_cols": exp_cols,
        "actual_cols": act_cols,
        "col_overlap": round(col_ov, 4),
        "row_f1": round(rf1, 4),
    }

    return score, result, info
