# DEHA Gemma 4 Agent Research

Research artifacts for the Gemma 4 Developer Agent Paper Track. The experiments ask how agent topology and tool allocation interact with model scale, whether synthetic-rationale LoRA transfers to repository repair, and when parallel patch generation changes the verifier's decision.

## Architecture and benchmark

The evaluation uses 20 fixed repository-repair tasks. The recorded harness evaluates candidate patches against task tests and records whether each task resolves. The E4B DAG uses a Planner, two Coders, and a QA Judge. The 31B single-agent design removes the standalone Planner and gives an execution-first Fixer a QA loop. The parallel design runs Fixer A and Fixer B in separate workspaces, followed by a QA Judge that selects a candidate. The harness can also evaluate a recovered unsubmitted patch.

| Run | Configuration | Time / tool-call cap | Resolved |
| --- | --- | --- | --- |
| [run21](experiments/run21/SUMMARY.md) | E4B QAT DAG baseline | 15 min / 58 | 6/20 |
| [run32A](experiments/run32A/SUMMARY.md) | E4B v6 LoRA on all DAG roles | 15 min / 58 | 0/20 |
| [run32B](experiments/run32B/SUMMARY.md) | E4B v6 LoRA on coder and QA roles | 15 min / 58 | 0/20 |
| [run35](experiments/run35/SUMMARY.md) | Local 31B GGUF Fixer and QA | 15 min / 58 | 10/20 |
| [run36](experiments/run36/SUMMARY.md) | Local 31B GGUF parallel Fixers and QA | 30 min / 110 | 13/20 |
| run35 ∪ run36 | Oracle union of solved task IDs | Two runs | 14/20 |

The 31B rows used a local NVIDIA L4 with GGUF Q3_K_M and MTP. Official W4A16 uses a separate vLLM evaluation path. The local scores and timings apply to the local environment. The different time and tool-call budgets between run35 and run36 prevent isolating the effect of parallelism from this comparison.

## Observations

- The standalone 31B Planner exhausted shared tool calls during exploration in preliminary attempts. The execution-first topology was used for the completed run35 evaluation.
- Both v6 LoRA variants resolved 0/20. The manuscript calls this observed regression **Synthetic CoT Collapse**. Short synthetic rationales interfering with long-horizon tool use are a hypothesized mechanism for these runs. The experiments do not establish a general causal effect.
- Run36 attributed ten resolutions to Fixer A and three to automatic patch recovery. Fixer B directly won zero resolved tasks. On `requests_7309`, CONSENSUS submitted a patch in 263.6 s, compared with a 955.9 s unsubmitted attempt in run35, a 3.6× difference in this single task.
- The first six run36 tasks used original v2. The remaining fourteen used v2r, reconstructed from recorded traces and configuration notes. The original v2 package is unavailable in the collected materials. The parallel configurations whose filenames end in `v2` are the archived reconstruction. [Reconstruction details](research/submission_kaggle_31b_parallel_v2.RECONSTRUCTION.md)

## Evidence

- [Paper Track manuscript](paper/DEHA_Gemma4_Paper_Track_Submission.md) and [release notes for reading the manuscript](paper/README.md)
- [E4B DAG YAML and prompts](configs/e4b-dag/), [31B single-fixer YAML](configs/31b-single/), and [31B parallel YAML](configs/31b-parallel/)
- [Cross-run report](research/CROSS_RUN_REPORT.md), [base high-think report](research/BASE_HIGHTHINK_REPORT.md), [v6 training and evaluation report](research/V6_FINAL_TRAINING_EVAL_REPORT.md), and [31B parallel validation report](research/VALIDATION_31B_PARALLEL_REPORT.md)
- [Result table](experiments/results.csv), [source manifest](research/PROVENANCE.tsv), [release checksums](SHA256SUMS), and [verification and rerun instructions](research/REPRODUCTION.md)

Each selected run has 20 task-result extracts that preserve the recorded measurements used in aggregation. The `selected-logs/` folders contain three original task logs per run. Complete raw JSON traces, aborted attempts, and experiment records for the wider 36-run series are outside this release.
