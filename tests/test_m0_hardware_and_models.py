"""
M0 Verification Test Suite (Gate 0 & Gate 1):
Verifies real hardware inspection, local model cache, on-Mac MLX inference smoke test,
tiny on-Mac LoRA training smoke test, and frozen A/B/C/P architecture documentation.
"""

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_m0_required_reports_exist():
    required = [
        "docs/hardware_report.md",
        "docs/environment_report.json",
        "docs/local_compute_budget.md",
        "docs/offline_mode.md",
        "docs/ADR/0001-local-architecture-and-models.md",
    ]
    for rel in required:
        p = ROOT_DIR / rel
        assert p.exists(), f"Missing required M0 deliverable: {rel}"
        assert p.stat().st_size > 200, f"Deliverable {rel} is unexpectedly empty"


def test_environment_report_contains_real_hardware_and_smoke_tests():
    env_path = ROOT_DIR / "docs" / "environment_report.json"
    data = json.loads(env_path.read_text(encoding="utf-8"))

    hw = data["hardware"]
    assert hw["chip"] == "Apple M4"
    assert hw["architecture"] == "arm64"
    assert hw["unified_memory_gb"] == 24
    assert hw["disk_free_gb"] > 10.0

    models = data["selected_models"]
    assert models["A_base_executor"]["id"] == "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
    assert models["A_base_executor"]["smoke_test"]["tokens_per_sec"] > 20.0
    assert len(models["A_base_executor"]["smoke_test"]["primary_safetensors_sha256"]) == 64

    assert models["C_independent_small_model"]["id"] == "mlx-community/SmolLM2-135M-Instruct"
    assert models["C_independent_small_model"]["smoke_test"]["tokens_per_sec"] > 20.0
    assert len(models["C_independent_small_model"]["smoke_test"]["primary_safetensors_sha256"]) == 64

    smoke_train = models["B_finetuned_executor"]["tiny_train_smoke_test"]
    assert smoke_train["status"] == "PASSED"
    assert smoke_train["iters"] == 5
    assert smoke_train["adapter_size_kb"] > 100.0
    assert len(smoke_train["adapter_sha256"]) == 64


def test_local_model_files_cached_for_offline_use():
    model_a = ROOT_DIR / ".hf_cache" / "models" / "Qwen2.5-0.5B-Instruct-4bit" / "model.safetensors"
    model_c = ROOT_DIR / ".hf_cache" / "models" / "SmolLM2-135M-Instruct" / "model.safetensors"
    assert model_a.exists(), "Model A weights must be cached locally in .hf_cache"
    assert model_c.exists(), "Model C weights must be cached locally in .hf_cache"


def test_hardware_report_redacts_serial_numbers():
    text = (ROOT_DIR / "docs" / "hardware_report.md").read_text(encoding="utf-8")
    assert "Apple M4" in text
    assert "Serial Number:" not in text
    assert "Hardware UUID:" not in text
