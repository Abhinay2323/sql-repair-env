"""
SQL Repair Grader

This module evaluates a submitted SQL query against an expected query
by executing both on an in-memory SQLite database.

Scoring Rules:
--------------
1. Execution failure                  → 0.00
2. No column overlap                 → 0.05
3. Partial column match              → 0.05 + (column_overlap * 0.15)
4. Row similarity (F1 score)         → above + (0.80 * row_f1)
5. Perfect match                     → 1.00
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Tuple, Optional

from models import QueryResultModel as QueryResult


# ---------------------------------------------------------------------------
# Database Utilities
# ---------------------------------------------------------------------------

def _execute_query(
    conn: sqlite3.Connection, sql: str
) -> Tuple[List[str], List[List[Any]], Optional[str]]:
    """
    Execute a SQL query safely.

    Returns:
        columns: List of column names
        rows: Query result rows
        error: Error message if execution fails, else None
    """
    try:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [list(row) for row in cursor.fetchall()]
        return columns, rows, None
    except Exception as exc:
        return [], [], str(exc)


# ---------------------------------------------------------------------------
# Normalization Helpers
# ---------------------------------------------------------------------------

def _normalize_value(value: Any) -> str:
    """
    Normalize values into a stable string format for comparison.
    Floats are rounded to 4 decimal places.
    """
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value) if value is not None else "NULL"


def _row_to_key(row: List[Any]) -> Tuple[str, ...]:
    """Convert a row into a comparable tuple key."""
    return tuple(_normalize_value(v) for v in row)


# ---------------------------------------------------------------------------
# Scoring Helpers
# ---------------------------------------------------------------------------

def _calculate_column_overlap(
    actual_cols: List[str], expected_cols: List[str]
) -> float:
    """
    Compute column overlap ratio (case-insensitive).
    """
    if not expected_cols:
        return 1.0

    actual_set = {col.lower() for col in actual_cols}
    expected_set = {col.lower() for col in expected_cols}

    return len(actual_set & expected_set) / len(expected_set)


def _calculate_row_f1(
    actual_rows: List[List[Any]], expected_rows: List[List[Any]]
) -> float:
    """
    Compute F1 score between actual and expected rows using multiset logic.
    """
    if not expected_rows and not actual_rows:
        return 1.0
    if not expected_rows or not actual_rows:
        return 0.0

    def build_multiset(rows: List[List[Any]]) -> Dict[Tuple[str, ...], int]:
        multiset: Dict[Tuple[str, ...], int] = {}
        for row in rows:
            key = _row_to_key(row)
            multiset[key] = multiset.get(key, 0) + 1
        return multiset

    actual_multiset = build_multiset(actual_rows)
    expected_multiset = build_multiset(expected_rows)

    # Intersection count
    common_count = sum(
        min(actual_multiset.get(key, 0), count)
        for key, count in expected_multiset.items()
    )

    precision = common_count / len(actual_rows) if actual_rows else 0.0
    recall = common_count / len(expected_rows) if expected_rows else 0.0

    if precision + recall == 0:
        return 0.0

    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# Core Grading Logic
# ---------------------------------------------------------------------------

def _compute_score(
    actual_cols: List[str],
    expected_cols: List[str],
    actual_rows: List[List[Any]],
    expected_rows: List[List[Any]],
) -> Tuple[float, float, float]:
    """
    Compute final score along with intermediate metrics.
    """
    col_overlap = _calculate_column_overlap(actual_cols, expected_cols)
    row_f1 = _calculate_row_f1(actual_rows, expected_rows)

    # Perfect match shortcut
    if actual_cols == expected_cols and _row_to_key(actual_rows) == _row_to_key(expected_rows):
        return 0.99, col_overlap, row_f1

    score = 0.20 * col_overlap + 0.80 * row_f1
    score = round(min(max(score, 0.01), 0.99), 6)

    return score, col_overlap, row_f1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def grade(
    submitted_query: str,
    expected_query: str,
    db_setup: str,
) -> Tuple[float, QueryResult, Dict[str, Any]]:
    """
    Evaluate a submitted SQL query against an expected query.

    Workflow:
        1. Initialize in-memory database
        2. Execute DB setup script
        3. Run expected query (ground truth)
        4. Run submitted query
        5. Compare results and compute score

    Returns:
        score: Float in range [0.0, 1.0]
        result: QueryResult object for submitted query
        info: Diagnostic metadata
    """
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")

    # Step 1: Setup DB
    try:
        conn.executescript(db_setup)
    except Exception as exc:
        conn.close()
        return 0.01, QueryResult(error=f"DB setup error: {exc}"), {}

    # Step 2: Execute expected query
    expected_cols, expected_rows, expected_err = _execute_query(conn, expected_query)
    if expected_err:
        conn.close()
        return 0.01, QueryResult(error=f"Expected query error: {expected_err}"), {}

    # Step 3: Execute submitted query
    actual_cols, actual_rows, actual_err = _execute_query(conn, submitted_query)
    conn.close()

    if actual_err:
        return 0.01, QueryResult(error=actual_err), {"execution_error": actual_err}

    # Step 4: Build result object
    result = QueryResult(
        columns=actual_cols,
        rows=actual_rows,
        row_count=len(actual_rows),
    )

    # Step 5: Compute score
    score, col_overlap, row_f1 = _compute_score(
        actual_cols, expected_cols, actual_rows, expected_rows
    )

    # Step 6: Diagnostics
    info: Dict[str, Any] = {
        "expected_rows": len(expected_rows),
        "actual_rows": len(actual_rows),
        "expected_cols": expected_cols,
        "actual_cols": actual_cols,
        "col_overlap": round(col_overlap, 4),
        "row_f1": round(row_f1, 4),
    }

    return score, result, info