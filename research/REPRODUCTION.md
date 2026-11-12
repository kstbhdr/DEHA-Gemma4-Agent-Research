# Verification and rerun requirements

## Verify the recorded outcomes

Run these commands from the repository root with Python 3 and a SHA-256 checksum utility.

```sh
sha256sum -c SHA256SUMS
python3 scripts/aggregate_results.py --check
```

The script checks the task IDs against the 20-task manifest and counts the original Boolean `resolved` values retained in each extract. It should print 6/20, 0/20, 0/20, 10/20 and 13/20 for run21, run32A, run32B, run35 and run36, respectively. It computes the 14/20 oracle union by taking the set union of the solved IDs in run35 and run36. This verifies aggregation from the stored outcomes. A model and test rerun is a separate procedure.

## Rerun the benchmark

1. Provision a Linux sandbox per task with the benchmark's original repository revision, environment, and fail-to-pass and pass-to-pass tests. Use the same 20 task IDs and original order from [the manifest](../experiments/kaggle_bench_20_ids.json). Confirm the benchmark preflight before evaluating candidate patches.
2. Set up the original ADK and evaluation dependencies, then select the model backend and package corresponding to the run. Use the [run21 snapshot](../scripts/run21/) for the E4B compile-gated package. For the LoRA variants, consult [the training snapshots](../training/) and the [v6 report](V6_FINAL_TRAINING_EVAL_REPORT.md). The LoRA weights and source training datasets must be supplied separately.
3. For local 31B work, provision a compatible llama-server with the Q3_K_M model and MTP configuration from the [run35](../experiments/run35/SUMMARY.md) and [run36](../experiments/run36/SUMMARY.md) summaries. Point the [archived harness](../scripts/run36/adk_dag_harness.py) to it through `DEHA_API_BASE` and set `DEHA_BACKEND=llamacpp`. Run35 used a 15-minute, 58-call cap. Run36 used 30 minutes and 110 calls. Use the official competition harness and W4A16 backend for official evaluation.
4. Use the package's QA checks and the task's evaluation suite to score the resulting patch. Compare to the historical outcomes by task ID. For run36, compare the reconstructed v2r package against the last fourteen tasks separately. Exact replay of the first six requires the missing original v2 package.

The scripts are research snapshots with environment-specific paths. This release omits model weights, datasets, archived benchmark workspaces, some harness helpers and dependency pins, complete raw traces, and the original run36 v2 package. Full training or inference replay was not verified. The [manifest](PROVENANCE.tsv) identifies the source file and source hash for each verbatim copy, archive member, exported manuscript, or result extract. Extracts retain the named scalar fields without filling absent fields. In run36, the original summary identifies the six v2 tasks, including those with no `pkg` field in the raw JSON.
