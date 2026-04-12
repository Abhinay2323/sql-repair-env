---
title: SQL Repair Environment
sdk: docker
pinned: false
tags:
  - openenv
  - sql
  - database
  - agent
  - evaluation
---

# SQL Repair Environment

An OpenEnv-compliant environment where AI agents debug and fix broken SQL queries.

---

## Motivation

Database query debugging is a high-frequency, high-value real-world task. Engineers
spend hours tracing wrong aggregations, JOIN mismatches, and subtle syntax typos.
This environment trains and evaluates agents on exactly this skill — with deterministic
graders and clear partial-progress signals.

---

## Environment Description

The agent receives a broken SQL query and a database schema. It must submit corrected
queries (executed against an in-memory SQLite database) until it solves the task
(reward ≥ 0.95) or exhausts its attempts.

Each submission is evaluated against ground-truth results. Partial credit rewards
progress toward the solution.

---

## Action Space

| Field | Type   | Description                           |
|-------|--------|---------------------------------------|
| query | string | The SQL query to execute and evaluate |

**Example (HTTP):**
```json
{ "action": { "query": "SELECT name, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC" } }
```

---

## Observation Space

| Field            | Type   | Description                                        |
|-----------------|--------|----------------------------------------------------|
| task_id          | string | Task identifier                                    |
| task_description | string | Natural language description of expected results   |
| schema_info      | string | Table/column definitions shown to the agent        |
| broken_query     | string | The original broken query to fix                   |
| current_query    | string | The agent's most recent submission                 |
| last_result      | object | Columns + rows from last execution (if successful) |
| last_error       | string | Error from last failed execution, or null          |
| attempts_used    | int    | Number of submissions so far                       |
| max_attempts     | int    | Episode length limit                               |
| done             | bool   | Whether the episode has ended                      |
| reward           | float  | Score from the last step [0.0 – 1.0]              |

---

## Tasks

### 1. `fix_syntax` — Easy (max 8 steps)

**Domain:** Employee salary table
**Bug count:** 3 typos
- `salry` → `salary` (column name)
- `emplyees` → `employees` (table name)
- `ORER BY` → `ORDER BY` (keyword)

**Baseline score:** ~1.00

---

### 2. `fix_logic` — Medium (max 12 steps)

**Domain:** Multi-table e-commerce orders
**Bug count:** 1 logical error
- `JOIN orders o ON c.customer_id = o.product_id` — wrong FK column (should be `o.customer_id`)

**Baseline score:** ~0.85–1.00

---

### 3. `complex_analytics` — Hard (max 15 steps)

**Domain:** E-commerce user revenue analytics with CTEs
**Bug count:** 3 subtle bugs — wrong aggregation function, case-sensitive status filter, incorrect HAVING clause

**Baseline score:** ~0.50–0.80

---

### 4. `fix_null_handling` — Medium (max 10 steps)

**Domain:** Sales commission calculation with nullable rates
**Bug count:** 1 — missing `COALESCE` causes NULL × amount = NULL, silently zeroing those reps' contributions to regional totals

**Baseline score:** ~0.85–1.00

---

### 5. `fix_duplicate_count` — Medium (max 10 steps)

**Domain:** E-commerce order counting across customers
**Bug count:** 1 — `COUNT(*)` after joining `order_items` counts item rows, not orders (fan-out trap); fix is `COUNT(DISTINCT o.order_id)`

**Baseline score:** ~0.85–1.00

---

### 6. `fix_window_rank` — Hard (max 15 steps)

**Domain:** Employee salary ranking per department using window functions
**Bug count:** 1 — `ROW_NUMBER() OVER (ORDER BY salary DESC)` ranks globally; missing `PARTITION BY department` means only the 2 highest-paid company-wide are returned instead of top 2 per department

**Baseline score:** ~0.40–0.75

---

## Reward Function

```
0.00  — query fails to execute (syntax/runtime error)
0.20  — executes, columns match, rows wrong
0.20–1.00 — column overlap (20%) + row F1 score (80%)
1.00  — exact match → episode ends (done=True)
```

---

## API Endpoints

| Method | Path        | Description                               |
|--------|-------------|-------------------------------------------|
| POST   | `/reset`    | Start new episode (optional task in body) |
| POST   | `/step`     | Submit a query action                     |
| GET    | `/state`    | Inspect current observation               |
| GET    | `/schema`   | Action / observation schemas              |
| GET    | `/metadata` | Environment name and description          |
| GET    | `/health`   | Liveness probe                            |
| POST   | `/mcp`      | JSON-RPC MCP endpoint                     |

### Reset
```bash
curl -X POST https://Abhinay124-sql-repair-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "fix_syntax"}'
```

### Step
```bash
curl -X POST https://Abhinay124-sql-repair-env.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"query": "SELECT name, salary FROM employees WHERE department = '\''Engineering'\'' ORDER BY salary DESC"}}'
```

---

## Setup & Usage

### Local with uv

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run the server
uv run uvicorn server.app:app --host 0.0.0.0 --port 7860

# Run baseline inference (requires HF_TOKEN)
export HF_TOKEN=your_token
uv run python inference.py
```

### Docker

```bash
docker build -t sql-repair-env .
docker run -p 7860:7860 -e HF_TOKEN=your_token sql-repair-env
```

### Single task

```bash
TASK_NAME=fix_syntax uv run python inference.py
```

---

## Baseline Scores

Tested with `Qwen/Qwen2.5-72B-Instruct` via HuggingFace Inference API:

| Task                | Difficulty | Expected Score | Typical Steps |
|--------------------|-----------|---------------|---------------|
| fix_syntax          | Easy       | 0.95–1.00     | 1–2           |
| fix_logic           | Medium     | 0.80–1.00     | 1–3           |
| fix_null_handling   | Medium     | 0.85–1.00     | 1–2           |
| fix_duplicate_count | Medium     | 0.85–1.00     | 1–3           |
| complex_analytics   | Hard       | 0.50–0.85     | 3–8           |
| fix_window_rank     | Hard       | 0.40–0.75     | 3–10          |

---

## Environment Variables

| Variable     | Default                          | Description              |
|-------------|----------------------------------|--------------------------|
| API_BASE_URL | https://router.huggingface.co/v1 | LLM API endpoint         |
| MODEL_NAME   | Qwen/Qwen2.5-72B-Instruct        | Model identifier         |
| HF_TOKEN     | (required)                       | HuggingFace / API key    |
| TASK_NAME    | (all tasks)                      | Run a single task        |

---

## Project Structure

```
sql-repair-env/
├── Dockerfile
├── README.md
├── openenv.yaml               ← OpenEnv spec
├── pyproject.toml             ← dependencies + scripts
├── uv.lock                    ← locked dependency versions
├── inference.py               ← baseline inference script
├── models.py                  ← Action / Observation models (openenv base classes)
├── tasks.py                   ← task definitions (schema, data, queries)
├── graders.py                 ← deterministic scoring logic
└── server/
    ├── app.py                 ← FastAPI app via openenv create_app()
    └── sql_repair_env_environment.py  ← Environment class
```
