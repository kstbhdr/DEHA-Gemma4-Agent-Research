#!/usr/bin/env python3
"""run_17 bench20 — STREAMING orchestrator (prepare -> run -> write to Drive immediately).

Lesson from the previous crash: nothing reached Drive until the whole batch was done, so the Colab
recycle erased hours of work. This loop therefore treats Drive as the only durable store and commits
after *every single task*, before starting the next one:

  1. resume   — skip any task whose results/<task_id>.json is already on Drive;
  2. prepare  — one repo at a time, in a private mount namespace, plus a pre-flight gate that checks
                the declared FAIL_TO_PASS tests really fail at base_commit (else -> INVALID_ENV);
  3. agent    — the v5 surgical submission driven by the real Google ADK classes against vLLM;
  4. commit   — <task_id>.json + task_logs/<task_id>.log + SUMMARY.md + HEARTBEAT.txt to Drive, os.sync();
  5. cleanup  — drop /tmp/work_<task_id> and /workspace so the local disk never fills up.

Usage: python3 run_streaming_bench20.py [--only ID[,ID]] [--limit N] [--dry]
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

DRIVE = Path("/content/drive/MyDrive/DEHA-Gemma4-Agent-Competition")
RUN_NAME = "run_17_bench20_v5"
RUN = DRIVE / "logs" / RUN_NAME
RESULTS = RUN / "results"
TASKLOGS = RUN / "task_logs"
IDS_FILE = DRIVE / "kaggle_bench_20_ids.json"
SUMMARY = RUN / "SUMMARY.md"
HEARTBEAT = RUN / "HEARTBEAT.txt"

SUB = "/content/submission_swegemma_v5_surgical"
TOOLS = "/content/bench_tools"
LOCAL = Path(f"/content/{RUN_NAME}_local")
BENCH = json.loads(Path("/content/kaggle_real_bench/bench.json").read_text())
ROWS = {json.loads(l)["instance_id"]: json.loads(l) for l in open("/content/kaggle_data/tasks.jsonl")}


def set_run(run_name: str, sub: str) -> None:
    """Point every path at another run/submission pair (run_17 v5, run_18 v6, ...)."""
    global RUN_NAME, RUN, RESULTS, TASKLOGS, SUMMARY, HEARTBEAT, SUB, LOCAL
    RUN_NAME = run_name
    RUN = DRIVE / "logs" / run_name
    RESULTS = RUN / "results"
    TASKLOGS = RUN / "task_logs"
    SUMMARY = RUN / "SUMMARY.md"
    HEARTBEAT = RUN / "HEARTBEAT.txt"
    SUB = sub
    LOCAL = Path(f"/content/{run_name}_local")


VLLM_LOG = "/content/vllm_run17.log"
VLLM_CMD = ["vllm", "serve", "google/gemma-4-E4B-it-qat-w4a16-ct",
            "--served-model-name", "gemma-4-e4b-it-qat-w4a16-ct",
            "--tool-call-parser", "gemma4", "--reasoning-parser", "gemma4", "--enable-auto-tool-choice",
            "--enable-prefix-caching", "--enable-chunked-prefill", "--gpu-memory-utilization", "0.90",
            "--max-model-len", "32768", "--limit-mm-per-prompt", '{"image":0,"audio":0}',
            "--port", "8000", "--host", "127.0.0.1"]
TASK_TIMEOUT = 2400
PROTECTED = {"conftest.py", "pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg"}
T0 = time.time()
_vllm_proc: subprocess.Popen | None = None


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    with open(LOCAL / "orchestrator.log", "a") as f:
        f.write(line + "\n")


# --------------------------------------------------------------------------- durable Drive writes
def _drive_put(dst: Path, data: bytes) -> None:
    """Write through a local staging file, then rename into Drive and flush to the mount."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    staging = LOCAL / "drive_stage"
    staging.mkdir(parents=True, exist_ok=True)
    tmp = staging / dst.name
    tmp.write_bytes(data)
    os.sync()
    shutil.copyfile(tmp, str(dst) + ".part")
    os.replace(str(dst) + ".part", dst)
    os.sync()


def drive_json(dst: Path, obj) -> None:
    _drive_put(dst, json.dumps(obj, indent=1).encode())


def drive_text(dst: Path, text: str) -> None:
    _drive_put(dst, text.encode())


def done_ids() -> set[str]:
    return {p.stem for p in RESULTS.glob("*.json")} if RESULTS.exists() else set()


def load_result(tid: str) -> dict:
    p = RESULTS / f"{tid}.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {"task": tid, "status": "CORRUPT_RESULT"}


# --------------------------------------------------------------------------- error taxonomy
def _patch_files(patch: str) -> list[str]:
    files = re.findall(r"(?m)^diff --git a/(\S+) b/\S+", patch or "")
    if not files:
        files = re.findall(r"(?m)^\+\+\+ b/(\S+)", patch or "")
    return sorted(set(files))


def _is_test(path: str) -> bool:
    p = Path(path)
    return (p.name.startswith("test_") or p.name.endswith("_test.py")
            or bool({"tests", "test", "testing"} & set(p.parts)))


def _src_files(files: list[str]) -> set[str]:
    return {f for f in files if not _is_test(f) and p_name(f) not in PROTECTED}


def p_name(f: str) -> str:
    return Path(f).name


def classify(res: dict, ev: dict) -> str:
    """Evidence-based bucket: resolved, or one of the five failure modes from the run plan."""
    status = res.get("status")
    if status:
        return status
    if res.get("resolved"):
        return "Çözüldü"
    verdict = str(res.get("verdict") or "")
    tail = " ".join(map(str, res.get("tail") or [])) + verdict
    submitted = bool(res.get("submitted"))
    turns, calls = int(res.get("turns") or 0), int(res.get("tool_calls") or 0)
    if "empty patch" in verdict or (submitted and not _patch_files(res.get("patch", ""))):
        return "Erken Submit"
    if not submitted and (turns >= ev.get("max_turns", 36) or calls >= ev.get("max_tool_calls", 48)
                          or "BudgetExceeded" in json.dumps(res.get("trace") or [])[-4000:]):
        return "Tur Limiti"
    if ("Failed to apply" in verdict or verdict.startswith("exit=2") or verdict.startswith("exit=-")
            or re.search(r"\b\d+ errors?\b", tail) or res.get("error")):
        return "Syntax/Import Hatası"
    tid = res.get("task", "")
    gold = _src_files(_patch_files(ROWS.get(tid, {}).get("patch", "")))
    agent = _src_files(_patch_files(res.get("patch", "")))
    if agent and gold and not (agent & gold):
        return "Yanlış Dosya"
    return "Yanlış Mantık"


TAXONOMY = ["Çözüldü", "Yanlış Dosya", "Erken Submit", "Syntax/Import Hatası", "Yanlış Mantık", "Tur Limiti"]

NOTES = """## Notlar (2026-11-07 streaming oturumu)

- **Resume:** 10 görevin sonucu önceki oturumdan Drive'da duruyordu (9 + `requests_7205` smoke testi),
  10 görev bu oturumda koşuldu. Hiçbir görev iki kez koşturulmadı.
- **fastapi ortam düzeltmesi:** PyPI-latest `starlette` (1.10.0) eski commit'lerde
  `Router.__init__() got an unexpected keyword argument 'on_startup'` toplama hatası veriyordu; ayrıca
  `python-multipart` (extras) ve `inline-snapshot` (PEP 735 `test` grubu) eksikti. Bu yüzden 3 fastapi
  görevi yanlışlıkla `INVALID_ENV` almıştı. `real_tasks.install_commit_deps()` artık her görev için
  **o commit'in kendi pinlerini** kuruyor (`[project.dependencies]` + `optional-dependencies` +
  `dependency-groups.test`) ve pin seti başına cache'leniyor. Üç görev düzeltilmiş ortamla yeniden
  koşuldu; düzeltme öncesi kayıtlar `results_invalid_env_pre_deppin/` altında kanıt olarak duruyor.
- **Doğrulanan ayrım:** `rich_3468` ve önceki oturumun `fastapi_13920` / `fastapi_14258` sonuçlarındaki
  `exit=2` **ortam kaynaklı değil** — base preflight temiz geçiyor ve bu görevlerin test dosyaları eksik
  olabilecek hiçbir modül import etmiyor. Hata ajanın kendi patch'inden (syntax/import) geliyor,
  bu yüzden taksonomide `Syntax/Import Hatası` / `Tur Limiti` olarak bırakıldılar.
- **Ortam sadakati:** git-clone tabanlı hazırlık, Drive'daki `validation/*.json` kayıtlarıyla birebir
  aynı `base_tail` değerlerini üretiyor (ör. `requests_7205`: `1 failed, 205 passed, 13 skipped`;
  `rich_3468`: `1 failed, 97 passed`), yani snapshot'sız yeniden kurulum ölçütü kaydırmıyor.
- **Kaggle:** `~/.kaggle/kaggle.json` yok → `58059842` referanslı v5 gönderiminin skoru bu oturumdan
  sorgulanamadı.
"""


def notes_text() -> str:
    """Per-run notes live next to the results on Drive, so each run documents its own caveats."""
    p = RUN / "NOTES.md"
    if p.exists():
        try:
            return p.read_text()
        except OSError:
            pass
    return NOTES if RUN_NAME == "run_17_bench20_v5" else ""


def eval_config() -> dict:
    import yaml
    ev = {"timeout_seconds": 300, "max_tool_calls": 100, "max_time_minutes": 60, "max_turns": 500}
    p = Path(SUB) / "eval_config.yaml"
    if p.exists():
        ev.update(yaml.safe_load(p.read_text())["evaluation"])
    return ev


# --------------------------------------------------------------------------- reporting
def localization(res: dict) -> str:
    """How many of the gold source files the agent actually touched (the real file-localization metric).

    The taxonomy bucket "Yanlış Dosya" only fires when the two sets are disjoint, so an empty patch after
    the protected-file strip shows up as "Erken Submit" instead; this column measures localization directly.
    """
    if res.get("status"):
        return "—"
    tid = res.get("task", "")
    gold = _src_files(_patch_files(ROWS.get(tid, {}).get("patch", "")))
    agent = _src_files(_patch_files(res.get("patch", "")))
    if not gold:
        return "—"
    if not agent:
        return f"0/{len(gold)} (yama boş)"
    return f"{len(agent & gold)}/{len(gold)}"


def build_summary(ids: list[str]) -> str:
    ev = eval_config()
    rows, buckets = [], {k: 0 for k in TAXONOMY}
    other: dict[str, int] = {}
    resolved_n = finished = loc_hit = loc_tot = 0
    for tid in ids:
        res = load_result(tid)
        spec = BENCH.get(tid, {})
        if not res:
            rows.append(f"| {tid} | {spec.get('repo','?')} | {spec.get('difficulty','?')} | "
                        f"{len(spec.get('FAIL_TO_PASS',[]))} | — | — | — | — | — | — | PENDING |")
            continue
        finished += 1
        bucket = classify(res, ev)
        if bucket in buckets:
            buckets[bucket] += 1
        else:
            other[bucket] = other.get(bucket, 0) + 1
        resolved_n += bool(res.get("resolved"))
        loc = localization(res)
        if "/" in loc:
            hit, tot = loc.split(" ")[0].split("/")
            loc_tot += 1
            loc_hit += int(hit) > 0
        rows.append(
            f"| {tid} | {spec.get('repo','?')} | {spec.get('difficulty','?')} | "
            f"{len(spec.get('FAIL_TO_PASS',[]))} | {'YES' if res.get('resolved') else 'no'} | "
            f"{res.get('submitted')} | {res.get('tool_calls','—')} | {res.get('turns','—')} | "
            f"{res.get('wall_s','—')} | {loc} | "
            f"{bucket} :: {str(res.get('verdict') or res.get('error') or '')[:90]} |")
    tax = "  |  ".join(f"{k}: {v}" for k, v in buckets.items() if v) or "—"
    if other:
        tax += "  |  " + "  ".join(f"{k}: {v}" for k, v in other.items())
    elapsed = int(time.time() - T0)
    loc_line = f"{loc_hit}/{loc_tot}" if loc_tot else "—"
    return (f"# {RUN_NAME} bench20 — live summary\n\n"
            f"updated: {now()}  |  **{resolved_n}/{len(ids)} resolved**  |  {finished}/{len(ids)} tasks finished"
            f"  |  dosya lokalizasyonu (gold kaynak dosyaya dokunan görev): {loc_line}"
            f"  |  orchestrator uptime {elapsed}s\n\n"
            f"model: google/gemma-4-E4B-it-qat-w4a16-ct (vLLM 0.33.0, CUDA graphs + prefix caching + "
            f"chunked prefill, gpu_mem_util 0.90, max_model_len 32768)\n"
            f"submission: {SUB}  |  eval_config: {ev['max_tool_calls']} tool calls / {ev['max_turns']} turns / "
            f"{ev['max_time_minutes']} min / cmd timeout {ev['timeout_seconds']}s\n"
            f"streaming: her görev biter bitmez `results/<task_id>.json` + `task_logs/<task_id>.log` + bu tablo "
            f"Drive'a yazılıp `os.sync()` çağrılır (resume: Drive'da sonucu olan görev atlanır)\n\n"
            f"| task | repo | diff | F2P | resolved | submitted | calls | turns | wall_s | src∩gold | verdict |\n"
            f"|---|---|---|---|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
            f"## Hata Taksonomisi\n\n{tax}\n\n"
            f"`src∩gold` = ajanın değiştirdiği (test/korunaklı olmayan) kaynak dosyalar ∩ gold patch'in kaynak "
            f"dosyaları. `Yanlış Dosya` kovası yalnızca bu iki küme **hiç** kesişmediğinde dolar; yaması "
            f"strip'ten sonra boşalan görev `Erken Submit` sayılır, bu yüzden lokalizasyon bu sütundan okunur.\n\n"
            f"{notes_text()}")


def write_reports(ids: list[str]) -> None:
    resolved = sum(bool(load_result(t).get("resolved")) for t in ids)
    finished = len(done_ids() & set(ids))
    drive_text(SUMMARY, build_summary(ids))
    drive_text(HEARTBEAT,
               f"HEARTBEAT — {RUN_NAME} (streaming{' resume' if finished else ''})\n"
               f"written_at: {now()}\n"
               f"drive_writable: YES (os.sync after every task)\n"
               f"submission: {SUB}\n"
               f"progress: {finished}/{len(ids)} finished  |  {resolved}/{len(ids)} resolved\n"
               f"orchestrator_uptime_s: {int(time.time() - T0)}\n"
               f"pending: {[t for t in ids if t not in done_ids()]}\n")


# --------------------------------------------------------------------------- vLLM supervision
def vllm_healthy(timeout: float = 5.0) -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=timeout) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def wait_vllm(seconds: int = 900) -> bool:
    t0 = time.time()
    while time.time() - t0 < seconds:
        if vllm_healthy():
            log(f"vLLM healthy after {int(time.time() - t0)}s")
            return True
        time.sleep(10)
    return False


def restart_vllm() -> bool:
    global _vllm_proc
    log("vLLM unreachable — restarting server")
    subprocess.run("pkill -f 'vllm serve' || true", shell=True)
    time.sleep(10)
    with open(VLLM_LOG, "a") as lf:
        _vllm_proc = subprocess.Popen(VLLM_CMD, stdout=lf, stderr=subprocess.STDOUT, cwd="/content")
    return wait_vllm(900)


# --------------------------------------------------------------------------- one task
def run_one(tid: str) -> dict:
    """Prepare + run a single task inside its own mount namespace; returns the result dict."""
    work = Path(f"/tmp/work_{tid}")
    out = LOCAL / tid
    for p in (work / "workspace", work / "tmp", out):
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
        p.mkdir(parents=True, exist_ok=True)
    Path("/workspace").mkdir(parents=True, exist_ok=True)
    inner = (f"mount --bind {work}/workspace /workspace && mount --bind {work}/tmp /tmp && "
             f"cd {TOOLS} && exec env DEHA_OUT={out} PYTHONUNBUFFERED=1 "
             f"python3 -u task_runner.py {tid} {SUB}")
    cmd = ["unshare", "-m", "--propagation", "private", "/bin/bash", "-c", inner]
    log(f"RUN {tid} :: {json.dumps({'$': 'unshare -m ... task_runner.py ' + tid})}")
    t0 = time.time()
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TASK_TIMEOUT)
        rc, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        rc, timed_out = -9, True
        stdout = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = (e.stderr or b"").decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
    wall = round(time.time() - t0, 1)
    logtext = (f"$ {' '.join(cmd)}\n{stdout}\n--- stderr ---\n{stderr[-4000:]}\n"
               f"--- rc={rc} wall={wall}s timed_out={timed_out} ---\n")

    res = {}
    if (out / f"{tid}.json").exists():
        res = json.loads((out / f"{tid}.json").read_text())
    elif (out / "preflight.json").exists() and (rc == 2 or timed_out is False):
        pf = json.loads((out / "preflight.json").read_text())
        if not pf.get("ok"):
            res = {"task": tid, "status": "INVALID_ENV", "resolved": False, "submitted": False,
                   "preflight": pf, "verdict": f"INVALID_ENV: {pf.get('reason') or pf.get('error')}",
                   "wall_s": wall, "harness_rc": rc}
    if not res:
        res = {"task": tid, "status": "TIMEOUT" if timed_out else "RUNNER_ERROR", "resolved": False,
               "submitted": False, "verdict": (stderr or stdout)[-800:], "wall_s": wall, "harness_rc": rc}
    res.setdefault("task", tid)
    res["harness_rc"] = rc
    res["run_elapsed_s"] = wall
    res["streamed_to_drive_at"] = now()
    drive_json(RESULTS / f"{tid}.json", res)
    drive_text(TASKLOGS / f"{tid}.log", logtext)
    log(f"DONE {tid}: resolved={res.get('resolved')} status={res.get('status','-')} "
        f"calls={res.get('tool_calls','-')} turns={res.get('turns','-')} wall={wall}s "
        f"-> Drive results/{tid}.json")
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree("/workspace", ignore_errors=True)
    Path("/workspace").mkdir(parents=True, exist_ok=True)
    return res


def argval(flag: str, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def write_run_meta(ids: list[str]) -> None:
    """Record once per run what produced these results, so a cold session can tell v5 from v6 apart."""
    p = RUN / "RUN_META.json"
    if p.exists():
        return
    ev = eval_config()
    files = sorted(f for f in Path(SUB).rglob("*") if f.is_file())
    sha = hashlib.sha1("".join(
        hashlib.sha1(f.read_bytes()).hexdigest() + str(f) for f in files).encode()).hexdigest() if files else "?"
    drive_json(p, {
        "run": RUN_NAME,
        "started": now(),
        "submission": SUB,
        "submission_sha1": sha,
        "submission_files": [str(f.relative_to(SUB)) for f in files],
        "model": "google/gemma-4-E4B-it-qat-w4a16-ct",
        "vllm": "0.33.0 CUDA graphs + prefix caching + chunked prefill, gpu_mem_util 0.90, max_model_len 32768",
        "eval_config": ev,
        "tasks": ids,
        "isolation": "unshare -m: private /workspace and /tmp per task (bind mounts)",
        "env_prep": "GitHub mirror + base_commit checkout + per-commit dependency pins (real_tasks.py)",
        "code": f"logs/{RUN_NAME}/code/ (see also logs/run_17_bench20_v5/RESUME.md)",
    })


def main() -> int:
    set_run(argval("--run", RUN_NAME), argval("--sub", SUB))
    ids = json.loads(IDS_FILE.read_text())["task_ids"]
    if "--tasks" in sys.argv:  # explicit order, e.g. run_18: the 15 tasks v5 lost first, then the 5 it solved
        want = [t.strip() for t in str(argval("--tasks")).split(",") if t.strip()]
        unknown = [t for t in want if t not in ids]
        if unknown:
            log(f"UYARI: bench20 listesinde olmayan görevler atlandı: {unknown}")
        ids = [t for t in want if t in ids]
    if "--only" in sys.argv:
        ids = [t for t in str(argval("--only")).split(",") if t in ids]
    if "--limit" in sys.argv:
        ids = ids[:int(argval("--limit"))]
    RESULTS.mkdir(parents=True, exist_ok=True)
    TASKLOGS.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    write_run_meta(ids)

    have = done_ids()
    log(f"=== {RUN_NAME} STREAMING bench20 === sub={SUB} | {len(ids)} tasks, "
        f"{len(have & set(ids))} already on Drive (resume)")
    for tid in ids:
        if tid in have:
            log(f"SKIP {tid} (result already on Drive)")
    write_reports(ids)

    if "--dry" in sys.argv:
        log("dry run — nothing executed")
        return 0

    if not vllm_healthy():
        if not wait_vllm(900):
            log("FATAL: vLLM never became healthy; aborting so results already on Drive stay valid")
            return 1

    for i, tid in enumerate(ids, 1):
        if tid in done_ids():
            continue
        log(f"--- task {i}/{len(ids)}: {tid} ---")
        if not vllm_healthy() and not restart_vllm():
            res = {"task": tid, "status": "VLLM_DOWN", "resolved": False, "submitted": False,
                   "verdict": "vLLM server could not be restarted"}
            drive_json(RESULTS / f"{tid}.json", res)
            write_reports(ids)
            log(f"FATAL: vLLM down at {tid}; stopping loop (progress is safe on Drive)")
            return 1
        try:
            run_one(tid)
        except Exception as e:  # noqa: BLE001 - one bad task must not kill the remaining ones
            log(f"ERROR {tid}: {type(e).__name__}: {e}")
            drive_json(RESULTS / f"{tid}.json",
                       {"task": tid, "status": "RUNNER_ERROR", "resolved": False, "submitted": False,
                        "verdict": f"{type(e).__name__}: {e}"})
        write_reports(ids)

    results = [load_result(t) for t in ids]
    resolved = sum(bool(r.get("resolved")) for r in results)
    log(f"=== COMPLETE: {resolved} / {len(ids)} resolved ===")
    print(build_summary(ids), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
