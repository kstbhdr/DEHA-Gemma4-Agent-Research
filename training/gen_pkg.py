import yaml, sys, shutil
from pathlib import Path
OUT = Path(sys.argv[1]); P = Path(sys.argv[2])
if OUT.exists(): shutil.rmtree(OUT)
(OUT/"sub_agents").mkdir(parents=True)
MODEL = "google/gemma-4-E4B-it-qat-w4a16-ct"
class Lit(str): pass
yaml.SafeDumper.add_representer(Lit, lambda d, s: d.represent_scalar("tag:yaml.org,2002:str", s, style="|"))
def dump(path, obj): (OUT/path).write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=10**6))
dump("agent.yaml", {"agent_class": "LoopAgent", "name": "deha_dag_loop",
     "description": "Feedback loop around one planner -> coder A -> coder B -> QA judge iteration.",
     "max_iterations": 3, "sub_agents": [{"config_path": "dag_iteration.yaml"}]})
dump("dag_iteration.yaml", {"agent_class": "SequentialAgent", "name": "deha_dag_iteration",
     "description": "One iteration: planner, isolated coder A, isolated coder B and merger, QA judge.",
     "sub_agents": [{"config_path": f"sub_agents/{n}.yaml"} for n in ("planner", "coder_a", "coder_b", "qa_judge")]})
dump("eval_config.yaml", {"evaluation": {"timeout_seconds": 180, "max_tool_calls": 58, "max_turns": int(sys.argv[3]) if len(sys.argv) > 3 else 45, "max_time_minutes": 15}})
A = {
 "planner": ("deha_planner_and_conflict_guard", 0.2, 16384, 8192,
             ["search_similar_code", "get_code_neighbors", "get_code_subgraph", "read_file", "run_command", "get_status"]),
 "coder_a": ("deha_isolated_coder_a", 0.2, 20480, 12288,
             ["read_file", "edit_file", "run_command", "get_status", "search_similar_code"]),
 "coder_b": ("deha_isolated_coder_b_and_merger", 0.2, 20480, 12288,
             ["read_file", "edit_file", "run_command", "get_status", "search_similar_code"]),
 "qa_judge": ("deha_qa_smoke_and_feedback", 0.1, 16384, 8192,
              ["read_file", "run_command", "get_status", "submit_patch"]),
}
for f, (name, temp, mot, tb, tools) in A.items():
    instr = (P/f"{f}.md").read_text().rstrip("\n") + "\n"
    dump(f"sub_agents/{f}.yaml", {"agent_class": "LlmAgent", "name": name, "model": MODEL, "include_contents": "none",
        "instruction": Lit(instr),
        "generate_content_config": {"temperature": temp, "top_p": 0.95, "max_output_tokens": mot,
                                    "thinking_config": {"include_thoughts": True, "thinking_budget": tb}},
        "tools": tools})
print("written", sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file()))
