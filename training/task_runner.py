#!/usr/bin/env python3
"""One bench task, end to end: environment pre-flight gate, then the real ADK agent run.

Invoked by run_streaming_bench20.py inside a private mount namespace where
/tmp/work_<task>/workspace is bind-mounted to /workspace and /tmp/work_<task>/tmp to /tmp, so a task
can neither see nor pollute its neighbours. Results are written to $DEHA_OUT (on /content, i.e. outside
the namespace) so the orchestrator can push them to Drive the moment the process exits.

Exit codes: 0 = agent run completed, 2 = INVALID_ENV (pre-flight gate failed), 1 = unexpected error.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import yaml  # noqa: E402

import real_tasks  # noqa: E402

WS = Path("/workspace")
PREFLIGHT_KEYS = ("ok", "stage", "reason", "base_exit", "base_tail", "collected", "declared",
                  "failed_at_base", "missing", "error", "cmd", "preflight_s")


def main() -> int:
    tid = sys.argv[1]
    sub = Path(sys.argv[2]).resolve()
    out = Path(os.environ.get("DEHA_OUT", f"/content/run17_local/{tid}"))
    out.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    pf = real_tasks.preflight(tid, WS)
    pf["preflight_s"] = round(time.time() - t0, 1)
    (out / "preflight.json").write_text(json.dumps(pf, indent=1))
    print("[preflight] " + json.dumps({k: pf.get(k) for k in PREFLIGHT_KEYS}, default=str), flush=True)
    if not pf.get("ok"):
        print(f"[INVALID_ENV] {tid}: {pf.get('reason') or pf.get('error')}", flush=True)
        return 2

    import adk_dag_harness as H

    info = H.validate_submission(sub)
    print("[validate] " + json.dumps({k: v for k, v in info.items() if k != "tree"}), flush=True)
    ev = {"timeout_seconds": 300, "max_tool_calls": 100, "max_time_minutes": 60, "max_turns": 500}
    if (sub / "eval_config.yaml").exists():
        ev.update(yaml.safe_load((sub / "eval_config.yaml").read_text())["evaluation"])

    t1 = time.time()
    res = asyncio.run(H.run_task(sub, H.ALL_TASKS[tid], ev, info))
    res["preflight"] = {k: pf.get(k) for k in ("ok", "base_exit", "base_tail", "collected",
                                               "failed_at_base", "preflight_s")}
    res["eval_config"] = ev
    res["agent_s"] = round(time.time() - t1, 1)
    (out / f"{tid}.json").write_text(json.dumps(res, indent=1))
    print(f"[dag] {tid}: submitted={res['submitted']} resolved={res['resolved']} turns={res['turns']} "
          f"tool_calls={res['tool_calls']} edit_errors={res['edit_errors']} nudges={res['nudges']} "
          f"wall={res['wall_s']}s verdict={res['verdict']!r} err={res['error']}\n"
          f"      flow={' -> '.join(res['flow'])}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001 - always leave a machine-readable trace for the orchestrator
        out = Path(os.environ.get("DEHA_OUT", "/content/run17_local"))
        out.mkdir(parents=True, exist_ok=True)
        tid = sys.argv[1] if len(sys.argv) > 1 else "unknown"
        (out / f"{tid}.error.json").write_text(json.dumps(
            {"task": tid, "status": "RUNNER_ERROR", "error": f"{type(e).__name__}: {e}"}, indent=1))
        print(f"[RUNNER_ERROR] {tid}: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
