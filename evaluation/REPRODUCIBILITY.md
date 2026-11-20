# CloudPilot Benchmark Reproducibility Guide (`REPRODUCIBILITY.md`)

## 1. Exact Offline Reproduction Commands

All evaluations run 100% locally on the user's Apple M4 Mac with network access disabled for model loading:

```bash
# 1. Regenerate and validate the frozen test split (seed=20261120):
HF_HUB_OFFLINE=1 .venv/bin/python training/data_pipeline/generate_dataset.py
HF_HUB_OFFLINE=1 .venv/bin/python training/data_pipeline/validate_dataset.py

# 2. Run the three-model (A/B/C) evaluation harness and regenerate charts:
HF_HUB_OFFLINE=1 .venv/bin/python evaluation/suites/run_abc_evaluation.py

# 3. Verify all benchmark deliverables and assertions via pytest:
HF_HUB_OFFLINE=1 .venv/bin/pytest tests/test_m6_benchmarks.py -v
```

## 2. Evaluation Conditions & Controls

- **Matched Prompt & Decode Settings:** Models A, B, and C receive the exact same system prompt (`EXECUTOR_SYSTEM_PROMPT`), JSON user payload, greedy/default MLX decoding, and `max_tokens=96`.
- **Sequential Model Loading:** Each model is loaded cleanly after `mx.clear_cache()` so earlier models do not pollute unified memory measurements.
- **Deterministic Scoring:** Every model output is scored by deterministic JSON parsing and exact AST/field comparison (`score_prediction` in `evaluation/suites/run_abc_evaluation.py`)—no LLM-as-a-judge or cloud grading is used.
