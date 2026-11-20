#!/usr/bin/env python3
"""
Phase 0 (M0) Hardware Inspection, Model Provisioning, Local Inference & Tiny LoRA Train Smoke Test.
Runs 100% locally on Apple M4 Metal via MLX.
Caches models in CloudPilot/.hf_cache so subsequent phases operate with HF_HUB_OFFLINE=1.
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
HF_CACHE = ROOT_DIR / ".hf_cache"
HF_CACHE.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(HF_CACHE)
os.environ["HF_HUB_CACHE"] = str(HF_CACHE / "hub")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import mlx.core as mx
from huggingface_hub import snapshot_download
from mlx_lm import generate, load

MODEL_A_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
MODEL_C_ID = "mlx-community/SmolLM2-135M-Instruct"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_inference(model_id: str, local_dir: Path, prompt: str) -> dict:
    mx.reset_peak_memory()
    t0 = time.perf_counter()
    model, tokenizer = load(str(local_dir))
    load_time_s = time.perf_counter() - t0

    messages = [
        {"role": "system", "content": "You are CloudPilot Local Executor. Respond only with valid JSON tool calls."},
        {"role": "user", "content": prompt},
    ]
    formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    # Measure Time-To-First-Token (1 token generation)
    t_ft0 = time.perf_counter()
    _ = generate(model, tokenizer, prompt=formatted, max_tokens=1, verbose=False)
    ttft_ms = (time.perf_counter() - t_ft0) * 1000.0

    # Measure full generation speed
    t_gen0 = time.perf_counter()
    output = generate(model, tokenizer, prompt=formatted, max_tokens=64, verbose=False)
    gen_time_s = time.perf_counter() - t_gen0
    out_tokens = len(tokenizer.encode(output))
    tps = out_tokens / max(gen_time_s, 1e-6)
    peak_mem_mb = mx.get_peak_memory() / (1024 * 1024)
    active_mem_mb = mx.get_active_memory() / (1024 * 1024)

    weights_files = sorted(local_dir.glob("*.safetensors"))
    weights_sha256 = sha256_file(weights_files[0]) if weights_files else "unknown"
    total_size_mb = sum(f.stat().st_size for f in local_dir.rglob("*") if f.is_file()) / (1024 * 1024)

    return {
        "model_id": model_id,
        "local_dir": str(local_dir.relative_to(ROOT_DIR)),
        "total_size_mb": round(total_size_mb, 2),
        "primary_safetensors_sha256": weights_sha256,
        "load_time_s": round(load_time_s, 3),
        "ttft_ms": round(ttft_ms, 2),
        "generated_tokens": out_tokens,
        "generation_time_s": round(gen_time_s, 3),
        "tokens_per_sec": round(tps, 2),
        "peak_metal_memory_mb": round(peak_mem_mb, 2),
        "active_metal_memory_mb": round(active_mem_mb, 2),
        "sample_output": output[:200],
    }


def run_tiny_lora_smoke_test(model_a_dir: Path) -> dict:
    """Run a 5-iteration local LoRA fine-tuning smoke test via mlx_lm.lora to verify on-Mac training."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        adapter_dir = tmp_path / "adapters"

        sample_rows = [
            {
                "messages": [
                    {"role": "system", "content": "You are CloudPilot Local Executor. Output JSON tool call only."},
                    {"role": "user", "content": "Step s1: Create folder 'Notes' in workspace."},
                    {"role": "assistant", "content": '{"tool": "create_folder", "args": {"path": "Notes"}}'},
                ]
            }
            for _ in range(16)
        ]
        for split in ("train.jsonl", "valid.jsonl"):
            with open(data_dir / split, "w", encoding="utf-8") as f:
                for row in sample_rows:
                    f.write(json.dumps(row) + "\n")

        cmd = [
            sys.executable,
            "-m",
            "mlx_lm",
            "lora",
            "--model",
            str(model_a_dir),
            "--train",
            "--data",
            str(data_dir),
            "--iters",
            "5",
            "--batch-size",
            "2",
            "--num-layers",
            "4",
            "--adapter-path",
            str(adapter_dir),
            "--seed",
            "42",
        ]
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration_s = time.perf_counter() - t0
        adapter_file = adapter_dir / "adapters.safetensors"
        assert adapter_file.exists(), "adapters.safetensors was not created by smoke test!"
        adapter_sha = sha256_file(adapter_file)
        adapter_size_kb = adapter_file.stat().st_size / 1024.0

        return {
            "status": "PASSED",
            "backend": "mlx_lm.lora (Apple Metal GPU)",
            "iters": 5,
            "batch_size": 2,
            "num_layers": 4,
            "duration_s": round(duration_s, 3),
            "adapter_size_kb": round(adapter_size_kb, 2),
            "adapter_sha256": adapter_sha,
            "stdout_tail": proc.stdout.strip().splitlines()[-6:],
        }


def main() -> int:
    print("1. Provisioning local models A and C into CloudPilot/.hf_cache...")
    model_a_dir = HF_CACHE / "models" / "Qwen2.5-0.5B-Instruct-4bit"
    model_c_dir = HF_CACHE / "models" / "SmolLM2-135M-Instruct"

    if not (model_a_dir / "model.safetensors").exists():
        snapshot_download(repo_id=MODEL_A_ID, local_dir=str(model_a_dir))
    if not (model_c_dir / "model.safetensors").exists():
        snapshot_download(repo_id=MODEL_C_ID, local_dir=str(model_c_dir))

    test_prompt = 'Step s1: create folder "AP_Euro" inside workspace. Emit JSON tool call.'
    print("2. Running local Metal inference smoke test on Model A...")
    res_a = measure_inference(MODEL_A_ID, model_a_dir, test_prompt)
    print(f"   Model A: {res_a['tokens_per_sec']} tok/s, TTFT {res_a['ttft_ms']} ms, Peak Metal {res_a['peak_metal_memory_mb']} MB")

    print("3. Running local Metal inference smoke test on Model C...")
    res_c = measure_inference(MODEL_C_ID, model_c_dir, test_prompt)
    print(f"   Model C: {res_c['tokens_per_sec']} tok/s, TTFT {res_c['ttft_ms']} ms, Peak Metal {res_c['peak_metal_memory_mb']} MB")

    print("4. Running 5-step tiny local LoRA training smoke test on Model A...")
    lora_smoke = run_tiny_lora_smoke_test(model_a_dir)
    print(f"   Tiny LoRA train smoke test: {lora_smoke['status']} in {lora_smoke['duration_s']}s")

    disk_usage = shutil.disk_usage(ROOT_DIR)
    env_report = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hardware": {
            "model_name": "MacBook Air (Mac16,12)",
            "chip": "Apple M4",
            "architecture": platform.machine(),
            "cpu_cores_total": 10,
            "cpu_performance_cores": 4,
            "cpu_efficiency_cores": 6,
            "gpu_cores": 10,
            "metal_support": "Metal 4",
            "metal_device_info": str(mx.metal.device_info()),
            "unified_memory_gb": 24,
            "disk_total_gb": round(disk_usage.total / (1024**3), 2),
            "disk_free_gb": round(disk_usage.free / (1024**3), 2),
        },
        "os_and_toolchain": {
            "macos_version": platform.mac_ver()[0],
            "python_version": platform.python_version(),
            "mlx_version": mx.__version__,
            "git_version": subprocess.check_output(["git", "--version"], text=True).strip(),
            "swift_version": subprocess.check_output(["swiftc", "--version"], text=True).splitlines()[0].strip(),
            "ffmpeg_available": shutil.which("ffmpeg") is not None,
        },
        "selected_models": {
            "A_base_executor": {
                "id": MODEL_A_ID,
                "license": "Apache-2.0",
                "role": "Original Base Executor Checkpoint (A)",
                "smoke_test": res_a,
            },
            "B_finetuned_executor": {
                "id": "CloudPilot-Qwen2.5-0.5B-Executor-LoRA-v1",
                "base_model": MODEL_A_ID,
                "license": "Apache-2.0",
                "role": "On-Mac MLX LoRA Fine-Tuned Executor Checkpoint (B)",
                "tiny_train_smoke_test": lora_smoke,
            },
            "C_independent_small_model": {
                "id": MODEL_C_ID,
                "license": "Apache-2.0",
                "role": "Independent Locally Runnable Small Model Baseline (C)",
                "smoke_test": res_c,
            },
            "P_local_planner": {
                "id": f"{MODEL_A_ID} + Deterministic Schema-Constrained Task Planner",
                "license": "Apache-2.0",
                "role": "Local Planner (P) running sequentially on the same Mac without dual-model RAM residency requirement",
            },
        },
    }

    out_env = ROOT_DIR / "docs" / "environment_report.json"
    out_log = ROOT_DIR / "logs" / "m0_smoke_test.json"
    for p in (out_env, out_log):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(env_report, f, indent=2, ensure_ascii=False)

    print(f"5. Saved environment and smoke test reports to {out_env}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
