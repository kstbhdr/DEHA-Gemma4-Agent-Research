"""BASE_HIGHTHINK_REPORT.md: run_30 (8K/12K) vs run_21 + run_28A (4096) per task + thinking-token stats per agent."""
import json, statistics, sys, datetime
from pathlib import Path
sys.path.insert(0, "/content/eval_highthink/bench_tools"); sys.argv = ["x"]
from adk_dag_harness import count_tokens
L = Path("/content/drive/MyDrive/DEHA-Gemma4-Agent-Competition/logs")
RUNS = {"run_21_bench20_v5_8": "run21 (4096)", "run_28A_base_control_v5": "run28A (4096)", "run_30_base_highthink": "run30 (8K/12K)",
        "run_31_feedback_fix": "run31 (8K/12K + geri bildirim düzeltmesi)"}
IDS = ["requests_7205", "requests_6644", "requests_7309", "requests_7315", "fastapi_14301", "fastapi_14616", "rich_3454",
       "rich_3518", "fastapi_14964", "rich_3468", "rich_3506", "rich_3718", "rich_3882", "rich_3052", "fastapi_14356",
       "fastapi_14791", "fastapi_14482", "fastapi_13920", "fastapi_14258", "httpx_3672"]
SHORT = {"deha_planner_and_conflict_guard": "planner", "deha_isolated_coder_a": "coder_a",
         "deha_isolated_coder_b_and_merger": "coder_b", "deha_qa_smoke_and_feedback": "qa_judge"}
sys.path.insert(0, "/content/eval_highthink/bench_tools")
import run_highthink as R
def load(run, tid):
    p = L / run / "results" / f"{tid}.json"
    return json.loads(p.read_text()) if p.exists() else {}
data = {r: {t: load(r, t) for t in IDS} for r in RUNS}
def thoughts(res):
    """Per model response thought token counts, by agent. Tokenised from the trace text for all runs (same method);
    run30 also has vLLM usage.reasoning_tokens."""
    per = {}
    for rec in res.get("trace") or []:
        if rec.get("thought"):
            per.setdefault(SHORT.get(rec["author"], rec["author"]), []).append(count_tokens(rec["thought"]))
    return per
def usage(res):
    per = {}
    for c in res.get("llm_calls") or []:
        if c.get("thoughts_tokens") is not None:
            per.setdefault(SHORT.get(c["agent"], c["agent"]), []).append(c["thoughts_tokens"])
    return per
ev = {"max_turns": 45, "max_tool_calls": 58}
lines = [f"# BASE_HIGHTHINK_REPORT — v5.8 saf taban, thinking 4096 → 8192/12288\n",
         f"oluşturma: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n"]
score = {r: sum(bool(d.get("resolved")) for d in data[r].values()) for r in RUNS}
fin = {r: sum(bool(d) for d in data[r].values()) for r in RUNS}
lines.append("## Skor\n\n| koşu | thinking_budget | resolved | biten |\n|---|---|---|---|")
for r, lab in RUNS.items():
    lines.append(f"| `{r}` | {lab.split('(')[1].rstrip(')')} | **{score[r]}/20** | {fin[r]}/20 |")
lines.append("\n## Görev bazında\n\n| task | run21 | run28A | run30 | run31 | run31 kova | run31 calls/turns/wall_s |\n|---|---|---|---|---|---|---|")
f = lambda x: ("YES" if x.get("resolved") else "no") if x else "— (koşulmadı)"
for t in IDS:
    c = data["run_31_feedback_fix"][t]
    lines.append(f"| {t} | " + " | ".join(f(data[r][t]) for r in RUNS) + f" | {R.classify(c, {"max_turns": 72, "max_tool_calls": 58}) if c else '—'} | "
                 f"{c.get('tool_calls','—')}/{c.get('turns','—')}/{c.get('wall_s','—')} |")
ever4096 = {t for t in IDS if data["run_21_bench20_v5_8"][t].get("resolved") or data["run_28A_base_control_v5"][t].get("resolved")}
both4096 = {t for t in IDS if data["run_21_bench20_v5_8"][t].get("resolved") and data["run_28A_base_control_v5"][t].get("resolved")}
for r in ("run_30_base_highthink", "run_31_feedback_fix"):
    sol = {t for t in IDS if data[r][t].get("resolved")}
    lines.append(f"- **{r}:** 4096'da hiç çözülmemişken çözülen: {sorted(sol - ever4096) or '—'}; iki 4096 koşusunda da çözülmüşken kaybedilen: {sorted((both4096 - sol) & {t for t in IDS if data[r][t]}) or '—'}")
lines.append(f"- 4096 kontrolünün kendi gürültüsü: iki koşuda da çözülen {sorted(both4096)}; yalnız birinde çözülen {sorted(ever4096 - both4096)}")
lines.append(f"- Dört koşunun **herhangi birinde** çözülen görevler (birleşim): {len({t for t in IDS if any(data[r][t].get('resolved') for r in RUNS)})}/20 — {sorted(t for t in IDS if any(data[r][t].get('resolved') for r in RUNS))}")
lines.append("\n## Ajan başına düşünce token'ları (model yanıtı başına)\n\nAynı yöntem: trace'teki düşünce metni Gemma-4 tokenizer'ı ile sayıldı (eski koşular yalnızca metni sakladığı için). run30 için vLLM `usage.reasoning_tokens` sütunu da verildi.\n")
lines.append("| ajan | run21 ort / maks (n) | run28A ort / maks (n) | run30 ort / maks (n) | run31 ort / maks (n) | run30+31 vLLM usage ort / maks (n) | bütçe (run30/31) |\n|---|---|---|---|---|---|---|")
budget = {"planner": 8192, "coder_a": 12288, "coder_b": 12288, "qa_judge": 8192}
agg = {r: {} for r in RUNS}; uagg = {}
for r in RUNS:
    for t in IDS:
        for k, v in thoughts(data[r][t]).items():
            agg[r].setdefault(k, []).extend(v)
for r in ("run_30_base_highthink", "run_31_feedback_fix"):
    for t in IDS:
        for k, v in usage(data[r][t]).items():
            uagg.setdefault(k, []).extend(v)
fmt = lambda v: f"{statistics.mean(v):.0f} / {max(v)} ({len(v)})" if v else "—"
for k in ("planner", "coder_a", "coder_b", "qa_judge"):
    lines.append(f"| {k} | {fmt(agg['run_21_bench20_v5_8'].get(k, []))} | {fmt(agg['run_28A_base_control_v5'].get(k, []))} | "
                 f"{fmt(agg['run_30_base_highthink'].get(k, []))} | {fmt(agg['run_31_feedback_fix'].get(k, []))} | {fmt(uagg.get(k, []))} | {budget[k]} |")
hit = {k: sum(x >= budget[k] - 16 for x in uagg.get(k, [])) for k in budget}
lines.append(f"\nrun30+31'de bütçe tavanına (≥ bütçe−16) dayanan yanıt sayısı: {hit}")
# context guard / clamp / finish reasons
g = [x for r in ('run_30_base_highthink','run_31_feedback_fix') for t in IDS for x in (data[r][t].get('context_guard') or [])]
calls = [x for r in ('run_30_base_highthink','run_31_feedback_fix') for t in IDS for x in (data[r][t].get('llm_calls') or [])]
if g:
    lines.append(f"\n## Bağlam koruması (run30 + run31)\n\n- model çağrısı: {len(g)}; budama tetiklenen: {sum(1 for x in g if x['pruned_parts'])}; "
                 f"max_output_tokens kısılan (prompt+çıktı > 32768 olacaktı): {sum(1 for x in g if x['max_out_clamped'])}; "
                 f"maks prompt tahmini: {max(x['prompt_est'] for x in g)} → budama sonrası maks {max(x['after_prune'] for x in g)}")
    fr = {}
    for x in calls:
        fr[x.get('finish_reason')] = fr.get(x.get('finish_reason'), 0) + 1
    lines.append(f"- finish_reason dağılımı: {fr}; LLM hata kodlu yanıt: {sum(1 for x in calls if x.get('error'))}")
    to = [f'{r[4:6]}:{t}' for r in ('run_30_base_highthink','run_31_feedback_fix') for t in IDS if 'time budget' in json.dumps(data[r][t].get('trace') or [])[-3000:]]
    lines.append(f"- 15 dk zaman bütçesine takılan görevler: {to or '—'}")
lines.append("\n## Taksonomi\n")
for r in RUNS:
    tax = {}
    e2 = {"max_turns": 72 if r == "run_31_feedback_fix" else 45, "max_tool_calls": 58}
    for t in IDS:
        c = data[r][t]
        if c:
            k = R.classify(c, e2); tax[k] = tax.get(k, 0) + 1
    lines.append(f"- `{r}`: " + "  |  ".join(f"{k}: {v}" for k, v in tax.items()))
extra = Path("/content/eval_highthink/report_notes.md")
if extra.exists():
    lines.append("\n" + extra.read_text())
out = "\n".join(lines) + "\n"
Path("/content/eval_highthink/BASE_HIGHTHINK_REPORT.md").write_text(out)
print(out)
