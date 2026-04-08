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
queries (against an in-memory SQLite database) until it either solves the task (reward
≥ 0.95) or exhausts its attempts.

Each submission is evaluated against ground-truth results produced by the correct query.
Partial credit rewards progress toward the solution.

---

## Action Space

| Field        | Type   | Description                                      |
|-------------|--------|--------------------------------------------------|
| action_type | string | Always `"submit_query"`                          |
| query       | string | The SQL query to execute and evaluate            |

**Example:**
```json
{ "action_type": "submit_query", "query": "SELECT name, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC" }
```

---

## Observation Space

| Field            | Type    | Description                                          |
|-----------------|---------|------------------------------------------------------|
| task_id          | string  | Task identifier                                      |
| task_description | string  | Natural language description of expected results     |
| schema_info      | string  | Table/column definitions shown to the agent          |
| broken_query     | string  | The original broken query to fix                     |
| current_query    | string  | The agent's most recent submission                   |
| last_result      | object  | Columns + rows from last execution (if successful)   |
| last_error       | string  | Error message from last failed execution, or null    |
| attempts_used    | int     | Number of submissions so far                         |
| max_attempts     | int     | Episode length limit                                 |
| done             | bool    | Whether the episode has ended                        |
| reward           | float   | Score from the last step [0.0 – 1.0]                |

---

## Tasks

### 1. `fix_syntax` — Easy (max 8 steps)

**Domain:** Employee salary table  
**Bug count:** 3 typos  
**Bugs:**
- `salry` → `salary` (column name)
- `emplyees` → `employees` (table name)
- `ORER BY` → `ORDER BY` (keyword)

**Baseline score:** ~1.00 (frontier LLMs handle typos well)

---

### 2. `fix_logic` — Medium (max 12 steps)

**Domain:** Multi-table e-commerce orders (customers × orders)  
**Bug count:** 1 logical error  
**Bug:** `JOIN orders o ON c.customer_id = o.product_id` uses the wrong FK column
(should be `o.customer_id`), producing completely wrong aggregation results.

**Baseline score:** ~0.85–1.00

---

### 3. `complex_analytics` — Hard (max 15 steps)

**Domain:** E-commerce user revenue analytics with CTEs  
**Bug count:** 3 subtle bugs  
**Bugs:**
1. `AVG(oi.quantity * oi.unit_price)` → `SUM(...)` (wrong aggregation function)
2. `o.status = 'COMPLETED'` → `'completed'` (SQLite string comparison is case-sensitive)
3. `HAVING total_revenue > 100` → `HAVING num_orders >= 2` (wrong filter semantics)

**Baseline score:** ~0.50–0.80 (hard for most models on first pass)

---

## Reward Function

Scoring is deterministic and based on comparing query results to ground truth:

```
0.00  — query fails to execute (syntax/runtime error)
0.20  — columns match + F1 of row sets
...   — partial credit proportional to column overlap (0.20) + row F1 (0.80)
1.00  — exact match (all columns, all rows, all values)
```

The episode ends when `reward >= 0.95` (solved) or `attempts_used >= max_attempts`.

---

## API Endpoints

| Method | Path     | Description                              |
|--------|----------|------------------------------------------|
| POST   | `/reset` | Start new episode (optional task in body)|
| POST   | `/step`  | Submit a query action                    |
| GET    | `/state` | Inspect current observation              |
| GET    | `/tasks` | List all available tasks                 |
| GET    | `/health`| Liveness probe                           |

### Reset
```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "fix_syntax"}'
```

### Step
```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "submit_query", "query": "SELECT name, salary FROM employees WHERE department = '\''Engineering'\'' ORDER BY salary DESC"}'
```

---

## Setup & Usage

### Local (Python)

```bash
pip install -r requirements.txt

# Run the FastAPI server
uvicorn server.main:app --host 0.0.0.0 --port 7860

# Run baseline inference (requires HF_TOKEN)
export HF_TOKEN=your_token
python inference.py
```

### Docker

```bash
docker build -t sql-repair-env .
docker run -p 7860:7860 -e HF_TOKEN=your_token sql-repair-env
```

### Run a single task

```bash
TASK_NAME=fix_syntax python inference.py
```

---

## Baseline Scores

Tested with `Qwen/Qwen2.5-72B-Instruct` via HuggingFace Inference API:

| Task               | Difficulty | Expected Score | Typical Steps |
|-------------------|-----------|---------------|---------------|
| fix_syntax         | Easy       | 0.95–1.00     | 1–2           |
| fix_logic          | Medium     | 0.80–1.00     | 1–3           |
| complex_analytics  | Hard       | 0.50–0.85     | 3–8           |

---

## Environment Variables

| Variable      | Default                            | Description                       |
|--------------|------------------------------------|-----------------------------------|
| API_BASE_URL  | https://router.huggingface.co/v1   | LLM API endpoint                  |
| MODEL_NAME    | Qwen/Qwen2.5-72B-Instruct          | Model identifier                  |
| HF_TOKEN      | (required)                         | HuggingFace / API key             |
| TASK_NAME     | (all tasks)                        | Override to run a single task     |

---

## Project Structure

```
sql-repair-env/
├── Dockerfile
├── README.md
├── openenv.yaml
├── requirements.txt
├── inference.py           ← baseline inference script
├── sql_repair_env/
│   ├── __init__.py
│   ├── env.py             ← SQLRepairEnv class
│   ├── graders.py         ← deterministic scoring logic
│   ├── models.py          ← Pydantic typed models
│   └── tasks.py           ← task definitions (schema, data, queries)
└── server/
    ├── __init__.py
    └── main.py            ← FastAPI HTTP wrapper
```
