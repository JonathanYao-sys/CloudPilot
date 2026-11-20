# CloudPilot — Final Delivery Manifest (`release/DELIVERY_MANIFEST.md`)

> **Specification:** `agent.md` v4.0 — **LOCAL-ONLY**  
> **Overall Release Status:** **`PARTIAL / NOT RELEASED`** (**All 7 Deliverables Built & Verified 100% Locally on Apple M4 Mac**; Public Internet Upload / Hosting Gated on Explicit User Authorization per `agent.md` Section 2.2 & Section 16)  
> **Checksum Manifest:** `release/checksums.sha256`

## 1. Seven Mandatory Deliverables Verification Matrix

| # | Deliverable | Local Build Status | Public Publication Status | Verified Local Path | Size & SHA-256 Checksum | Test Evidence | Blockers & Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **1** | **Fine-Tuned Model Weights (Model B)** | `DONE` | `BLOCKED — AWAITING_USER_PUBLICATION_AUTH` | `model/adapters/adapters.safetensors` & `model/deployment/model.safetensors` (+ `model/MODEL_CARD.md`) | Adapter: `5.61 MB` (`49b6f62a9838ff4e69b62249a7eb10ce6430d8f7a4f0ce8a3eaa43d6512b66e9`)<br>Fused: `265.18 MB` (`97cd74ed52a094ff05068216e67c48be9415cc58c4bde29cb95a3cc0983e7706`) | `tests/test_m4_finetuned_model.py` (`3/3 PASSED`); `logs/m4_lora_train.log`; `training/reports/training_metrics.json` | None locally. Public weight upload awaits user approval & repo target. |
| **2** | **macOS Application (`.app` & `.dmg` with Bundled Weights)** | `DONE` | `BLOCKED — AWAITING_USER_PUBLICATION_AUTH` | `release/artifacts/CloudPilot.app` & `release/artifacts/CloudPilot-v1.0-macOS.dmg` (bundling `Contents/Resources/model/deployment/model.safetensors`, `adapters.safetensors`, & `backend/`) | DMG: `261 MB` (`c8c69b82ef69907ea06c7e85e6642790a564f494d5f4ae08b6560e560e454531`)<br>Ad-hoc locally signed (`codesign --sign -`; disclosed unnotarized) | `tests/test_m5_macos_app_and_dmg.py` (`3/3 PASSED`): mounts DMG, copies `CloudPilot.app` to isolated temp dir outside `/Users/yao/CloudPilot`, unmounts DMG, and verifies offline execution from bundled weights | None locally. Optional Apple Developer ID notarization & GitHub release upload await user credentials/consent. |
| **3** | **User & Technical Instructions (CN/EN)** | `DONE` | `DONE` (Local Repo) | `README.md`, `docs/architecture.md`, `docs/installation.md`, `docs/user_guide.md`, `docs/security.md`, `docs/privacy.md`, `docs/troubleshooting.md`, `docs/offline_compliance.md` | 12 Markdown files + `docs/environment_report.json` | `tests/test_m0_hardware_and_models.py` (`4/4 PASSED`) & `tests/test_m7_release_and_media.py` | Complete. |
| **4** | **GitHub Repository / Tagged Release** | `DONE` (Local Git + Checkpoints) | `BLOCKED — ACCOUNT/PERMISSION` | Local Git repository `/Users/yao/CloudPilot` with tags `checkpoint-M0` .. `checkpoint-M7` | `release/checksums.sha256` verified via `shasum -a 256 -c` | `orchestrator.py status` & Git tag audit | Per `agent.md` Section 2.2 & Section 13: pushing to a public GitHub remote requires explicit user approval of repo URL & visibility. |
| **5** | **Three-Model Benchmark Report (A/B/C) + Pre-Train Baseline** | `DONE` | `DONE` (Local Repo) | Pre-Train A/C Freeze: `evaluation/baselines/pretrain_ac_baseline.json` & `PRETRAIN_BASELINE_REPORT.md`<br>Post-Train A/B/C: `evaluation/EVALUATION_REPORT.md`, `evaluation/results.csv`, `evaluation/raw_results/*.jsonl`, `evaluation/charts/*.png` | `pretrain_ac_baseline.json`: `cf07a59255a4739559521f3bd826121191fdfc9183826a9f5679e4618d2bfa74`<br>`results.csv`: `f7fc58751039d001d2a1c9451a87c524323bf75132314aaf45a85f0872c5df7a` | `tests/test_m3_dataset_quality.py` (`3/3 PASSED`) & `tests/test_m6_benchmarks.py` (`3/3 PASSED`): Model B `95.31%` grounding & **`92.86%` model-only safety refusal** (vs `0.0%` on Base A & Small C), plus `16/16` Layer 2 `PolicyValidator` defense-in-depth | Complete. Self-run benchmark status & model-only vs rule-validator separation truthfully documented. |
| **6** | **Product Launch Website** | `DONE` | `BLOCKED — AWAITING_USER_PUBLICATION_AUTH` | `website/index.html`, `website/styles.css`, `website/app.js`, `website/assets/*.png` | `index.html`: `266d505af102958aabfcecfab1103f1201449e98ba0b0e7175cc63b857775a3c` (6 distinct verified UI screenshots + 3 benchmark charts, 0 CDN dependencies) | `tests/test_m7_release_and_media.py` (verifies 6 unique screenshot SHA-256 hashes, local asset existence, zero external URLs) | Static files built & verified locally. Public static hosting awaits user approval (`M8`). |
| **7** | **Promotional Video (`.mp4`)** | `DONE` | `BLOCKED — AWAITING_USER_PUBLICATION_AUTH` | `marketing/exports/CloudPilot_Promo.mp4` (+ `marketing/storyboard.md`) | `1,277.5 KB`, `1920x1080` H.264 + AAC, `31.97s` (`ffbce1b5aabea6120b89f30d01107c2a32709c22c37b5b984a2063088d13da71`) | `ffprobe` stream/codec verification in `tests/test_m7_release_and_media.py` | Playable 1080p MP4 rendered locally from distinct real screenshots & charts. Public upload awaits user approval (`M8`). |

## 2. Milestone & Gate Completion Summary

- **M0 (Phase 0 & 1 / Gate 0 & 1):** `PASSED` (`checkpoint-M0`)
- **M1 (Phase 2 / Gate 2):** `PASSED` (`checkpoint-M1`)
- **M2 (Phase 3 / Gate 3):** `PASSED` (`checkpoint-M2`)
- **M3 (Phase 4 / Gate 4):** `PASSED` (`checkpoint-M3`)
- **M4 (Phase 5 / Gate 5):** `PASSED` (`checkpoint-M4`)
- **M5 (Phase 6 / Gate 6):** `PASSED` (`checkpoint-M5`)
- **M6 (Phase 7 / Gate 7):** `PASSED` (`checkpoint-M6`)
- **M7 (Phase 8, 9 & 10 Local Build / Gate 8, 9, 10 Local):** `PASSED` (`checkpoint-M7`)
- **M8 (Public Internet Upload & Hosting / Gate 8 & 9 Public):** `BLOCKED` on user approval gate (`agent.md` Section 2.2).
