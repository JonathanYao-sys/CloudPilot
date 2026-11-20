"""
M3 Verification Test Suite (Gate 1 & Gate 4):
Verifies local synthetic dataset splits (train/validation/test), >= 1,200 validated examples,
8 balanced task families, zero train/val/test leakage, zero PII/secrets, dataset cards,
and the frozen pre-training A/C baseline report (pretrain_ac_baseline.json & PRETRAIN_BASELINE_REPORT.md).
"""

import json
from pathlib import Path

from training.data_pipeline.validate_dataset import validate_splits

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_m3_dataset_files_and_reports_exist():
    required = [
        "training/data_pipeline/generate_dataset.py",
        "training/data_pipeline/validate_dataset.py",
        "training/datasets/train.jsonl",
        "training/datasets/validation.jsonl",
        "training/datasets/test.jsonl",
        "training/datasets/DATASET_CARD.md",
        "training/reports/data_quality.md",
        "evaluation/baselines/run_pretrain_ac_baseline.py",
        "evaluation/baselines/pretrain_ac_baseline.json",
        "evaluation/baselines/PRETRAIN_BASELINE_REPORT.md",
    ]
    for rel in required:
        p = ROOT_DIR / rel
        assert p.exists(), f"Missing M3 deliverable: {rel}"
        assert p.stat().st_size > 100, f"Empty M3 deliverable: {rel}"


def test_m3_dataset_quality_and_zero_leakage():
    report = validate_splits()
    assert report["status"] == "PASSED"
    assert report["total_examples"] == 1320
    assert report["split_counts"]["train"] == 1000
    assert report["split_counts"]["validation"] == 160
    assert report["split_counts"]["test"] == 160
    assert report["leakage_checks"]["train_validation_overlap"] == 0
    assert report["leakage_checks"]["train_test_overlap"] == 0
    assert report["leakage_checks"]["validation_test_overlap"] == 0
    assert len(report["family_counts"]["train"]) == 8
    assert len(report["family_counts"]["test"]) == 8


def test_m3_frozen_pretrain_ac_baseline():
    baseline_path = ROOT_DIR / "evaluation" / "baselines" / "pretrain_ac_baseline.json"
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert data["stage"] == "M3_PRE_TRAINING_BASELINE_FREEZE"
    assert len(data["frozen_test_split_sha256"]) == 64
    assert data["evaluated_cases_count"] == 64

    model_a = data["models"]["A_base_executor"]
    model_c = data["models"]["C_independent_small_model"]
    assert model_a["model_id"] == "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
    assert model_c["model_id"] == "mlx-community/SmolLM2-135M-Instruct"
    assert model_a["mean_tokens_per_sec"] > 20.0
    assert model_c["mean_tokens_per_sec"] > 20.0
    # Untrained Model A has 0% on ambiguity abstention, error classification, and permission rejection
    assert model_a["family_accuracy_pct"]["family_4_ambiguity_abstention"] == 0.0
    assert model_a["family_accuracy_pct"]["family_5_error_classification"] == 0.0
    assert model_a["family_accuracy_pct"]["family_6_permission_rejection"] == 0.0
