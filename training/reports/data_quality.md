# CloudPilot Data Quality & Validation Report (`data_quality.md`)

- **Validation Status:** `PASSED`
- **Total Validated Cases:** `1320` (`train=1000`, `validation=160`, `test=160`)
- **Schema Validation:** `100.0%` of assistant responses pass `ToolCallV1` JSON Schema and Pydantic validation.
- **Cross-Split Leakage:** `0` overlapping prompts across `train`, `validation`, and frozen `test`.
- **PII / Secret Audit:** `CLEAN (0 personal paths or secrets)`

## Tool Distribution Across Splits

```json
{
  "train": {
    "abstain": 250,
    "report_error": 188,
    "get_file_info": 42,
    "generate_manifest": 62,
    "copy_file": 312,
    "list_files": 41,
    "verify_file": 63,
    "create_folder": 42
  },
  "validation": {
    "abstain": 40,
    "list_files": 6,
    "generate_manifest": 10,
    "copy_file": 50,
    "report_error": 30,
    "create_folder": 7,
    "verify_file": 10,
    "get_file_info": 7
  },
  "test": {
    "verify_file": 10,
    "abstain": 40,
    "report_error": 30,
    "copy_file": 50,
    "list_files": 6,
    "get_file_info": 7,
    "create_folder": 7,
    "generate_manifest": 10
  }
}
```

## Family Distribution Across Splits

```json
{
  "train": {
    "family_6_permission_rejection": 125,
    "family_8_adversarial_safety": 125,
    "family_1_tool_choice": 125,
    "family_3_step_dependencies": 125,
    "family_5_error_classification": 125,
    "family_4_ambiguity_abstention": 125,
    "family_7_idempotent_replay": 125,
    "family_2_grounded_copy": 125
  },
  "validation": {
    "family_6_permission_rejection": 20,
    "family_1_tool_choice": 20,
    "family_3_step_dependencies": 20,
    "family_2_grounded_copy": 20,
    "family_4_ambiguity_abstention": 20,
    "family_5_error_classification": 20,
    "family_7_idempotent_replay": 20,
    "family_8_adversarial_safety": 20
  },
  "test": {
    "family_3_step_dependencies": 20,
    "family_6_permission_rejection": 20,
    "family_5_error_classification": 20,
    "family_7_idempotent_replay": 20,
    "family_2_grounded_copy": 20,
    "family_8_adversarial_safety": 20,
    "family_1_tool_choice": 20,
    "family_4_ambiguity_abstention": 20
  }
}
```
