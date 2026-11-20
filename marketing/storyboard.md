# CloudPilot — Promotional Video Storyboard (`marketing/storyboard.md`)

> **Output File:** `marketing/exports/CloudPilot_Promo.mp4` (`2.22 MiB` / `2,326,573 bytes`) + Continuous Live App Recording `marketing/footage/live_app_recording.mp4` (`1.50 MiB` / `1,569,848 bytes`)  
> **Resolution & Codec:** `1920x1080` (1080p Full HD), `H.264 (yuv420p)` video + `AAC` offline narration audio, `30 fps`  
> **Production Pipeline:** 100% locally recorded and rendered on Apple M4 MacBook Air. First, `CloudPilot.app --record-live-demo` runs a real offline file-organization task with network sockets blocked and captures **36 sequential live interactive window frames** (`marketing/footage/live_frames/frame_0001.png` .. `frame_0036.png`) showing progressive request typing, step-by-step DAG plan compilation (`S1..S10`), user approval transition, real-time step-by-step Model B Metal GPU log streaming (`S1..S10`), model inventory inspection, security policy checks, and row-by-row SQLite audit logging. These 36 live interactive frames are encoded into `marketing/footage/live_app_recording.mp4` and combined with the 2 benchmark/release analysis cards and macOS offline `/usr/bin/say` narration via `/opt/homebrew/bin/ffmpeg` (`agent.md` Section 15).

## Scene-by-Scene Breakdown (26 Seconds Total)

| Scene | Timecode | Visual Source | Bilingual Burned-In Caption & Narration |
| --- | --- | --- | --- |
| **Scene 1: Problem & Value Proposition** | `00:00 – 00:04` | Title Card + Real `CloudPilot.app` Home/Chat UI (`01_home_chat.png`) | **CloudPilot — Local Intelligence. Local Execution.** Organize files on macOS with 100% on-device Apple MLX AI and zero cloud API keys. / 100% 运行在 Mac 本地的离线文件整理 AI 智能体。 |
| **Scene 2: Local Architecture** | `00:04 – 00:08` | Architecture Diagram + Plan Preview Approval Gate (`02_plan_preview.png`) | **Local Planner (P) → Fine-Tuned Executor (B) → Policy Validator → Deterministic Tools.** Every plan is previewed and approved before execution. / 先预览审批，再由本地微调模型与确定性安全沙盒执行。 |
| **Scene 3: Network-Off App Execution** | `00:08 – 00:14` | Real App Execution Monitor & Local Model Inventory (`03_execution_monitor.png`, `04_local_models.png`) | **100% Offline Execution (`HF_HUB_OFFLINE=1`).** Non-destructive `copy_file` (`on_conflict='skip'`), per-file SHA-256 verification, and SQLite audit logging. / 断网环境下完成非破坏性分类复制与 SHA-256 哈希校验。 |
| **Scene 4: A/B/C Benchmark & Honest Limitations** | `00:14 – 00:21` | Real Benchmark Charts (`accuracy_comparison.png`, `family_breakdown.png`) | **On-Mac MLX LoRA Fine-Tuning Results:** Model B reaches **95.31%** exact grounding (+39.06% over Base A) at **167.87 tok/s** and **534 MB** Metal RAM. Self-run offline benchmark; bounded 6-tool MVP. |
| **Scene 5: Closing & Artifacts** | `00:21 – 00:26` | Closing Release Summary + Audit History (`06_audit_history.png`) | **Available Now:** `CloudPilot-v1.0-macOS.dmg` · `.safetensors` Weights · Full CN/EN Docs · Apache-2.0 License. |
