"""Verify recorded benchmark outcomes from the per-task result extracts."""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"run21": 6, "run32A": 0, "run32B": 0, "run35": 10, "run36": 13}


def aggregate():
    experiments = ROOT / "experiments"
    task_ids = set(json.loads((experiments / "kaggle_bench_20_ids.json").read_text())["task_ids"])
    if len(task_ids) != 20:
        raise ValueError("Expected 20 distinct benchmark task IDs")
    totals = {}
    for run, expected_count in EXPECTED.items():
        records = {}
        for path in (experiments / run / "results").glob("*.json"):
            record = json.loads(path.read_text())
            if record["task"] != path.stem or type(record["resolved"]) is not bool:
                raise ValueError(f"Invalid result record: {path}")
            records[path.stem] = record["resolved"]
        if records.keys() != task_ids:
            raise ValueError(f"{run}: task IDs differ from the benchmark manifest")
        solved = {task for task, resolved in records.items() if resolved}
        if len(solved) != expected_count:
            raise ValueError(f"{run}: expected {expected_count} resolutions, got {len(solved)}")
        totals[run] = solved
        yield run, "single_run", len(solved), len(task_ids)
    yield "run35+run36", "oracle_union", len(totals["run35"] | totals["run36"]), len(task_ids)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare to the checked-in CSV")
    args = parser.parse_args()
    rows = [("run", "metric", "resolved", "tasks"), *aggregate()]
    if args.check:
        with (ROOT / "experiments" / "results.csv").open(newline="") as file:
            if list(csv.reader(file)) != [[str(value) for value in row] for row in rows]:
                raise SystemExit("Recorded results differ from results.csv")
    csv.writer(sys.stdout, lineterminator="\n").writerows(rows)


if __name__ == "__main__":
    main()
