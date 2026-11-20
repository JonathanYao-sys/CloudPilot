# CloudPilot Local Executor Dataset Card (`DATASET_CARD.md`)

> **Provenance:** 100% locally synthesized and rule-validated on Apple M4 MacBook Air (`training/data_pipeline/generate_dataset.py`)  
> **Random Seed:** `20261120`  
> **Cloud LLM / External Labeling Usage:** **NONE (0 remote calls)**  
> **License:** Apache-2.0

## 1. Dataset Summary & Split Integrity

| Split | File | Example Count | Families Covered | SHA-256 Checksum |
| --- | --- | --- | --- | --- |
| **Train** | `training/datasets/train.jsonl` | `1000` | 8 / 8 (125 each) | `60f7b6c9069bc6b1ff537091329987aa143141c6cf15f42560cdfee76292e3ce` |
| **Validation** | `training/datasets/validation.jsonl` | `160` | 8 / 8 (20 each) | `e2af239ab3f6ef015b4e9bb6e509f026dce70b070a8a3e1fe6c526dcc57c268b` |
| **Test (Frozen)** | `training/datasets/test.jsonl` | `160` | 8 / 8 (20 each) | `0c53993d810169f23272731aa2d82899593c96e10b1fd898d7ef7d2fe4fc0837` |
| **Total** | — | **`1320`** | **8 families** | — |

## 2. Eight Required Task Families (`agent.md` Section 9)

1. **`family_1_tool_choice`**: Correct tool choice and typed arguments (`create_folder`, `get_file_info`, `list_files`).
2. **`family_2_grounded_copy`**: Grounded file selection and exact safe relative paths (`copy_file` with `on_conflict="skip"`).
3. **`family_3_step_dependencies`**: Step dependencies and current-state interpretation (`verify_file` and `generate_manifest`).
4. **`family_4_ambiguity_abstention`**: Ambiguity/wildcard handling and structured abstention (`abstain`).
5. **`family_5_error_classification`**: Missing source detection and structured error reporting (`report_error` with `FILE_NOT_FOUND`).
6. **`family_6_permission_rejection`**: Unapproved overwrite refusal (`abstain` with `PERMISSION_DENIED`).
7. **`family_7_idempotent_replay`**: Idempotent replay and duplicate destination handling (`on_conflict="skip"`).
8. **`family_8_adversarial_safety`**: Path traversal rejection (`UNSAFE_PATH`) and prompt-injection filenames treated as inert data.

## 3. Anti-Leakage & Privacy Guarantees

- **Disjoint Domain Vocabularies:** `train` uses academic/coursework templates, `validation` uses design/studio templates, and `test` uses finance/engineering/audit templates.
- **Measured Prompt Overlap:**
  - `train ∩ validation = 0`
  - `train ∩ test = 0`
  - `validation ∩ test = 0`
- **Privacy Scan:** `CLEAN (0 personal paths or secrets)`.
