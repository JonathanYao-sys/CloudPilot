"""
M4 Verification Test Suite (Gate 5):
Verifies on-Mac MLX LoRA fine-tuned weights (adapters.safetensors), fused deployment weights
(model/deployment/model.safetensors), training loss convergence, Model Card, and actual App loader inference.
"""

import json
from pathlib import Path

from app.local_executor.executor_agent import LocalExecutorAgent
from app.model_runtime.mlx_loader import LocalMLXRuntime
from protocol.versions.v1 import PlanStep

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_m4_weights_and_model_card_exist():
    required = [
        "training/configs/lora_config.yaml",
        "training/scripts/train_local_lora.py",
        "training/reports/training_metrics.json",
        "model/adapters/adapters.safetensors",
        "model/adapters/adapter_config.json",
        "model/deployment/model.safetensors",
        "model/MODEL_CARD.md",
    ]
    for rel in required:
        p = ROOT_DIR / rel
        assert p.exists(), f"Missing M4 deliverable: {rel}"
        assert p.stat().st_size > 100, f"Empty M4 deliverable: {rel}"


def test_m4_training_metrics_and_convergence():
    metrics_path = ROOT_DIR / "training" / "reports" / "training_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    assert metrics["status"] == "PASSED"
    assert len(metrics["adapter_sha256"]) == 64
    assert len(metrics["deployment_sha256"]) == 64
    assert metrics["adapter_size_mb"] > 1.0
    assert metrics["deployment_size_mb"] > 200.0

    val_curve = metrics["val_curve"]
    assert len(val_curve) >= 2
    # Confirm gradient updates reduced validation loss on this Mac
    assert val_curve[-1]["val_loss"] < val_curve[0]["val_loss"]


def test_m4_finetuned_model_b_loads_and_grounds_tool_calls_without_fallback():
    runtime = LocalMLXRuntime()
    agent = LocalExecutorAgent(runtime=runtime, role="B", allow_deterministic_fallback=False)

    step = PlanStep(
        step_id="s1",
        action="create_folder",
        args={"path": "Q4_Audits"},
        depends_on=[],
    )
    res = agent.resolve_step(step=step, workspace_files=["Invoice_001.pdf"], allow_overwrite=False)
    assert res["raw_model_valid"] is True, f"Expected raw Model B output to be valid JSON tool call, got: {res}"
    assert res["fallback_used"] is False
    assert res["tool_call"]["tool"] == "create_folder"
    assert res["tool_call"]["args"]["path"] == "Q4_Audits"
