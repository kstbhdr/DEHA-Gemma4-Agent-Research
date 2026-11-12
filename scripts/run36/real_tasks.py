"""Real Kaggle tasks (tasks.jsonl) for the local harness — run_17 STREAMING edition.

Same public API as the run_11 original (setup_workspace / venv_bin / verify_patch / ROWS / strip_protected)
but the offline `snapshots/*.tgz` + `/wheels` cache is gone with the previous /content, so:

  * repos are cloned from GitHub into a local mirror cache (/content/repo_cache) and checked out at
    `base_commit`, then hardlink-cloned per task (fast, no repeated network fetches);
  * dependencies come from PyPI (network is available here, unlike the offline sandbox) into one
    venv per repo, cached across tasks;
  * `sandbox/setup.py` from kaggle_data is still what writes git-exclude rules, pytest.ini,
    conftest.py and workspace_paths.pth, so the workspace layout matches the real evaluation.

Container B semantics are unchanged: fresh setup -> strip protected files from the agent patch ->
4-pass apply -> reset test files -> apply test_patch -> pytest with JUnit XML -> resolved iff exit 0,
something passed, nothing failed and every FAIL_TO_PASS node passed.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

DATA = Path("/content/work_l4_resume/kaggle_data")
BENCH_DIR = Path("/content/work_l4_resume/kaggle_real_bench")
CACHE = Path("/content/work_l4_resume/repo_cache")
VENVS = BENCH_DIR / "venvs"
ROWS = {json.loads(l)["instance_id"]: json.loads(l) for l in open(DATA / "tasks.jsonl")}
BENCH = json.loads((BENCH_DIR / "bench.json").read_text()) if (BENCH_DIR / "bench.json").exists() else {}
LAST_DEPS = ""  # set by setup_workspace: which commit-pin set was applied to the shared venv

EXTRA = {"requests": ["urllib3", "idna", "charset_normalizer", "certifi"],
         "rich": ["pygments", "markdown_it_py", "mdurl", "ipywidgets"],
         "httpx": ["h11", "httpcore", "certifi", "idna", "sniffio", "anyio", "pytest-asyncio",
                   "cryptography", "trustme", "uvicorn", "flask", "wsproto"],
         "fastapi": ["starlette", "pydantic", "pydantic_core", "typing_extensions", "annotated_types", "anyio",
                     "sniffio", "idna", "httpx", "httpcore", "certifi", "sqlmodel", "sqlalchemy", "jinja2",
                     "markupsafe", "typer", "click", "rich", "pygments", "markdown_it_py", "mdutil", "packaging",
                     "flask", "werkzeug", "itsdangerous", "pytest-asyncio", "orjson", "ujson", "email-validator",
                     "python-multipart", "pyyaml", "inline-snapshot", "dirty-equals"]}
PROTECTED_NAMES = {"conftest.py", "pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg", ".pytest.ini",
                   "sitecustomize.py", "usercustomize.py", "_swegemma_stubs.py"}


def sh(cmd, cwd=None, timeout=1800, env=None):
    return subprocess.run(cmd, shell=isinstance(cmd, str), cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, env=env)


def repo_short(repo: str) -> str:
    return repo.split("/")[-1]


ACTIVE_VENV: dict[str, Path] = {}  # repo short name -> venv currently prepared for the task in flight


def venv_bin(repo: str) -> Path:
    """Bin dir of the venv belonging to the task currently set up.

    The venv is keyed by the commit's dependency-pin set (see ensure_venv), so callers that only know the
    repo name - the harness sets CTX.path from venv_bin(repo) - must get the one setup_workspace activated.
    """
    s = repo_short(repo)
    return (ACTIVE_VENV[s] / "bin") if s in ACTIVE_VENV else (VENVS / s / "bin")


def ensure_mirror(repo: str) -> Path:
    """Local full clone of the upstream repo, reused by every task of that repo."""
    m = CACHE / repo.replace("/", "__")
    if not (m / ".git").exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        r = sh(f"git clone --quiet https://github.com/{repo}.git {m}", timeout=2400)
        if r.returncode:
            raise RuntimeError(f"mirror clone failed for {repo}: {r.stderr[-400:]}")
        sh("git config gc.auto 0", cwd=m)
    return m


def pin_key(deps: list[str]) -> str:
    return hashlib.sha1("|".join(sorted(deps)).encode()).hexdigest()[:12] if deps else "base"


def ensure_venv(repo: str, key: str = "base") -> Path:
    """One venv per (repo, dependency-pin set).

    A single shared per-repo venv is wrong: commits pin incompatible test stacks (requests_6644 pins
    pytest<=6.2.5 while its neighbours pin pytest>=3), so each task downgraded what the previous one had
    installed and pytest plugins raised AssertionError at collection time. Keying the venv by the pin set
    makes every task's environment self-consistent and still cached across tasks that share the pins.
    """
    v = VENVS / f"{repo_short(repo)}__{key}"
    if not (v / "bin" / "python").exists():
        VENVS.mkdir(parents=True, exist_ok=True)
        sh(f"uv venv --seed --python 3.13 {v}", timeout=600)
        sh(f"{v}/bin/python -m pip install -q pytest pytest-timeout==2.1.0 typer pdm-backend setuptools wheel "
           f"poetry-core hatchling flit-core editables", timeout=1200)
        site = sh(f"{v}/bin/python -c 'import site;print(site.getsitepackages()[0])'").stdout.strip()
        for f in ("imp.py", "telnetlib.py"):
            src = DATA / "docker" / f
            if site and src.exists():
                shutil.copy(src, Path(site) / f)
    marker = v / ".extra_deps"
    if not marker.exists():
        extra = EXTRA.get(repo_short(repo), [])
        r = sh(f"{v}/bin/python -m pip install -q {' '.join(extra)}", timeout=1800) if extra else None
        marker.write_text(f"rc={r.returncode if r else 'skipped'}\n" + (r.stderr[-500:] if r and r.returncode else ""))
    ACTIVE_VENV[repo_short(repo)] = v
    return v


def _clean_req(line: str) -> str:
    """Keep the version specifier (unlike sandbox/setup.py, which strips it); drop comments and markers."""
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("-"):
        return ""
    return re.split(r";", line)[0].strip()


def commit_deps(ws: Path) -> list[str]:
    """Dependency constraints the repo itself declares at this exact commit."""
    deps: list[str] = []
    pp = ws / "pyproject.toml"
    if pp.exists():
        try:
            data = tomllib.loads(pp.read_text(encoding="utf-8"))
            proj = data.get("project") or {}
            deps += [c for c in map(_clean_req, proj.get("dependencies") or []) if c]
            # extras too: that is where fastapi keeps python-multipart / email-validator, and without them
            # whole test modules die at collection time (looks like an invalid env, is not)
            for group in (proj.get("optional-dependencies") or {}).values():
                deps += [c for c in map(_clean_req, group or []) if c]
            # PEP 735 test group: fastapi's newer commits declare inline-snapshot / pytest-* there
            deps += [c for c in map(_clean_req, (data.get("dependency-groups") or {}).get("test") or []) if c]
        except Exception:  # noqa: BLE001 - unparsable pyproject just means no pins
            pass
    for name in ("requirements.txt", "requirements-dev.txt", "test-requirements.txt"):
        rf = ws / name
        if rf.exists():
            try:
                deps += [c for c in map(_clean_req, rf.read_text(encoding="utf-8").splitlines())
                         if c and not c.startswith("#")]
            except OSError:
                pass
    return deps


def apply_commit_deps(v: Path, deps: list[str], key: str) -> str:
    """Install the commit's own pins into its dedicated venv.

    The venv is already keyed by this pin set, so one marker per venv is enough and no task can ever
    downgrade another task's pytest / starlette / httpcore behind its back.
    """
    if not deps:
        return "no-pins"
    marker = v / ".commit_deps"
    if marker.exists():
        return f"cached:{key}"
    r = sh(f"{v}/bin/python -m pip install -q {' '.join(shlex.quote(d) for d in deps)}", timeout=1800)
    marker.write_text(f"rc={r.returncode}\n" + (r.stderr[-800:] if r.returncode else ""))
    return f"installed:{key}:rc={r.returncode}"


def _drop_dead_symlinks(ws: Path) -> None:
    for root, dirs, files in os.walk(ws, followlinks=False):
        if ".git" in dirs:
            dirs.remove(".git")
        for name in dirs + files:
            p = Path(root) / name
            try:
                if p.is_symlink() and not p.exists():
                    p.unlink()
            except OSError:
                pass


def _clear(ws: Path) -> None:
    """Empty the workspace. /workspace is a bind-mount point inside the per-task namespace, and a mount
    point cannot be rmdir'd (EBUSY) — in that case only its contents are removed."""
    if ws.exists():
        try:
            shutil.rmtree(ws)
        except OSError:
            for child in ws.iterdir():
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    try:
                        child.unlink()
                    except OSError:
                        pass
    ws.mkdir(parents=True, exist_ok=True)


def setup_workspace(task_id: str, ws: Path) -> None:
    """Per-repo lock (run_24 parallel): shared mirror / venv preparation of one repo is serialised;
    different repos and the agent runs themselves proceed in parallel."""
    repo = ROWS[task_id]["repo"]
    with open(f"/content/work_l4_resume/.lock_{repo_short(repo)}", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _setup_workspace_locked(task_id, ws)


def _setup_workspace_locked(task_id: str, ws: Path) -> None:
    """Fresh container setup: clone at base_commit + sandbox/setup.py + eval_baseline commit."""
    row = ROWS[task_id]
    repo, commit = row["repo"], row["base_commit"]
    mirror = ensure_mirror(repo)
    _clear(ws)
    ws.parent.mkdir(parents=True, exist_ok=True)
    r = sh(f"git clone --quiet --shared --no-checkout {mirror} {ws}", timeout=1200)
    if r.returncode:
        raise RuntimeError(f"work clone failed: {r.stderr[-400:]}")
    r = sh(f"git checkout --quiet --detach {commit}", cwd=ws, timeout=600)
    if r.returncode:
        raise RuntimeError(f"base_commit {commit[:12]} not in upstream history: {r.stderr[-300:]}")
    _drop_dead_symlinks(ws)
    deps = commit_deps(ws)
    key = pin_key(deps)
    v = ensure_venv(repo, key)
    global LAST_DEPS
    LAST_DEPS = apply_commit_deps(v, deps, key)
    r = sh([str(v / "bin" / "python"), str(DATA / "sandbox" / "setup.py"), repo_short(repo),
            "--workspace", str(ws)], cwd=ws, timeout=1200)
    if r.returncode:
        raise RuntimeError("setup.py failed: " + (r.stderr or r.stdout)[-500:])
    # editable install is best-effort: workspace_paths.pth from setup.py already makes the repo importable
    sh(f"{v}/bin/python -m pip install -q --no-build-isolation --no-deps -e {ws}", cwd=ws, timeout=900)
    sh(f"{v}/bin/python {DATA / 'sandbox' / 'setup.py'} {repo_short(repo)} --workspace {ws}", cwd=ws, timeout=600)
    sh("git add -A && git -c user.email=agent@eval -c user.name=Agent commit -q -m eval_baseline --allow-empty",
       cwd=ws, timeout=600)


def test_targets(task_id: str) -> list[str]:
    return sorted(set(re.findall(r"^\+\+\+ b/(\S+)", ROWS[task_id]["test_patch"], re.M)))


def _is_protected(path: str) -> bool:
    p = Path(path)
    return (p.name in PROTECTED_NAMES or p.suffix == ".pth" or p.name.startswith("test_")
            or p.name.endswith("_test.py") or (p.suffix == ".py" and bool({"tests", "test", "testing"} & set(p.parts))))


def strip_protected(patch: str) -> str:
    chunks = re.split(r"(?m)^(?=diff --git )", patch)
    keep = []
    for c in chunks:
        m = re.match(r"diff --git a/(\S+) b/(\S+)", c)
        if m and (_is_protected(m.group(2)) or _is_protected(m.group(1))):
            continue
        keep.append(c)
    return "".join(keep)


def patch_files(patch: str) -> list[str]:
    return sorted({m for m in re.findall(r"(?m)^diff --git a/(\S+) b/\S+", patch)})


def apply_patch(ws: Path, patch: str) -> tuple[bool, str]:
    pf = ws.parent / f".{ws.name}.agent.patch"
    pf.write_text(patch.rstrip("\n") + "\n")
    r = None
    for cmd in (f"git apply --unsafe-paths -p1 {pf}", f"git apply -3 {pf}",
                f"git apply --ignore-space-change --ignore-whitespace {pf}", f"git apply --recount {pf}",
                f"git apply --unsafe-paths -p0 {pf}", f"patch -p1 --batch --forward < {pf}"):
        r = sh(cmd, cwd=ws)
        if r.returncode == 0:
            return True, cmd
    return False, (r.stderr if r else "no apply strategy ran")[-300:]


def pytest_cmd(task_id: str, junit: Path) -> str:
    """The README/bench test command with a JUnit sink injected (needed for per-node FAIL_TO_PASS checks)."""
    spec = BENCH.get(task_id, {})
    cmd = spec.get("test_command")
    if not cmd:
        cmd = f"python3 -s -m pytest {' '.join(test_targets(task_id))} -p no:anyio -o timeout=0 " \
              f"-o python_classes='Test* *Test' -q"
    cmd = re.sub(r"--junitxml(?:=|\s+)\S+", f"--junitxml={junit}", cmd)
    if "--junitxml" not in cmd:
        cmd = cmd.replace(" -m pytest ", f" -m pytest --junitxml={junit} ", 1)
    return cmd


def run_tests(task_id: str, ws: Path, tag: str) -> dict:
    """Reset protected/test files, apply test_patch, run the bench pytest command with JUnit XML."""
    repo = repo_short(ROWS[task_id]["repo"])
    targets = test_targets(task_id)
    files_to_reset = " ".join(targets)
    sh(f"git ls-tree -r -z --name-only HEAD -- {files_to_reset} | xargs -0 -r git checkout HEAD -- ; "
       f"git clean -f -- {files_to_reset}", cwd=ws, timeout=300)
    tp = ws.parent / f".{ws.name}.test.patch"
    tp.write_text(ROWS[task_id]["test_patch"].rstrip("\n") + "\n")  # tasks.jsonl patches lack the final newline
    r = sh(f"git apply {tp} || git apply --recount {tp} || patch -p1 --batch --forward < {tp}", cwd=ws, timeout=300)
    if r.returncode:
        return {"exit": -1, "error": "test_patch apply failed: " + r.stderr[-200:]}
    junit = Path(f"/tmp/_swegemma_junit_{task_id}_{tag}.xml")
    junit.unlink(missing_ok=True)
    env = {"PATH": f"{venv_bin(ROWS[task_id]['repo'])}:/usr/local/bin:/usr/bin:/bin", "PYTHONSAFEPATH": "1",
           "PYTHONNOUSERSITE": "1", "HOME": "/root", "TEST_TMPDIR": "/tmp", "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        r = sh(pytest_cmd(task_id, junit), cwd=ws, timeout=600, env=env)
    except subprocess.TimeoutExpired:
        return {"exit": -2, "error": "pytest timeout 600s"}
    res = {"exit": r.returncode,
           "tail": r.stdout.strip().splitlines()[-1:] if r.stdout.strip() else [r.stderr[-300:]],
           "cmd": pytest_cmd(task_id, junit)}
    tests = {}
    if junit.exists():
        try:
            for tc in ET.parse(junit).getroot().iter("testcase"):
                name = f"{tc.get('classname')}::{tc.get('name')}"
                st = "passed"
                for child in tc:
                    if child.tag in ("failure", "error"):
                        st = "failed"
                    elif child.tag == "skipped":
                        st = "skipped"
                tests[name] = st
        except ET.ParseError as e:
            res["error"] = f"junit parse error: {e}"
    res["tests"] = tests
    return res


def resolved(task_id: str, res: dict, required: list[str]) -> bool:
    t = res.get("tests", {})
    return (res.get("exit") == 0 and sum(v == "passed" for v in t.values()) > 0
            and not any(v == "failed" for v in t.values()) and all(t.get(n) == "passed" for n in required))


def required_nodes(task_id: str) -> list[str]:
    return list(BENCH.get(task_id, {}).get("FAIL_TO_PASS", []))


def preflight(task_id: str, ws: Path) -> dict:
    """Base-commit sanity gate: env must build and the declared FAIL_TO_PASS tests must actually fail."""
    out: dict = {"task": task_id, "ok": False, "stage": "setup"}
    try:
        setup_workspace(task_id, ws)
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {str(e)[:400]}"
        return out
    out["stage"] = "base_tests"
    required = required_nodes(task_id)
    try:
        res = run_tests(task_id, ws, "base")
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {str(e)[:400]}"
        return out
    t = res.get("tests", {})
    out.update({"base_exit": res.get("exit"), "base_tail": res.get("tail"), "collected": len(t),
                "failed_at_base": sorted(n for n, s in t.items() if s == "failed"),
                "declared": required, "cmd": res.get("cmd"), "error": res.get("error"),
                "commit_deps": LAST_DEPS})
    if res.get("exit") == -1:
        out["reason"] = "test_patch apply failed"
    elif not t:
        out["reason"] = "no tests collected (broken env / missing deps)"
    elif required and not any(t.get(n) == "failed" for n in required):
        out["reason"] = "declared FAIL_TO_PASS did not fail at base_commit"
    elif required and any(n not in t for n in required):
        out["missing"] = [n for n in required if n not in t]
        out["reason"] = "declared FAIL_TO_PASS node ids not produced by the test run"
    else:
        out["ok"] = True
    return out


def verify_patch(task_id: str, ws: Path, patch: str, required: list[str]) -> tuple[str, bool, dict]:
    """Container B: fresh setup, protected strip, apply, test_patch, junit check."""
    setup_workspace(task_id, ws)
    agent = strip_protected(patch)
    if not agent.strip():
        return "empty patch (after protected-file strip)", False, {"applied_files": patch_files(patch)}
    ok, how = apply_patch(ws, agent)
    if not ok:
        return "Failed to apply agent patch: " + how, False, {}
    res = run_tests(task_id, ws, "verify")
    t = res.get("tests", {})
    f2p_pass = sum(t.get(n) == "passed" for n in required)
    res["applied_files"] = patch_files(agent)
    verdict = f"exit={res.get('exit')} required {f2p_pass}/{len(required)} passed; {res.get('tail') or res.get('error')}"
    return verdict, resolved(task_id, res, required), res
