"""
Inference Script — SQL Repair Environment
==========================================

Runs a baseline LLM agent against all three tasks and emits the mandatory
[START] / [STEP] / [END] log lines to stdout.

Environment variables
---------------------
API_BASE_URL   LLM endpoint  (default: https://router.huggingface.co/v1)
MODEL_NAME     Model ID      (default: Qwen/Qwen2.5-72B-Instruct)
HF_TOKEN       HuggingFace / API key
TASK_NAME      Run only this task (default: run all three)

Output format (strict)
----------------------
[START] task=<name> env=sql-repair-env model=<model>
[STEP]  step=<n> action=submit_query('<sql>') reward=<0.00> done=<true|false> error=<msg|null>
[END]   success=<true|false> steps=<n> score=<0.00> rewards=<r1,r2,...>
"""

from __future__ import annotations

import os
import re
import sys
from typing import List, Optional

from openai import OpenAI

from server.sql_repair_env_environment import SQLRepairEnvEnvironment
from models import SQLRepairAction
from tasks import TASK_NAMES

# ---------------------------------------------------------------------------
# Config — match exactly what the problem statement requires
# ---------------------------------------------------------------------------

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or "hf_placeholder"
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")  # reserved for docker-image mode

BENCHMARK = "sql-repair-env"
MAX_STEPS = 10
TEMPERATURE = 0.2
MAX_TOKENS = 512
SOLVED_THRESHOLD = 0.95

# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)


def _build_prompt(obs) -> str:
    parts: List[str] = [
        f"## Task\n{obs.task_description}",
        f"## Database Schema\n{obs.schema_info}",
        f"## Broken Query\n```sql\n{obs.broken_query}\n```",
    ]

    if obs.current_query and obs.current_query != obs.broken_query:
        parts.append(f"## Your Previous Attempt\n```sql\n{obs.current_query}\n```")

    if obs.last_error:
        parts.append(f"## Error from Previous Attempt\n{obs.last_error}")
    elif obs.last_result is not None and obs.reward is not None:
        preview = obs.last_result.preview(max_rows=5)
        parts.append(
            f"## Result from Previous Attempt (score={float(obs.reward):.2f})\n"
            f"{preview}\n\nThe result is INCORRECT. Fix the query."
        )

    parts.append(
        "## Instructions\n"
        "Return ONLY the corrected SQL query. "
        "No markdown fences, no explanation — just raw SQL."
    )
    return "\n\n".join(parts)


def _call_llm(obs) -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert SQL developer. Fix broken SQL queries."},
                {"role": "user",   "content": _build_prompt(obs)},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        raw = (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        sys.stderr.write(f"[LLM ERROR] {exc}\n")
        return obs.broken_query

    # Strip markdown fences if present
    fence = re.search(r"```(?:sql)?\s*([\s\S]+?)\s*```", raw, re.IGNORECASE)
    return fence.group(1).strip() if fence else raw


# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------

def run_episode(task_name: str) -> None:
    env = SQLRepairEnvEnvironment()
    obs = env.reset(task=task_name)

    # Emit [START]
    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    rewards: List[float] = []
    score = 0.0
    step_num = 0

    try:
        for step_num in range(1, MAX_STEPS + 1):
            query = _call_llm(obs)
            # Sanitise for single-line output
            action_repr = "submit_query(" + repr(query[:80].replace("\n", " ")) + ")"

            action = SQLRepairAction(query=query)
            obs = env.step(action)  # direct Python call — correct format

            reward = float(obs.reward) if obs.reward is not None else 0.0
            done = obs.done
            error_str = obs.last_error.replace("\n", " ") if obs.last_error else "null"

            rewards.append(reward)
            score = reward

            # Emit [STEP]  — all on one line, no embedded newlines
            print(
                f"[STEP] step={step_num} action={action_repr} "
                f"reward={reward:.2f} done={str(done).lower()} error={error_str}",
                flush=True,
            )

            if done:
                break

    except Exception as exc:
        sys.stderr.write(f"[EXCEPTION] task={task_name} {exc}\n")
    finally:
        env._obs = None  # cleanup

    success = score >= SOLVED_THRESHOLD
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)

    # Emit [END]
    print(
        f"[END] success={str(success).lower()} steps={step_num} "
        f"score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    task_override = os.getenv("TASK_NAME", "").strip()

    if task_override:
        if task_override not in TASK_NAMES:
            sys.exit(f"Unknown TASK_NAME '{task_override}'. Valid: {', '.join(TASK_NAMES)}")
        run_episode(task_override)
    else:
        for task in TASK_NAMES:
            run_episode(task)


if __name__ == "__main__":
    main()
