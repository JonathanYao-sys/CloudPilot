# CloudPilot — Installation & Offline Provisioning Guide (`docs/installation.md`)

## 1. System & Hardware Requirements

| Requirement | Minimum Supported | Tested & Verified Baseline |
| --- | --- | --- |
| **Chip / Architecture** | Apple Silicon (M1 / M2 / M3 / M4 `arm64`) | Apple M4 (10-core CPU, 10-core Metal 4 GPU) |
| **Unified Memory (RAM)** | 8 GB Unified Memory (Sequential loading requires < 600 MB Metal RAM) | 24 GB Unified Memory |
| **Free SSD Storage** | 2.0 GB free disk space | 36.64 GB free SSD (Project footprint < 1.0 GB) |
| **Operating System** | macOS 14.0 (Sonoma) or newer | macOS `27.2.1` |
| **Internet Connection** | **Not required at runtime** (Offline-first after file installation) | Verified with network sockets disabled |

## 2. Installing the macOS Desktop Application (`.dmg`)

1. Verify the SHA-256 checksum of the installer disk image:
   ```bash
   shasum -a 256 -c release/checksums.sha256
   ```
2. Mount `release/artifacts/CloudPilot-v1.0-macOS.dmg`:
   ```bash
   hdiutil attach release/artifacts/CloudPilot-v1.0-macOS.dmg
   ```
3. Drag `CloudPilot.app` into `/Applications` (or run it directly from `release/artifacts/CloudPilot.app`).
4. **Code Signing Disclosure (`agent.md` Section 11.6):**
   - `CloudPilot.app` is signed locally with an ad-hoc macOS code signature (`codesign --force --deep --sign -`).
   - It is **not** notarized with a paid Apple Developer ID certificate. On first launch in a clean user account, right-click `CloudPilot.app` and select **Open**.

## 3. Offline Model Provisioning & Verification

All required model weights are stored locally inside the repository workspace:

- **Fine-Tuned Executor Model B (Fused Deployment):** `model/deployment/model.safetensors` (`265.18 MB`)
- **Fine-Tuned Executor Model B (LoRA Adapter):** `model/adapters/adapters.safetensors` (`5.61 MB`)
- **Base Model A (`Qwen2.5-0.5B-Instruct-4bit`):** `.hf_cache/models/Qwen2.5-0.5B-Instruct-4bit` (`278.41 MB`)
- **Small Baseline Model C (`SmolLM2-135M-Instruct`):** `.hf_cache/models/SmolLM2-135M-Instruct` (`261.19 MB`)

Verify local model availability and SHA-256 hashes while offline:

```bash
HF_HUB_OFFLINE=1 .venv/bin/python -m app.local_executor.orchestration_loop models
```

## 4. Uninstallation & Rollback

To completely remove CloudPilot and its local caches:
1. Delete `/Applications/CloudPilot.app` (if copied to `/Applications`).
2. Remove the local `.cloudpilot_state.db` file inside any sandbox test workspace you used.
3. No background daemons, kernel extensions, launch agents, or system-wide plist files are ever installed.
