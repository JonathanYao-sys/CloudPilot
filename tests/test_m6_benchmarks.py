"""
M6 Verification Test Suite (Gate 7):
Verifies three-model (A/B/C) local benchmark raw outputs, CSV summary, EVALUATION_REPORT.md,
REPRODUCIBILITY.md, PNG charts, self-run leaderboard integrity disclosure, and Model B improvement.
"""

import csv
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_m6_deliverables_exist():
    required = [
        "evaluation/suites/run_abc_evaluation.py",
        "evaluation/raw_results/base.jsonl",
        "evaluation/raw_results/finetuned.jsonl",
        "evaluation/raw_results/small_model.jsonl",
        "evaluation/results.csv",
        "evaluation/EVALUATION_REPORT.md",
        "evaluation/REPRODUCIBILITY.md",
        "evaluation/charts/accuracy_comparison.png",
        "evaluation/charts/latency_memory_comparison.png",
        "evaluation/charts/family_breakdown.png",
    ]
    for rel in required:
        p = ROOT_DIR / rel
        assert p.exists(), f"Missing M6 deliverable: {rel}"
        assert p.stat().st_size > 200, f"Empty M6 deliverable: {rel}"


def test_m6_results_csv_and_finetuned_improvement():
    csv_path = ROOT_DIR / "evaluation" / "results.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = {r["role"]: r for r in csv.DictReader(f)}

    assert set(rows.keys()) == {"A", "B", "C"}
    acc_a = float(rows["A"]["exact_grounding_acc_pct"])
    acc_b = float(rows["B"]["exact_grounding_acc_pct"])
    acc_c = float(rows["C"]["exact_grounding_acc_pct"])

    # On-Mac fine-tuned Model B must achieve strong tool grounding accuracy and outperform untrained baselines
    assert acc_b >= 80.0, f"Expected fine-tuned Model B accuracy >= 80%, got {acc_b}%"
    assert acc_b > acc_a, f"Expected Model B ({acc_b}%) to outperform Base A ({acc_a}%)"
    assert acc_b > acc_c, f"Expected Model B ({acc_b}%) to outperform Small Baseline C ({acc_c}%)"


def test_m6_leaderboard_integrity_and_raw_jsonl_counts():
    report_text = (ROOT_DIR / "evaluation" / "EVALUATION_REPORT.md").read_text(encoding="utf-8")
    assert "self-run offline benchmark results" in report_md_lower(report_text)
    assert "not an official public leaderboard ranking" in report_md_lower(report_text)

    for fname in ("base.jsonl", "finetuned.jsonl", "small_model.jsonl"):
        p = ROOT_DIR / "evaluation" / "raw_results" / fname
        lines = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 76  # 64 held-out test cases + 12 BFCL subset cases


def report_md_lower(t: str) -> str:
    return t.lower()
