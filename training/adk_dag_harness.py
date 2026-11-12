"""Local emulation of the swegemma harness that runs a submission through the REAL Google ADK
agent classes (LoopAgent / SequentialAgent / LlmAgent with include_contents) against vLLM.

Mirrors HARNESS_README.md:
  * sandboxed YAML compiler: `!include` (no absolute paths, no `..`), `sub_agents[*].config_path`,
    single declared model, allowed extensions;
  * session.state = {problem_description}; initial user prompt sections from build_agent_prompt;
  * the 9 tools with the documented names/arguments/JSON results/limits
    (edit_file has exact -> flexible -> regex tiers; graph tools use a local AST call graph);
  * outer loop: break as soon as a final response is emitted with patch_submitted, nudges (max 3),
    tool-call/turn/time budgets from eval_config.yaml;
  * Phase 2: fresh checkout, `git apply`, protected test files restored, pytest exit code decides.

Usage: python3 adk_dag_harness.py <submission_dir> <task_id> [<task_id> ...]
"""

from __future__ import annotations

import asyncio
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import ast
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent  # noqa: E402
from google.adk.models.lite_llm import LiteLlm  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

import real_tasks  # noqa: E402
_BENCH = Path("/content/kaggle_real_bench/bench.json")
# run_17 streaming mode evaluates only the real Kaggle tasks; the synthetic held-out suite
# (held_out_suite.py / extra_tasks.py) lived in the wiped /content and is not needed here.
ALL_TASKS = {tid: {"id": tid, "real": True, "repo": row["repo"], "task": row["problem_statement"]}
             for tid, row in real_tasks.ROWS.items()}


def write_repo(task, dest):  # synthetic-task path, unused in streaming mode
    raise NotImplementedError("synthetic tasks are unavailable in run_17 streaming mode")

WS = Path("/workspace")
OUT = Path(os.environ.get("DEHA_OUT", "/content/run_artifacts/v4_dag"))
API_BASE = os.environ.get("DEHA_API_BASE") or os.environ.get("DEHA_VLLM_BASE", "http://127.0.0.1:8000/v1")  # run_30: DEHA_VLLM_BASE = local vLLM (or capture proxy) without REMOTE semantics
REMOTE = "DEHA_API_BASE" in os.environ
MODEL_OVERRIDE = os.environ.get("DEHA_MODEL")
ALLOWED_MODELS = {"gemma-4-31b-it-qat-w4a16-ct", "gemma-4-12b-it-qat-w4a16-ct",
                  "gemma-4-e4b-it-qat-w4a16-ct", "gemma-4-e2b-it-qat-w4a16-ct"}
ALLOWED_EXT = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
TOOL_NAMES = ["run_command", "submit_patch", "get_status", "read_file", "edit_file", "write_file",
              "get_code_neighbors", "search_similar_code", "get_code_subgraph"]
STDOUT_LIMIT = 5000
PROTECTED = {"conftest.py", "pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg"}


# ----------------------------------------------------------------------------- YAML compiler
class PathTraversalError(Exception):
    pass


def load_yaml(root: Path, rel: str, depth: int = 0, mode: str = "root"):
    """mode='root': !include relative to submission root; mode='file': relative to including file."""
    if depth > 10:
        raise RecursionError("include depth > 10")
    path = _safe(root, rel)
    base = root if mode == "root" else path.parent

    class Loader(yaml.SafeLoader):
        pass

    def include(loader, node):
        target = loader.construct_scalar(node)
        p = _safe(root, str((base / target).relative_to(root)) if mode == "file" else target)
        if p.suffix in (".md", ".txt"):
            return p.read_text(encoding="utf-8")
        return load_yaml(root, str(p.relative_to(root)), depth + 1, mode)

    Loader.add_constructor("!include", include)
    return yaml.load(path.read_text(encoding="utf-8"), Loader=Loader)


def _safe(root: Path, rel: str) -> Path:
    if rel.startswith("/") or "\x00" in rel or ".." in Path(rel).parts:
        raise PathTraversalError(rel)
    p = (root / rel)
    if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
        raise PathTraversalError(rel)
    if not p.exists():
        raise FileNotFoundError(f"{rel} (resolved to {p})")
    return p


SUB_ROOT: Path | None = None  # run_22: skills resolve relative to the submission root


def validate_submission(root: Path) -> dict:
    global SUB_ROOT
    SUB_ROOT = Path(root).resolve()
    files = [p for p in root.rglob("*") if p.is_file()]
    bad_ext = [str(p) for p in files if p.suffix not in ALLOWED_EXT]
    roots = [n for n in ("agent.yaml", "agent.yml", "root_agent.yaml", "root_agent.yml") if (root / n).exists()]
    assert not bad_ext, f"disallowed extensions: {bad_ext}"
    assert len(roots) == 1, f"root configs: {roots}"
    trees = {m: load_tree(root, roots[0], m) for m in ("root", "file")}
    assert json.dumps(trees["root"], sort_keys=True) == json.dumps(trees["file"], sort_keys=True), \
        "include resolution differs between root-relative and file-relative semantics"
    models, tools = set(), {}
    gen_errors, warnings = [], []
    def walk(cfg):
        if cfg.get("model"):
            raw = cfg["model"]
            norm = raw
            for pre in ("openai/", "google/", "hosted_vllm/", "custom/"):  # normalize_model_name
                if norm.startswith(pre):
                    norm = norm[len(pre):]
            if norm != norm.lower():
                warnings.append(f"{cfg.get('name')}: model {raw!r} normalises to {norm!r}; matched case-insensitively "
                                f"against ALLOWED_MODELS ({norm.lower()!r})")
            models.add(norm.lower())
        gc = cfg.get("generate_content_config") or {}
        if cfg.get("agent_class", "LlmAgent") == "LlmAgent" and gc:
            allowed = {"temperature", "top_p", "top_k", "max_output_tokens", "presence_penalty", "frequency_penalty",
                       "stop_sequences", "response_mime_type", "seed", "thinking_config"}
            for k in gc:
                if k not in allowed:
                    gen_errors.append(f"{cfg['name']}: generate_content_config.{k} not allowed")
            mot = gc.get("max_output_tokens", 16384)
            if not (isinstance(mot, int) and 1 <= mot <= 32768):
                gen_errors.append(f"{cfg['name']}: max_output_tokens={mot} outside 1..32768")
            th = gc.get("thinking_config") or {}
            tb = th.get("thinking_budget", 4096)
            if not (isinstance(tb, int) and 0 <= tb <= 32768):
                gen_errors.append(f"{cfg['name']}: thinking_budget={tb} outside 0..32768")
            if isinstance(tb, int) and isinstance(mot, int) and tb > mot:
                gen_errors.append(f"{cfg['name']}: thinking_budget={tb} > max_output_tokens={mot}")
            for k in th:
                if k not in ("thinking_budget", "include_thoughts", "thinking_level"):
                    gen_errors.append(f"{cfg['name']}: thinking_config.{k} not allowed")
        if cfg.get("agent_class", "LlmAgent") == "LlmAgent":
            tools[cfg["name"]] = cfg.get("tools", [])
            for t in cfg.get("tools", []):
                assert t in TOOL_NAMES, f"unknown tool {t}"
        for sub in cfg.get("sub_agents", []):
            walk(sub)
    walk(trees["root"])
    adapters = set()
    def walk_ad(cfg):
        if cfg.get("adapter"):
            adapters.add(cfg["adapter"])
        for sub in cfg.get("sub_agents", []):
            walk_ad(sub)
    walk_ad(trees["root"])
    for a in adapters:
        d = root / "adapters" / a
        assert (d / "adapter_config.json").exists() and (d / "adapter_model.safetensors").exists(), f"adapter {a} missing"
    assert len(models) == 1 and models <= ALLOWED_MODELS, models
    assert not gen_errors, gen_errors
    assert not any(p.is_symlink() for p in root.rglob("*")), "symlink in submission"
    total = sum(p.stat().st_size for p in files)
    assert total < 3 * 1024 ** 3, f"submission too large: {total}"
    return {"root": roots[0], "files": len(files), "models": sorted(models), "tools": tools, "errors": 0,
            "warnings": warnings, "size_bytes": total,
            "include_semantics_identical": True, "adapters": sorted(adapters), "tree": trees["root"]}


def load_tree(root: Path, rel: str, mode: str) -> dict:
    cfg = load_yaml(root, rel, mode=mode)
    subs = []
    for s in cfg.get("sub_agents", []) or []:
        ref = s["config_path"]
        if mode == "file":
            ref = str(((root / rel).parent / ref).relative_to(root))
        subs.append(load_tree(root, ref, mode))
    cfg["sub_agents"] = subs
    return cfg


def _skill_toolsets(cfg: dict) -> list:
    """`skills: [relative dirs]` -> one ADK SkillToolset (load_skill / load_skill_resource / run_skill_script)."""
    paths = cfg.get("skills") or []
    if not paths:
        return []
    from google.adk.skills import load_skill_from_dir
    from google.adk.tools.skill_toolset import SkillToolset
    skills = [load_skill_from_dir(_safe(SUB_ROOT, str(p))) for p in paths]
    return [SkillToolset(skills=skills)]


def compile_agent(cfg: dict, tool_fns: dict):
    cls = cfg.get("agent_class", "LlmAgent")
    if cls == "LoopAgent":
        return LoopAgent(name=cfg["name"], description=cfg.get("description", ""),
                         max_iterations=cfg.get("max_iterations", 500),
                         sub_agents=[compile_agent(s, tool_fns) for s in cfg["sub_agents"]])
    if cls == "SequentialAgent":
        return SequentialAgent(name=cfg["name"], description=cfg.get("description", ""),
                               sub_agents=[compile_agent(s, tool_fns) for s in cfg["sub_agents"]])
    gc = dict(cfg.get("generate_content_config") or {})
    th = gc.pop("thinking_config", None) or {}
    budget = th.get("thinking_budget", 0)
    extra = {"chat_template_kwargs": {"enable_thinking": budget > 0}}
    if budget > 0:
        extra["thinking_token_budget"] = budget
    if REMOTE:  # vLLM-only knobs; a hosted API rejects them
        extra = {"reasoning_effort": "low"}
    served = MODEL_OVERRIDE or cfg.get("adapter") or cfg["model"]  # resolve_swegemma_adapter: adapter agents -> openai/<adapter_name>
    api_key = os.environ.get("DEHA_API_KEY", "EMPTY")
    model = LiteLlm(model=f"openai/{served}", api_base=API_BASE, api_key=api_key, extra_body=extra, num_retries=3)
    BUDGETS[cfg["name"]] = {"thinking_token_budget": extra.get("thinking_token_budget"),
                            "max_output_tokens": gc.get("max_output_tokens")}
    # run_22: LlmAgent.sub_agents (multi-agent transfer), output_key and transfer flags, as in HARNESS_README §2.3
    kw = {k: cfg[k] for k in ("output_key", "disallow_transfer_to_parent", "disallow_transfer_to_peers")
          if cfg.get(k) is not None}
    return LlmAgent(name=cfg["name"], description=cfg.get("description", ""), model=model,
                    instruction=cfg.get("instruction", ""), include_contents=cfg.get("include_contents", "default"),
                    generate_content_config=types.GenerateContentConfig(**gc),
                    tools=[tool_fns[t] for t in cfg.get("tools", [])] + _skill_toolsets(cfg),
                    sub_agents=[compile_agent(s, tool_fns) for s in cfg.get("sub_agents", []) or []],
                    before_model_callback=_context_guard, after_model_callback=_usage_probe, **kw)


# ----------------------------------------------------------------------------- run_30: context guard + telemetry
MAX_MODEL_LEN = int(os.environ.get("DEHA_MAX_MODEL_LEN", "32768"))
TOKEN_THRESHOLD = 14336      # EventsCompactionConfig.token_threshold (HARNESS_README §7.2)
EVENT_RETENTION = 5          # EventsCompactionConfig.event_retention_size
BUDGETS: dict = {}
_TOK = None


def _tokenizer():
    global _TOK
    if _TOK is None:
        try:
            from transformers import AutoTokenizer
            _TOK = AutoTokenizer.from_pretrained("google/gemma-4-E4B-it-qat-w4a16-ct")
        except Exception:  # noqa: BLE001 - fall back to a char heuristic
            _TOK = False
    return _TOK


def count_tokens(text: str) -> int:
    tok = _tokenizer()
    if tok:
        return len(tok(text, add_special_tokens=False)["input_ids"])
    return int(len(text) / 3.2) + 1


def _part_text(p) -> str:
    if p.text:
        return p.text
    if p.function_call:
        return p.function_call.name + json.dumps(dict(p.function_call.args or {}), default=str)
    if p.function_response:
        return p.function_response.name + json.dumps(p.function_response.response or {}, default=str)
    return ""


def _req_tokens(llm_request) -> int:
    sys_i = llm_request.config.system_instruction if llm_request.config else None
    txt = sys_i if isinstance(sys_i, str) else (
        "".join(_part_text(p) for p in (sys_i.parts or [])) if sys_i is not None and hasattr(sys_i, "parts") else "")
    body = "\n".join(_part_text(p) for c in (llm_request.contents or []) for p in (c.parts or []))
    tools = json.dumps([t.model_dump(exclude_none=True) for t in (llm_request.config.tools or [])], default=str) \
        if llm_request.config and llm_request.config.tools else ""
    n_msgs = len(llm_request.contents or [])
    return count_tokens(txt + body + tools) + 8 * n_msgs  # + chat-template overhead per turn


def _context_guard(callback_context, llm_request):
    """Kaggle runs EventsCompactionConfig(token_threshold=14336, event_retention_size=5) on the App, but ADK only
    compacts *after* an invocation; a single DAG invocation can still grow past 32K. Mirror that policy inside the
    invocation: once the prompt crosses token_threshold, older tool outputs / thoughts (all but the last 5 contents)
    are replaced by short stubs. The final safety net clamps max_output_tokens so prompt+completion <= max_model_len
    (logged, never silent)."""
    if CTX is None:
        return None
    agent = callback_context.agent_name
    before = _req_tokens(llm_request)
    pruned = 0
    est = before
    contents = llm_request.contents or []
    if est > TOKEN_THRESHOLD and len(contents) > EVENT_RETENTION:
        for c in contents[:-EVENT_RETENTION]:
            new_parts = []
            for p in c.parts or []:
                if p.thought and p.text:
                    pruned += 1
                    continue  # old reasoning is not needed for the next tool call
                if p.function_response:
                    raw = json.dumps(p.function_response.response or {}, default=str)
                    if len(raw) > 600:
                        # ADK shallow-copies Parts: the FunctionResponse object is shared with the session event, so
                        # never mutate it in place - build a new Part (request-only change, session history intact)
                        p = types.Part(function_response=p.function_response.model_copy(update={"response": {
                            "result": json.dumps({"status": "pruned",
                                                  "note": f"older tool output pruned by context guard ({len(raw)} chars)",
                                                  "head": raw[:400]})}}))
                        pruned += 1
                new_parts.append(p)
            c.parts = new_parts or [types.Part(text="(pruned)")]
        est = _req_tokens(llm_request)
    cfg_mot = llm_request.config.max_output_tokens if llm_request.config else None
    clamp = None
    if cfg_mot and est + cfg_mot + 512 > MAX_MODEL_LEN:
        clamp = MAX_MODEL_LEN - est - 512
        if clamp < 1:
            raise ValueError(f"Context limit exhausted: estimated input={est}")
        llm_request.config.max_output_tokens = clamp
    CTX.guard.append({"t": round(time.time() - CTX.t0, 1), "agent": agent, "prompt_est": before, "after_prune": est,
                      "pruned_parts": pruned, "max_out_cfg": cfg_mot, "max_out_clamped": clamp})
    return None


def _usage_probe(callback_context, llm_response):
    if CTX is None:
        return None
    u = llm_response.usage_metadata
    thought_txt = "".join(p.text for p in ((llm_response.content.parts if llm_response.content else None) or [])
                          if p.thought and p.text)
    rec = {"t": round(time.time() - CTX.t0, 1), "agent": callback_context.agent_name,
           "prompt_tokens": getattr(u, "prompt_token_count", None) if u else None,
           "completion_tokens": getattr(u, "candidates_token_count", None) if u else None,
           "thoughts_tokens": getattr(u, "thoughts_token_count", None) if u else None,
           "thought_chars": len(thought_txt),
           "finish_reason": str(llm_response.finish_reason) if llm_response.finish_reason else None,
           "error": llm_response.error_code}
    CTX.llm_calls.append(rec)
    CTX.last_finish = rec["finish_reason"]
    return None


# ----------------------------------------------------------------------------- tools
class Ctx:
    def __init__(self, max_tool_calls, max_minutes, cmd_timeout):
        self.max_tool_calls, self.max_minutes, self.cmd_timeout = max_tool_calls, max_minutes, cmd_timeout
        self.tool_calls = 0
        self.t0 = time.time()
        self.patch_submitted = False
        self.patch = ""
        self.exhausted = False
        self.trace = []
        self.edit_errors = 0
        self.graph = None
        self.path = "/usr/local/bin:/usr/bin:/bin"
        self.guard, self.llm_calls, self.last_finish = [], [], None

    def remaining_s(self):
        return self.max_minutes * 60 - (time.time() - self.t0)


CTX: Ctx | None = None


def _ok(**kw):
    return _wrap({"status": "ok", **kw})


def _err(t, msg, **details):
    return _wrap({"status": "error", "error_type": t, "error_message": msg, "details": details})


def _wrap(d):
    used, mx = CTX.tool_calls, CTX.max_tool_calls
    if mx >= 20 and mx - used <= 10:
        d["budget_warning"] = (f"Only {mx - used} tool call(s) remaining ({used}/{mx} used). "
                               "Finalize your edits and call submit_patch soon.")
    return json.dumps(d)


def _gate(count=True):
    if CTX.remaining_s() <= 0:
        CTX.exhausted = True
        return _err("BudgetExceeded", "time budget exhausted")
    if count:
        if CTX.tool_calls >= CTX.max_tool_calls:
            CTX.exhausted = True
            return _err("BudgetExceeded", "tool call budget exhausted")
        CTX.tool_calls += 1
    return None


def _path(fp: str) -> Path:
    fp = str(fp)
    for pre in ("/workspace/", "/"):
        if fp.startswith(pre):
            fp = fp[len(pre):]
    if ".." in Path(fp).parts:
        raise ValueError("path traversal")
    return WS / fp


def run_command(command: str) -> str:
    """Execute a shell command with /bin/bash -c inside /workspace. stdout/stderr truncated to 5000 chars."""
    if (g := _gate()):
        return g
    try:
        r = subprocess.run(["/bin/bash", "-c", command], cwd=WS, capture_output=True, text=True,
                           timeout=min(CTX.cmd_timeout, max(5, int(CTX.remaining_s()))),
                           env={**os.environ, "PATH": CTX.path, "PYTHONDONTWRITEBYTECODE": "1"})
    except subprocess.TimeoutExpired:
        return _err("TimeoutExceeded", "command timed out")
    out, err = r.stdout[:STDOUT_LIMIT], r.stderr[:STDOUT_LIMIT]
    if r.returncode == 0:
        return _ok(stdout=out, stderr=err, exit_code=0)
    return _err("CommandError", f"exit code {r.returncode}", stdout=out, stderr=err, exit_code=r.returncode)


def submit_patch() -> str:
    """Submit the current git diff of /workspace as the final patch. Ends the session after this turn."""
    if (g := _gate(count=False)):
        return g
    subprocess.run(["git", "add", "-N", "."], cwd=WS, capture_output=True)
    diff = subprocess.run(["git", "diff", "--binary", "HEAD"], cwd=WS, capture_output=True, text=True).stdout
    CTX.patch, CTX.patch_submitted = diff, True
    return _ok(patch_size=len(diff), files_changed=diff.count("diff --git"))


def get_status() -> str:
    """Return live budget consumption and patch status."""
    return json.dumps({"status": "ok", "tool_calls_used": CTX.tool_calls, "patch_submitted": CTX.patch_submitted,
                       "patch_size": len(CTX.patch), "tool_calls_remaining": CTX.max_tool_calls - CTX.tool_calls,
                       "max_tool_calls": CTX.max_tool_calls, "time_seconds_remaining": round(CTX.remaining_s(), 1),
                       "max_time_minutes": CTX.max_minutes})


def read_file(filepath: str, start_line: int | None = None, end_line: int | None = None) -> str:
    """Read a file in /workspace (1-indexed inclusive lines). At most 150 lines and 10000 characters per call."""
    if (g := _gate()):
        return g
    try:
        p = _path(filepath)
        lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    except Exception as e:  # noqa: BLE001
        return _err(type(e).__name__, str(e))
    s = max(1, int(start_line or 1))
    e = min(len(lines), int(end_line or len(lines)))
    out, n, trunc = [], s, False
    while n <= e:
        if len(out) >= 150 or sum(map(len, out)) + len(lines[n - 1]) > 10000:
            trunc = True
            break
        out.append(lines[n - 1])
        n += 1
    return _ok(filepath=filepath, content="".join(out), start_line=s, end_line=n - 1,
               total_lines=len(lines), is_truncated=trunc or (end_line is None and n - 1 < len(lines)))


def _flex(text: str, old: str, new: str):
    tl, ol = text.split("\n"), old.strip("\n").split("\n")
    os_ = [x.strip() for x in ol]
    hits = [i for i in range(len(tl) - len(ol) + 1) if [x.strip() for x in tl[i:i + len(ol)]] == os_]
    return hits, tl, ol


def edit_file(filepath: str, old_string: str, new_string: str, allow_multiple: bool = False) -> str:
    """Replace old_string with new_string in an existing file (exact, then whitespace-flexible, then regex match)."""
    if (g := _gate()):
        return g
    try:
        p = _path(filepath)
        if not p.exists() or p.stat().st_size == 0:
            raise FileNotFoundError(f"{filepath} does not exist or is empty")
        if not old_string:
            raise ValueError("old_string is empty")
        text = p.read_text(encoding="utf-8").replace("\r\n", "\n")
        old, new = old_string.replace("\r\n", "\n"), new_string.replace("\r\n", "\n")
        allow_multiple = str(allow_multiple).lower() == "true"
        result, strategy, occ = None, None, 0
        occ = text.count(old)
        if occ:
            if occ > 1 and not allow_multiple:
                raise ValueError(f"old_string matches {occ} occurrences; set allow_multiple or add context")
            result, strategy = text.replace(old, new), "exact"
        else:
            hits, tl, ol = _flex(text, old, new)
            if hits:
                if len(hits) > 1 and not allow_multiple:
                    raise ValueError(f"old_string matches {len(hits)} occurrences (flexible)")
                i = hits[0]
                indent = re.match(r"\s*", tl[i]).group()
                nl = new.strip("\n").split("\n")
                base = min((len(x) - len(x.lstrip()) for x in nl if x.strip()), default=0)
                nl = [indent + x[base:] if x.strip() else "" for x in nl]
                tl[i:i + len(ol)] = nl
                result, strategy, occ = "\n".join(tl), "flexible", len(hits)
            else:
                toks = [t for t in re.split(r"([()\[\]{}:>=<])|\s+", old.strip()) if t]
                rx = r"\s*".join(re.escape(t) for t in toks)
                ms = list(re.finditer(rx, text))
                if not ms:
                    raise ValueError("old_string not found in file (exact, flexible and regex tiers failed)")
                if len(ms) > 1 and not allow_multiple:
                    raise ValueError(f"old_string matches {len(ms)} occurrences (regex)")
                m = ms[0]
                result, strategy, occ = text[:m.start()] + new + text[m.end():], "regex", len(ms)
        p.write_text(result, encoding="utf-8")
        diff = "".join(difflib.unified_diff(text.splitlines(True), result.splitlines(True),
                                            f"a/{filepath}", f"b/{filepath}"))
        return _ok(filepath=filepath, occurrences=occ, strategy=strategy, diff=diff[:STDOUT_LIMIT],
                   is_truncated=len(diff) > STDOUT_LIMIT)
    except Exception as e:  # noqa: BLE001
        CTX.edit_errors += 1
        return _err("FileEditError", str(e))


def write_file(filepath: str, content: str) -> str:
    """Create or overwrite a file in /workspace, creating parent directories."""
    if (g := _gate()):
        return g
    p = _path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return _ok(filepath=filepath, size=len(content))


def _build_graph():
    if CTX.graph is not None:
        return CTX.graph
    CTX.graph = _build_graph_uncached()
    return CTX.graph


def _build_graph_uncached():
    nodes, calls = {}, {}
    for f in sorted(WS.rglob("*.py")):
        if ".git" in f.parts:
            continue
        mod = ".".join(f.relative_to(WS).with_suffix("").parts)
        try:
            src = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue

        def visit(node, prefix):
            for ch in ast.iter_child_nodes(node):
                if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    name = f"{prefix}.{ch.name}"
                    nodes[name] = ast.get_source_segment(src, ch) or ""
                    calls[name] = {(c.func.id if isinstance(c.func, ast.Name) else c.func.attr)
                                   for c in ast.walk(ch) if isinstance(c, ast.Call)
                                   and isinstance(c.func, (ast.Name, ast.Attribute))}
                    visit(ch, name)
        visit(tree, mod)
    by_short = {}
    for b in nodes:
        by_short.setdefault(b.split(".")[-1], []).append(b)
    edges = [(a, b) for a, cs in calls.items() for c in cs for b in by_short.get(c, []) if b != a]
    return nodes, edges


def _resolve(name: str, nodes):
    name = str(name).strip()
    for test in (lambda n: n == name, lambda n: n.endswith("." + name),
                 lambda n: n.lower() == name.lower() or n.lower().endswith("." + name.lower()),
                 lambda n: name.lower() in n.lower()):
        hit = [n for n in nodes if test(n)]
        if hit:
            return hit[0]
    return None


def search_similar_code(query: str, k: int = 10) -> str:
    """Find functions/classes similar to a symbol name (e.g. pkg.module.Class.method) or keyword query."""
    if (g := _gate()):
        return g
    nodes, _ = _build_graph()
    k = int(k)
    toks = set(re.findall(r"[a-z0-9]+", str(query).lower()))
    hit = _resolve(query, nodes)
    def score(n):
        nt = set(re.findall(r"[a-z0-9]+", (n + " " + nodes[n][:400]).lower()))
        return len(toks & nt) / (len(toks) or 1)
    ranked = sorted(nodes, key=lambda n: (n != hit, -score(n)))[:k]
    per, res, trunc = STDOUT_LIMIT // max(1, len(ranked)), [], False
    for n in ranked:
        code = nodes[n]
        trunc |= len(code) > per
        res.append({"node_name": n, "code": code[:per], "similarity": 1.0 if n == hit else round(score(n), 4)})
    return _ok(query=query, results=res, count=len(res), is_truncated=trunc)


def get_code_neighbors(node: str, edge_type: str | None = None, max_neighbors: int = 50) -> str:
    """Find callers and callees of a symbol node in the repository call graph."""
    if (g := _gate()):
        return g
    nodes, edges = _build_graph()
    n = _resolve(node, nodes)
    if not n:
        return _err("NodeNotFound", f"symbol {node!r} not found")
    nb = sorted({b for a, b in edges if a == n} | {a for a, b in edges if b == n})[:int(max_neighbors)]
    return _ok(node=n, neighbors=nb, count=len(nb), is_truncated=False)


def get_code_subgraph(nodes: list[str]) -> str:
    """Get the induced call subgraph connecting a list of symbol nodes."""
    if (g := _gate()):
        return g
    allnodes, edges = _build_graph()
    if isinstance(nodes, str):
        try:
            nodes = json.loads(nodes)
        except json.JSONDecodeError:
            nodes = [x.strip() for x in nodes.split(",")]
    res = [r for r in (_resolve(x, allnodes) for x in nodes) if r]
    sub = [{"from": a, "to": b, "type": "calls"} for a, b in edges if a in res and b in res]
    return _ok(nodes=res, edges=sub, node_count=len(res), edge_count=len(sub), is_truncated=False)


TOOL_FNS = {f.__name__: f for f in (run_command, submit_patch, get_status, read_file, edit_file, write_file,
                                    get_code_neighbors, search_similar_code, get_code_subgraph)}


# ----------------------------------------------------------------------------- prompt + runner
def _first_model(cfg):
    if cfg.get("model"):
        return cfg["model"]
    for s in cfg.get("sub_agents", []) or []:
        m = _first_model(s)
        if m:
            return m
    return None


def build_prompt(task, ev, declared):
    layout = subprocess.run("find . -mindepth 1 -maxdepth 3 -not -path './.git*' | sort | head -200",
                            shell=True, cwd=WS, capture_output=True, text=True).stdout
    parts = [f"You are evaluating a software engineering task for repository {task.get('repo', 'local/' + task['id'])}.\n\n"
             f"Problem Statement:\n{task['task']}",
             f"## Task Budget (Session terminates when any budget is exhausted)\n- Time allowance: "
             f"{ev['max_time_minutes']} minutes\n- Tool calls allowance: {ev['max_tool_calls']} calls\n"
             f"- Max loop iterations: {ev['max_turns']} turns",
             "## Execution Environment Rules\n- Single command timeout: "
             f"{ev['timeout_seconds']} seconds (commands exceeding this fail without ending the session)\n"
             "- Command output limit: 5000 characters\n- File view limit: 150 lines per read_file call\n"
             "- File character limit: 10000 characters per read_file call\n- Environment is offline (no network/"
             "PyPI access). All repository and test dependencies are ALREADY pre-installed. Do NOT attempt to run "
             "pip install or download packages.",
             "## Instructions\n0. Work strictly under /workspace.\n1. Inspect the existing code and conventions.\n"
             "2. Implement the fix.\n3. Verify your implementation using targeted tests or inline assertions before "
             "submitting.\n4. Call submit_patch once complete.\n5. Return a final text completion response."]
    graph = [t for t in ("search_similar_code", "get_code_neighbors", "get_code_subgraph") if t in declared]
    if graph:
        parts.append("## Code Intelligence Tools\nThis repository has pre-built code graph and embedding data "
                     "indexed by dotted symbol path (e.g. `pkg.module.Class.method`). Use these tools for fast, "
                     "targeted navigation:\n" + "\n".join(f"- `{t}`" for t in graph))
    parts.append(f"## Workspace Layout\n{layout}")
    return "\n\n".join(parts)


NUDGE_MAXTOK = ("Your previous response reached the token limit while thinking before a tool call was completed. "
                "Do NOT repeat your analysis in thought\u2014keep reasoning under a few sentences and emit your next tool "
                "call immediately, or call submit_patch when you have completed and verified your changes.")
NUDGE = ("Please continue your work using the available tools, or call submit_patch when you have completed "
         "and verified your changes.")


async def run_task(sub: Path, task: dict, ev: dict, info: dict) -> dict:
    global CTX
    CTX = Ctx(ev["max_tool_calls"], ev["max_time_minutes"], ev["timeout_seconds"])
    for f in Path("/tmp").glob("deha_*"):
        f.unlink()
    if task.get("real"):
        real_tasks.setup_workspace(task["id"], WS)
        CTX.path = f"{real_tasks.venv_bin(task['id'].split('_')[0])}:/usr/local/bin:/usr/bin:/bin"
        CTX.t0 = time.time()  # container setup is excluded from the agent time budget
    else:
        if WS.exists():
            shutil.rmtree(WS)
        write_repo(task, WS)
    root = compile_agent(info["tree"], TOOL_FNS)
    declared = {t for ts in info["tools"].values() for t in ts}
    svc = InMemorySessionService()
    sess = await svc.create_session(app_name="swegemma_eval", user_id="eval_user",
                                    state={"problem_description": task["task"]})
    from google.adk.apps.app import App, EventsCompactionConfig
    from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
    summ_llm = LiteLlm(model=f"openai/{MODEL_OVERRIDE or _first_model(info['tree'])}", api_base=API_BASE,
                       api_key=os.environ.get("DEHA_API_KEY", "EMPTY"),
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}}, num_retries=3)
    app = App(name="swegemma_eval", root_agent=root, events_compaction_config=EventsCompactionConfig(
        compaction_interval=15, overlap_size=2, token_threshold=TOKEN_THRESHOLD, event_retention_size=EVENT_RETENTION,
        summarizer=LlmEventSummarizer(llm=summ_llm)))
    runner = Runner(app=app, session_service=svc)
    msg, turns, nudges, consecutive, error = build_prompt(task, ev, declared), 0, 0, 0, None
    while True:
        had_tool = False
        try:
            async for evt in runner.run_async(user_id="eval_user", session_id=sess.id,
                                              new_message=types.Content(role="user", parts=[types.Part(text=msg)])):
                rec = {"t": round(time.time() - CTX.t0, 1), "author": evt.author}
                if evt.content and evt.content.parts:
                    for p in evt.content.parts:
                        if p.function_call:
                            had_tool = True
                            rec.setdefault("calls", []).append(
                                {"name": p.function_call.name, "args": {k: v for k, v in
                                                                        (p.function_call.args or {}).items()}})
                        elif p.function_response:
                            r = p.function_response.response or {}
                            rr = r.get("result", r)
                            try:
                                rr = json.loads(rr) if isinstance(rr, str) else rr
                            except json.JSONDecodeError:
                                pass
                            st = rr.get("status") if isinstance(rr, dict) else None
                            rec.setdefault("responses", []).append({"name": p.function_response.name, "status": st,
                                "detail": (json.dumps(rr)[:400] if st != "ok" else ""),
                                "output": json.dumps(rr)})  # run_25: full tool output for trajectory export
                        elif p.text and p.thought:
                            rec["thought"] = rec.get("thought", "") + p.text
                        elif p.text and not p.thought:
                            rec["text"] = p.text.strip()
                    if evt.content.role == "model" or evt.author != "user":
                        if any(p.function_call or (p.text and not p.thought) for p in evt.content.parts):
                            turns += 1
                CTX.trace.append(rec)
                fault = os.environ.get("DEHA_FAULT")  # "<agent_name>:<file>": undo that agent's edit in iteration 1
                if fault and evt.is_final_response() and evt.author == fault.split(":")[0] \
                        and Path("/tmp/deha_iter").exists() and Path("/tmp/deha_iter").read_text().strip() == "1":
                    target = fault.split(":")[1]
                    if target == "TASKB":
                        try:
                            tj = json.loads(Path("/tmp/deha_isolated_tasks.json").read_text())
                            target = next(t["file"] for t in tj if str(t.get("id")).upper().endswith("B"))
                        except Exception:  # noqa: BLE001
                            target = "."
                    fault = fault.split(":")[0] + ":" + target
                    subprocess.run(["git", "checkout", "--", target], cwd=WS, capture_output=True)
                    CTX.trace.append({"t": rec["t"], "author": "HARNESS", "text": "FAULT INJECTED: reverted " + fault})
                if evt.is_final_response() and CTX.patch_submitted:
                    break
                if CTX.exhausted or turns >= ev["max_turns"]:
                    break
        except Exception as e:  # noqa: BLE001
            error = f"{type(e).__name__}: {str(e)[:300]}"
            CTX.trace.append({"t": round(time.time() - CTX.t0, 1), "author": "HARNESS", "text": "EXC " + error})
        if CTX.patch_submitted or CTX.exhausted or turns >= ev["max_turns"] or CTX.remaining_s() <= 0:
            break
        consecutive = 0 if had_tool else consecutive + 1
        if consecutive > 3:
            break
        nudges += 1
        lf = (CTX.last_finish or "").upper()
        msg = NUDGE_MAXTOK if ("MAX_TOKENS" in lf or "LENGTH" in lf) else NUDGE
        CTX.trace.append({"t": round(time.time() - CTX.t0, 1), "author": "HARNESS", "text": "NUDGE"})
    patch = CTX.patch
    if not CTX.patch_submitted:  # what a non-submitting session would leave behind
        subprocess.run(["git", "add", "-N", "."], cwd=WS, capture_output=True)
        patch = subprocess.run(["git", "diff", "--binary", "HEAD"], cwd=WS, capture_output=True, text=True).stdout
    if task.get("real"):
        b = json.loads(_BENCH.read_text())[task["id"]]
        verdict, resolved, _ = real_tasks.verify_patch(task["id"], WS, patch, b["FAIL_TO_PASS"])
    else:
        verdict, resolved = verify(task, patch)
    flow = []
    for r in CTX.trace:
        a = r["author"]
        if a not in ("user",) and (not flow or flow[-1] != a):
            flow.append(a)
    tmp_left = sorted(str(p) for p in Path("/tmp").glob("deha_*"))
    return dict(task=task["id"], submitted=CTX.patch_submitted, resolved=resolved, verdict=verdict,
                turns=turns, tool_calls=CTX.tool_calls, edit_errors=CTX.edit_errors, nudges=nudges,
                wall_s=round(time.time() - CTX.t0, 1), error=error, flow=flow,
                iterations=int((Path("/tmp/deha_iter").read_text().strip() or 0)) if Path("/tmp/deha_iter").exists() else 0,
                untracked_in_patch=[l for l in patch.splitlines() if l.startswith("new file mode")],
                tmp_files=tmp_left, patch=patch, trace=CTX.trace, llm_calls=CTX.llm_calls, context_guard=CTX.guard,
                budgets=BUDGETS)


def verify(task, patch):
    vdir = Path("/content/verify_work") / task["id"]
    write_repo(task, vdir)
    if not patch.strip():
        return "empty patch", False
    (vdir.parent / f"{task['id']}.patch").write_text(patch)
    r = subprocess.run(["git", "apply", "--whitespace=nowarn", str(vdir.parent / f"{task['id']}.patch")],
                       cwd=vdir, capture_output=True, text=True)
    if r.returncode != 0:
        return "apply failed: " + r.stderr[:200], False
    for path, text in task["files"].items():  # anti-tampering: restore tests / protected config
        if Path(path).name.startswith("test_") or Path(path).name in PROTECTED:
            (vdir / path).write_text(text, encoding="utf-8")
    for path, text in task.get("hidden_tests", {}).items():
        (vdir / path).write_text(text, encoding="utf-8")
    r = subprocess.run(["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=vdir,
                       capture_output=True, text=True)
    return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:], r.returncode == 0


async def main():
    sub = Path(sys.argv[1]).resolve()
    info = validate_submission(sub)
    ev = {"timeout_seconds": 300, "max_tool_calls": 100, "max_time_minutes": 60, "max_turns": 500}
    if (sub / "eval_config.yaml").exists():
        ev.update(yaml.safe_load((sub / "eval_config.yaml").read_text())["evaluation"])
    print("[validate]", json.dumps({k: v for k, v in info.items() if k != "tree"}), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for tid in sys.argv[2:]:
        res = await run_task(sub, ALL_TASKS[tid], ev, info)
        (OUT / f"{tid}.json").write_text(json.dumps(res, indent=1))
        results.append(res)
        print(f"[dag] {tid}: submitted={res['submitted']} resolved={res['resolved']} iters={res['iterations']} "
              f"turns={res['turns']} tool_calls={res['tool_calls']} edit_errors={res['edit_errors']} "
              f"nudges={res['nudges']} wall={res['wall_s']}s verdict={res['verdict']!r} err={res['error']}\n"
              f"      flow={' -> '.join(res['flow'])}", flush=True)
    summ = [{k: v for k, v in r.items() if k not in ("trace", "patch")} for r in results]
    (OUT / "summary.json").write_text(json.dumps(summ, indent=1))
    print(f"[dag] resolved {sum(r['resolved'] for r in results)}/{len(results)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
