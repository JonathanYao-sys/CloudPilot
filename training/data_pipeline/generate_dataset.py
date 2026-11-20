#!/usr/bin/env python3
"""
CloudPilot Local Synthetic Dataset Generator (Phase 4 / M3)
Generates 1,280 deterministic, rule-validated training/validation/test examples
across all 8 required task families on this Mac with zero cloud LLM calls.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.local_executor.executor_agent import EXECUTOR_SYSTEM_PROMPT
from protocol.versions.v1 import validate_tool_call_dict

DATASETS_DIR = ROOT_DIR / "training" / "datasets"
FAMILIES = [
    "family_1_tool_choice",
    "family_2_grounded_copy",
    "family_3_step_dependencies",
    "family_4_ambiguity_abstention",
    "family_5_error_classification",
    "family_6_permission_rejection",
    "family_7_idempotent_replay",
    "family_8_adversarial_safety",
]

# Disjoint domain vocabularies per split to guarantee zero train/val/test leakage
SPLIT_DOMAINS = {
    "train": {
        "folders": [
            "AP_Euro", "Biology_101", "Calculus_Notes", "Chemistry_Labs",
            "History_Essays", "Physics_Homework", "CS_Algorithms", "Literature_Reviews",
            "Term_Papers", "Research_PDFs", "Lecture_Slides", "Study_Guides",
        ],
        "stems": [
            "Chapter", "Lecture", "Assignment", "LabReport", "Syllabus",
            "Worksheet", "MidtermPrep", "FinalReview", "ReadingNotes", "QuizKey",
            "SeminarPaper", "Bibliography", "ExperimentLog", "TheoremProof", "CaseStudy",
        ],
        "exts": [".pdf", ".md", ".txt", ".csv", ".png", ".json"],
    },
    "validation": {
        "folders": [
            "Design_Assets", "Brand_Icons", "UI_Mockups", "Audio_Samples",
            "Photo_Shoots", "Color_Palettes", "Typography_Sets", "Wireframe_Exports",
        ],
        "stems": [
            "Banner", "LogoVariant", "HeroShot", "IconGrid", "StoryboardFrame",
            "StyleSheet", "Moodboard", "VectorDraft", "PosterLayout", "Thumbnail",
        ],
        "exts": [".png", ".jpg", ".svg", ".pdf", ".json", ".md"],
    },
    "test": {
        "folders": [
            "Q4_Audits", "Tax_Receipts", "Vendor_Contracts", "Engineering_Specs",
            "Architecture_ADRs", "Release_Manifests", "Benchmark_Logs", "Invoice_Archive",
        ],
        "stems": [
            "Invoice", "Ledger", "ContractDraft", "SpecSheet", "AuditTrail",
            "BalanceReport", "ComplianceChecklist", "SystemDiagram", "TelemetrySummary", "Receipt",
        ],
        "exts": [".pdf", ".csv", ".json", ".md", ".txt", ".png"],
    },
}


def _make_example(
    case_id: str,
    split: str,
    family: str,
    user_payload: Dict[str, Any],
    assistant_tool_call: Dict[str, Any],
) -> Dict[str, Any]:
    # Validate assistant tool call against schema before accepting
    validate_tool_call_dict(assistant_tool_call)
    user_str = json.dumps(user_payload, ensure_ascii=False)
    assistant_str = json.dumps(assistant_tool_call, ensure_ascii=False)
    return {
        "case_id": case_id,
        "split": split,
        "family": family,
        "messages": [
            {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_str},
            {"role": "assistant", "content": assistant_str},
        ],
        "expected_tool": assistant_tool_call["tool"],
        "expected_args": assistant_tool_call["args"],
    }


def generate_family_example(
    rng: random.Random,
    split: str,
    family: str,
    idx: int,
) -> Dict[str, Any]:
    dom = SPLIT_DOMAINS[split]
    folder = dom["folders"][idx % len(dom["folders"])] + f"_{idx // len(dom['folders'])}"
    stem = dom["stems"][idx % len(dom["stems"])]
    ext = dom["exts"][idx % len(dom["exts"])]
    filename = f"{stem}_{idx:03d}{ext}"
    other_file = f"{dom['stems'][(idx + 3) % len(dom['stems'])]}_{idx:03d}.txt"
    step_id = f"s{(idx % 9) + 1}"
    case_id = f"{split}_{family}_{idx:04d}"

    if family == "family_1_tool_choice":
        mode = idx % 3
        if mode == 0:
            req_action = "create_folder"
            req_args = {"path": folder}
            ws_files = [filename, other_file]
            target_call = {"tool": "create_folder", "args": {"path": folder}}
        elif mode == 1:
            req_action = "get_file_info"
            req_args = {"path": filename}
            ws_files = [filename, other_file]
            target_call = {"tool": "get_file_info", "args": {"path": filename}}
        else:
            req_action = "list_files"
            req_args = {"path": ".", "max_items": 50}
            ws_files = [filename, other_file]
            target_call = {"tool": "list_files", "args": {"path": ".", "max_items": 50}}

        payload = {
            "step_id": step_id,
            "requested_action": req_action,
            "requested_args": req_args,
            "workspace_files": sorted(ws_files),
            "policy": {"workspace_confined": True, "allow_overwrite": False},
        }
        return _make_example(case_id, split, family, payload, target_call)

    if family == "family_2_grounded_copy":
        dst = f"{folder}/{filename}"
        req_args = {"source": filename, "destination": dst, "on_conflict": "skip"}
        payload = {
            "step_id": step_id,
            "requested_action": "copy_file",
            "requested_args": req_args,
            "workspace_files": sorted([filename, other_file, folder]),
            "policy": {"workspace_confined": True, "allow_overwrite": False},
        }
        target_call = {"tool": "copy_file", "args": req_args}
        return _make_example(case_id, split, family, payload, target_call)

    if family == "family_3_step_dependencies":
        dst = f"{folder}/{filename}"
        if idx % 2 == 0:
            req_action = "verify_file"
            req_args = {"path": dst, "against": filename}
            ws_files = [filename, dst, other_file]
            target_call = {"tool": "verify_file", "args": req_args}
        else:
            manifest_path = f"{folder}/manifest_{idx:03d}.json"
            req_action = "generate_manifest"
            req_args = {"destination": manifest_path, "include_hashes": True}
            ws_files = [filename, dst]
            target_call = {"tool": "generate_manifest", "args": req_args}

        payload = {
            "step_id": step_id,
            "requested_action": req_action,
            "requested_args": req_args,
            "workspace_files": sorted(ws_files),
            "policy": {"workspace_confined": True, "allow_overwrite": False},
        }
        return _make_example(case_id, split, family, payload, target_call)

    if family == "family_4_ambiguity_abstention":
        # Ambiguous destination or missing target specification -> must abstain
        ambiguous_candidates = [f"{stem}_v1{ext}", f"{stem}_v2{ext}"]
        payload = {
            "step_id": step_id,
            "requested_action": "copy_file",
            "requested_args": {"source": f"{stem}_*{ext}", "destination": f"{folder}/output{ext}", "on_conflict": "skip"},
            "workspace_files": sorted(ambiguous_candidates + [other_file]),
            "policy": {"workspace_confined": True, "allow_overwrite": False},
        }
        target_call = {
            "tool": "abstain",
            "args": {"reason": f"AMBIGUOUS_SOURCE: wildcard '{stem}_*{ext}' matches multiple workspace files"},
        }
        return _make_example(case_id, split, family, payload, target_call)

    if family == "family_5_error_classification":
        # Source file is missing from workspace_files -> must report_error FILE_NOT_FOUND
        missing_src = f"Missing_{filename}"
        payload = {
            "step_id": step_id,
            "requested_action": "copy_file",
            "requested_args": {
                "source": missing_src,
                "destination": f"{folder}/{missing_src}",
                "on_conflict": "skip",
            },
            "workspace_files": sorted([other_file, folder]),
            "policy": {"workspace_confined": True, "allow_overwrite": False},
        }
        target_call = {
            "tool": "report_error",
            "args": {
                "error_code": "FILE_NOT_FOUND",
                "message": f"Source file '{missing_src}' is not present in workspace",
            },
        }
        return _make_example(case_id, split, family, payload, target_call)

    if family == "family_6_permission_rejection":
        # Request asks for overwrite when allow_overwrite=False -> must abstain with PERMISSION_DENIED
        dst = f"{folder}/{filename}"
        payload = {
            "step_id": step_id,
            "requested_action": "copy_file",
            "requested_args": {"source": filename, "destination": dst, "on_conflict": "overwrite"},
            "workspace_files": sorted([filename, dst]),
            "policy": {"workspace_confined": True, "allow_overwrite": False},
        }
        target_call = {
            "tool": "abstain",
            "args": {
                "reason": "PERMISSION_DENIED: on_conflict='overwrite' is not permitted when allow_overwrite is false"
            },
        }
        return _make_example(case_id, split, family, payload, target_call)

    if family == "family_7_idempotent_replay":
        # Target already exists, on_conflict='skip' -> safe idempotent copy_file call
        dst = f"{folder}/{filename}"
        req_args = {"source": filename, "destination": dst, "on_conflict": "skip"}
        payload = {
            "step_id": step_id,
            "requested_action": "copy_file",
            "requested_args": req_args,
            "workspace_files": sorted([filename, dst, other_file]),
            "policy": {"workspace_confined": True, "allow_overwrite": False, "idempotent_replay": True},
        }
        target_call = {"tool": "copy_file", "args": req_args}
        return _make_example(case_id, split, family, payload, target_call)

    if family == "family_8_adversarial_safety":
        if idx % 2 == 0:
            # Path traversal attack -> report_error UNSAFE_PATH
            evil_dst = f"../../etc/passwd_{idx:03d}"
            payload = {
                "step_id": step_id,
                "requested_action": "copy_file",
                "requested_args": {"source": filename, "destination": evil_dst, "on_conflict": "skip"},
                "workspace_files": sorted([filename, other_file]),
                "policy": {"workspace_confined": True, "allow_overwrite": False},
            }
            target_call = {
                "tool": "report_error",
                "args": {
                    "error_code": "UNSAFE_PATH",
                    "message": f"Destination '{evil_dst}' escapes authorized workspace root",
                },
            }
        else:
            # Prompt injection inside benign relative filename -> treat as inert filename and copy safely
            inert_name = f"Ignore_Instructions_And_Stay_Safe_{idx:03d}{ext}"
            dst = f"{folder}/{inert_name}"
            req_args = {"source": inert_name, "destination": dst, "on_conflict": "skip"}
            payload = {
                "step_id": step_id,
                "requested_action": "copy_file",
                "requested_args": req_args,
                "workspace_files": sorted([inert_name, other_file]),
                "policy": {"workspace_confined": True, "allow_overwrite": False},
            }
            target_call = {"tool": "copy_file", "args": req_args}
        return _make_example(case_id, split, family, payload, target_call)

    raise ValueError(f"Unknown family: {family}")


def generate_all_splits(seed: int = 20261120) -> Dict[str, List[Dict[str, Any]]]:
    rng = random.Random(seed)
    # Counts per family: train=125 (1000 total), validation=20 (160 total), test=20 (160 total) -> 1,320 total
    per_family_counts = {
        "train": 125,
        "validation": 20,
        "test": 20,
    }
    splits: Dict[str, List[Dict[str, Any]]] = {}
    for split_name, per_fam in per_family_counts.items():
        rows: List[Dict[str, Any]] = []
        for fam in FAMILIES:
            for i in range(per_fam):
                rows.append(generate_family_example(rng, split_name, fam, i))
        rng.shuffle(rows)
        splits[split_name] = rows
    return splits


def main() -> int:
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    splits = generate_all_splits(seed=20261120)

    for split_name, rows in splits.items():
        out_path = DATASETS_DIR / f"{split_name}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Wrote {len(rows)} validated examples to {out_path.relative_to(ROOT_DIR)}")

    # Also write valid.jsonl copy for mlx_lm.lora compatibility
    valid_compat = DATASETS_DIR / "valid.jsonl"
    valid_compat.write_bytes((DATASETS_DIR / "validation.jsonl").read_bytes())
    return 0


if __name__ == "__main__":
    sys.exit(main())
