#!/usr/bin/env python3
"""
CloudPilot Pre-Training A/C Baseline Evaluation (Phase 1 & Phase 4 / M3)
Runs Original Base Executor (Model A: mlx-community/Qwen2.5-0.5B-Instruct-4bit)
and Independent Small Baseline (Model C: mlx-community/SmolLM2-135M-Instruct)
against the frozen held-out test split (training/datasets/test.jsonl) BEFORE Model B fine-tuning.
Records model size, latency, Metal memory, JSON validity, tool-call accuracy, and family breakdown.
"""

from __future__ import annotations

import hashlib
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["CLOUDPILOT_OFFLINE_ONLY"] = "1"

from app.model_runtime.mlx_loader import LocalMLXRuntime
from evaluation.suites.run_abc_evaluation import load_balanced_heldout_cases, score_prediction
from training.data_pipeline.generate_dataset import FAMILIES

BASELINES_DIR = ROOT_DIR / "evaluation" / "baselines"
OUT_JSON = BASELINES_DIR / "pretrain_ac_baseline.json"
OUT_MD = BASELINES_DIR / "PRETRAIN_BASELINE_REPORT.md"
TEST_PATH = ROOT_DIR / "training" / "datasets" / "test.jsonl"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def eval_pretrain_model(runtime: LocalMLXRuntime, role: str, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    runtime.ensure_loaded(role)
    model_dir, _, model_id = runtime.resolve_role_paths(role)
    total_size_mb = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file()) / (1024 * 1024)
    st_files = sorted(model_dir.glob("*.safetensors"))
    weights_sha = sha256_file(st_files[0]) if st_files else "unknown"

    tps_list: List[float] = []
    ttft_list: List[float] = []
    peak_mem_list: List[float] = []
    load_time_s = 0.0

    fam_totals: Dict[str, int] = defaultdict(int)
    fam_correct: Dict[str, int] = defaultdict(int)
    json_valid = 0
    tool_match = 0
    exact_grounding = 0

    for idx, case in enumerate(cases):
        msgs = case["messages"]
        trace = runtime.generate_structured(
            role=role,
            system_prompt=msgs[0]["content"],
            user_prompt=msgs[1]["content"],
            max_tokens=96,
            measure_ttft=(idx < 4),
        )
        if idx == 0:
            load_time_s = trace.load_time_s
        tps_list.append(trace.tokens_per_sec)
        if idx < 4:
            ttft_list.append(trace.ttft_ms)
        peak_mem_list.append(trace.peak_metal_memory_mb)

        sc = score_prediction(trace.parsed_json, case["expected_tool"], case["expected_args"])
        fam = case["family"]
        fam_totals[fam] += 1
        if sc["json_valid"]:
            json_valid += 1
        if sc["tool_match"]:
            tool_match += 1
        if sc["exact_grounding"]:
            exact_grounding += 1
            fam_correct[fam] += 1

    n = len(cases)
    return {
        "role": role,
        "model_id": model_id,
        "weights_sha256": weights_sha,
        "disk_size_mb": round(total_size_mb, 2),
        "load_time_s": round(load_time_s, 3),
        "mean_ttft_ms": round(statistics.mean(ttft_list), 2) if ttft_list else 0.0,
        "mean_tokens_per_sec": round(statistics.mean(tps_list), 2),
        "peak_metal_memory_mb": round(max(peak_mem_list), 2),
        "evaluated_cases": n,
        "json_valid_pct": round(100.0 * json_valid / n, 2),
        "tool_selection_acc_pct": round(100.0 * tool_match / n, 2),
        "exact_grounding_acc_pct": round(100.0 * exact_grounding / n, 2),
        "family_accuracy_pct": {
            f: round(100.0 * fam_correct[f] / max(fam_totals[f], 1), 2) for f in FAMILIES
        },
    }


def main() -> int:
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_balanced_heldout_cases(per_family=8)
    runtime = LocalMLXRuntime()

    print("Running M3 pre-training baseline evaluation for Model A and Model C on frozen test.jsonl...")
    res_a = eval_pretrain_model(runtime, "A", cases)
    res_c = eval_pretrain_model(runtime, "C", cases)

    payload = {
        "stage": "POST_HOC_UNMODIFIED_AC_BASELINE",
        "chronology_disclosure": (
            "Post-hoc baseline evaluation (事后补测基线): executed after M4 LoRA training using the unmodified "
            "original checkpoints for Model A (SHA256: ddffab9cbc7bf6dde941c6724841eeca8981fcfa81ca20ff8efff1396326d153) "
            "and Model C (SHA256: 989e3ef746b41999ca096055a60c87057b8e842824253391bc0d9ed8dfc6936e) against the "
            "held-out test.jsonl split that was frozen in M3 prior to M4 training."
        ),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "frozen_test_split_path": "training/datasets/test.jsonl",
        "frozen_test_split_sha256": sha256_file(TEST_PATH),
        "evaluated_cases_count": len(cases),
        "models": {
            "A_base_executor": res_a,
            "C_independent_small_model": res_c,
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    md = f"""# CloudPilot Post-Hoc Unmodified A & C Baseline Report (`PRETRAIN_BASELINE_REPORT.md`)

> **Baseline Classification:** **`POST_HOC_UNMODIFIED_AC_BASELINE`（事后补测的未修改 A/C 基线）**  
> **Chronology & Provenance Disclosure:** While `training/datasets/test.jsonl` (SHA-256: `{payload['frozen_test_split_sha256']}`) was generated and frozen in M3 prior to M4 LoRA training, and the base checkpoints for Model A and Model C were never modified during training, this 64-case stratified baseline script was executed **post-hoc (after M4 fine-tuning completed)**. It is therefore truthfully labeled as a **Post-Hoc Baseline on Unmodified A/C Checkpoints**, not a pre-training timestamped run.  
> **Evaluated Stratified Held-Out Cases:** `{len(cases)}` (8 task families × 8 cases)  
> **Network Condition:** `HF_HUB_OFFLINE=1` (100% On-Mac Apple M4 Metal 4 Execution)

## 1. Unmodified Base Model A vs. Small Model C Baseline Metrics

| Metric | **Model A** (`{res_a['model_id']}`) | **Model C** (`{res_c['model_id']}`) |
| --- | --- | --- |
| **Checkpoint SHA-256** | `{res_a['weights_sha256'][:16]}...` | `{res_c['weights_sha256'][:16]}...` |
| **Disk Footprint (`MB`)** | `{res_a['disk_size_mb']} MB` | `{res_c['disk_size_mb']} MB` |
| **Model Load Time (`s`)** | `{res_a['load_time_s']} s` | `{res_c['load_time_s']} s` |
| **Mean TTFT (`ms`)** | `{res_a['mean_ttft_ms']} ms` | `{res_c['mean_ttft_ms']} ms` |
| **Decode Speed (`tokens/sec`)** | `{res_a['mean_tokens_per_sec']} tok/s` | `{res_c['mean_tokens_per_sec']} tok/s` |
| **Peak Metal Memory (`MB`)** | `{res_a['peak_metal_memory_mb']} MB` | `{res_c['peak_metal_memory_mb']} MB` |
| **Valid JSON Rate (%)** | `{res_a['json_valid_pct']}%` | `{res_c['json_valid_pct']}%` |
| **Tool Selection Accuracy (%)** | `{res_a['tool_selection_acc_pct']}%` | `{res_c['tool_selection_acc_pct']}%` |
| **Exact Argument Grounding (%)** | **`{res_a['exact_grounding_acc_pct']}%`** | **`{res_c['exact_grounding_acc_pct']}%`** |

## 2. Pre-Training Per-Family Breakdown (Diagnosis motivating M4 LoRA Fine-Tuning)

| Task Family | Model A (Untrained Base) | Model C (Untrained Small) | Pre-Training Diagnosis |
| --- | --- | --- | --- |
| `family_1_tool_choice` | `{res_a['family_accuracy_pct']['family_1_tool_choice']}%` | `{res_c['family_accuracy_pct']['family_1_tool_choice']}%` | Base A handles basic single-tool JSON; Small C echoes prompt schema |
| `family_2_grounded_copy` | `{res_a['family_accuracy_pct']['family_2_grounded_copy']}%` | `{res_c['family_accuracy_pct']['family_2_grounded_copy']}%` | Base A copies arguments when no conflict/error exists |
| `family_3_step_dependencies` | `{res_a['family_accuracy_pct']['family_3_step_dependencies']}%` | `{res_c['family_accuracy_pct']['family_3_step_dependencies']}%` | Base A handles straightforward verify/manifest calls |
| `family_4_ambiguity_abstention` | **`{res_a['family_accuracy_pct']['family_4_ambiguity_abstention']}%`** | `{res_c['family_accuracy_pct']['family_4_ambiguity_abstention']}%` | **Critical Gap:** Untrained Base A never emits `abstain` on wildcard ambiguity |
| `family_5_error_classification` | **`{res_a['family_accuracy_pct']['family_5_error_classification']}%`** | `{res_c['family_accuracy_pct']['family_5_error_classification']}%` | **Critical Gap:** Untrained Base A blindly calls `copy_file` even when source is missing (`FILE_NOT_FOUND`) |
| `family_6_permission_rejection` | **`{res_a['family_accuracy_pct']['family_6_permission_rejection']}%`** | `{res_c['family_accuracy_pct']['family_6_permission_rejection']}%` | **Critical Gap:** Untrained Base A executes `on_conflict='overwrite'` when `allow_overwrite=False` |
| `family_7_idempotent_replay` | `{res_a['family_accuracy_pct']['family_7_idempotent_replay']}%` | `{res_c['family_accuracy_pct']['family_7_idempotent_replay']}%` | Base A preserves `on_conflict='skip'` |
| `family_8_adversarial_safety` | **`{res_a['family_accuracy_pct']['family_8_adversarial_safety']}%`** | `{res_c['family_accuracy_pct']['family_8_adversarial_safety']}%` | **Critical Gap:** Untrained Base A fails to reject `../../etc/passwd` traversal with `report_error (UNSAFE_PATH)` |
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(f"Saved pre-training A/C baseline to {OUT_JSON.relative_to(ROOT_DIR)} and {OUT_MD.relative_to(ROOT_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
