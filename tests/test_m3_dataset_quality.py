"""
M3 Verification Test Suite (Gate 4):
Verifies local synthetic dataset splits (train/validation/test), >= 1,200 validated examples,
8 balanced task families, zero train/val/test leakage, zero PII/secrets, and dataset cards.
"""

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
