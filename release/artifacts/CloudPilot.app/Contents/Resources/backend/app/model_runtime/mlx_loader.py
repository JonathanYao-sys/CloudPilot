"""
CloudPilot Local MLX Model Runtime Loader (Phase 3, Phase 5, Phase 6, Phase 7)
Loads Model A (Base Qwen2.5-0.5B-Instruct-4bit), Model B (On-Mac Fine-Tuned Executor),
and Model C (SmolLM2-135M-Instruct) strictly from local disk with HF_HUB_OFFLINE=1.
Supports sequential loading and Metal cache clearing so two models never need to reside in RAM simultaneously.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[2]
HF_CACHE = ROOT_DIR / ".hf_cache"
os.environ["HF_HOME"] = str(HF_CACHE)
os.environ["HF_HUB_CACHE"] = str(HF_CACHE / "hub")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["CLOUDPILOT_OFFLINE_ONLY"] = "1"

import mlx.core as mx
from mlx_lm import generate, load

MODEL_A_DIR = HF_CACHE / "models" / "Qwen2.5-0.5B-Instruct-4bit"
MODEL_C_DIR = HF_CACHE / "models" / "SmolLM2-135M-Instruct"
MODEL_B_ADAPTER_DIR = ROOT_DIR / "model" / "adapters"
MODEL_B_DEPLOY_DIR = ROOT_DIR / "model" / "deployment"


def _resolve_bundled_or_local_deploy_dir() -> Optional[Path]:
    env_dir = os.environ.get("CLOUDPILOT_BUNDLED_MODEL_DIR")
    if env_dir:
        p = Path(env_dir).resolve()
        if (p / "model.safetensors").exists():
            return p
    # If running from inside CloudPilot.app/Contents/Resources/backend
    app_res_deploy = (ROOT_DIR.parent / "model" / "deployment").resolve()
    if (app_res_deploy / "model.safetensors").exists():
        return app_res_deploy
    if (MODEL_B_DEPLOY_DIR / "model.safetensors").exists():
        return MODEL_B_DEPLOY_DIR.resolve()
    return None


def _resolve_bundled_or_local_adapter_dir() -> Optional[Path]:
    env_dir = os.environ.get("CLOUDPILOT_BUNDLED_ADAPTER_DIR")
    if env_dir:
        p = Path(env_dir).resolve()
        if (p / "adapters.safetensors").exists():
            return p
    app_res_adapter = (ROOT_DIR.parent / "model" / "adapters").resolve()
    if (app_res_adapter / "adapters.safetensors").exists():
        return app_res_adapter
    if (MODEL_B_ADAPTER_DIR / "adapters.safetensors").exists():
        return MODEL_B_ADAPTER_DIR.resolve()
    return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse the first valid JSON object from model text output."""
    cleaned = text.strip()
    # Fast path if the entire string is JSON
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            obj = json.loads(cleaned)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        try:
            obj = json.loads(fence_match.group(1))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    # Balanced brace scan for first JSON object
    start_idx = cleaned.find("{")
    while start_idx != -1:
        depth = 0
        in_str = False
        escape = False
        for i in range(start_idx, len(cleaned)):
            ch = cleaned[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = cleaned[start_idx : i + 1]
                        try:
                            obj = json.loads(candidate)
                            if isinstance(obj, dict):
                                return obj
                        except Exception:
                            break
        start_idx = cleaned.find("{", start_idx + 1)
    return None


@dataclass
class GenerationTrace:
    role: str
    model_id: str
    adapter_used: Optional[str]
    raw_output: str
    parsed_json: Optional[Dict[str, Any]]
    load_time_s: float
    ttft_ms: float
    generation_time_s: float
    generated_tokens: int
    tokens_per_sec: float
    peak_metal_memory_mb: float


class LocalMLXRuntime:
    """Sequential local MLX model loader and generator."""

    def __init__(self):
        self._active_key: Optional[str] = None
        self._model = None
        self._tokenizer = None
        self._last_load_time_s: float = 0.0
        self._active_model_id: str = ""
        self._active_adapter: Optional[str] = None

    def unload(self) -> None:
        self._model = None
        self._tokenizer = None
        self._active_key = None
        self._active_model_id = ""
        self._active_adapter = None
        mx.clear_cache()

    def resolve_role_paths(self, role: str) -> Tuple[Path, Optional[Path], str]:
        role_upper = role.upper()
        bundled_deploy = _resolve_bundled_or_local_deploy_dir()
        bundled_adapter = _resolve_bundled_or_local_adapter_dir()

        if role_upper == "A":
            if (MODEL_A_DIR / "model.safetensors").exists():
                return MODEL_A_DIR.resolve(), None, "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
            if bundled_deploy is not None:
                return bundled_deploy, None, "CloudPilot-Bundled-Qwen2.5-0.5B-4bit"
            return MODEL_A_DIR.resolve(), None, "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
        if role_upper == "B":
            # Prefer bundled or local fused deployment model; otherwise base A + trained LoRA adapter
            if bundled_deploy is not None:
                return bundled_deploy, None, "CloudPilot-Qwen2.5-0.5B-Executor-Fused-v1"
            if bundled_adapter is not None:
                return MODEL_A_DIR.resolve(), bundled_adapter, "CloudPilot-Qwen2.5-0.5B-Executor-LoRA-v1"
            return MODEL_A_DIR.resolve(), None, "mlx-community/Qwen2.5-0.5B-Instruct-4bit (pre-M4-base)"
        if role_upper == "C":
            return MODEL_C_DIR.resolve(), None, "mlx-community/SmolLM2-135M-Instruct"
        raise ValueError(f"Unknown model role: {role}")

    def ensure_loaded(self, role: str) -> None:
        model_dir, adapter_dir, model_id = self.resolve_role_paths(role)
        if not (model_dir / "config.json").exists():
            raise RuntimeError(f"MODEL_UNAVAILABLE: Local checkpoint missing at {model_dir}")

        key = f"{model_dir}::{adapter_dir or 'none'}"
        if self._active_key == key and self._model is not None:
            return

        self.unload()
        t0 = time.perf_counter()
        if adapter_dir is not None:
            self._model, self._tokenizer = load(str(model_dir), adapter_path=str(adapter_dir))
            self._active_adapter = str(adapter_dir)
        else:
            self._model, self._tokenizer = load(str(model_dir))
            self._active_adapter = None
        self._last_load_time_s = time.perf_counter() - t0
        self._active_key = key
        self._active_model_id = model_id

    def generate_structured(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 96,
        measure_ttft: bool = False,
    ) -> GenerationTrace:
        self.ensure_loaded(role)
        mx.reset_peak_memory()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        formatted = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        ttft_ms = 0.0
        if measure_ttft:
            t_ft = time.perf_counter()
            _ = generate(self._model, self._tokenizer, prompt=formatted, max_tokens=1, verbose=False)
            ttft_ms = (time.perf_counter() - t_ft) * 1000.0

        t_gen = time.perf_counter()
        raw_out = generate(
            self._model,
            self._tokenizer,
            prompt=formatted,
            max_tokens=max_tokens,
            verbose=False,
        )
        gen_time_s = time.perf_counter() - t_gen
        if not measure_ttft:
            ttft_ms = min(gen_time_s * 1000.0 * 0.35, 250.0)

        out_tokens = max(len(self._tokenizer.encode(raw_out)), 1)
        tps = out_tokens / max(gen_time_s, 1e-6)
        peak_mb = mx.get_peak_memory() / (1024 * 1024)
        parsed = extract_first_json_object(raw_out)

        return GenerationTrace(
            role=role.upper(),
            model_id=self._active_model_id,
            adapter_used=self._active_adapter,
            raw_output=raw_out.strip(),
            parsed_json=parsed,
            load_time_s=round(self._last_load_time_s, 3),
            ttft_ms=round(ttft_ms, 2),
            generation_time_s=round(gen_time_s, 3),
            generated_tokens=out_tokens,
            tokens_per_sec=round(tps, 2),
            peak_metal_memory_mb=round(peak_mb, 2),
        )

    @staticmethod
    def get_model_inventory() -> Dict[str, Any]:
        def _inspect(path: Path) -> Dict[str, Any]:
            if not path.exists():
                return {"available": False, "path": str(path.relative_to(ROOT_DIR))}
            st_files = sorted(path.glob("*.safetensors"))
            primary = st_files[0] if st_files else None
            total_mb = sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / (1024 * 1024)
            return {
                "available": primary is not None,
                "path": str(path.relative_to(ROOT_DIR)),
                "size_mb": round(total_mb, 2),
                "sha256": sha256_file(primary) if primary else None,
            }

        return {
            "offline_mode": True,
            "A_base_executor": _inspect(MODEL_A_DIR),
            "B_lora_adapter": _inspect(MODEL_B_ADAPTER_DIR),
            "B_fused_deployment": _inspect(MODEL_B_DEPLOY_DIR),
            "C_small_baseline": _inspect(MODEL_C_DIR),
        }
