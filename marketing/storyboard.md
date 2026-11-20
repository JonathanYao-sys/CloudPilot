# CloudPilot — Voiced Promotional Video Storyboard & Narration Script (`marketing/storyboard.md`)

> **Output Video:** `marketing/exports/CloudPilot_Promo.mp4` (`5.59 MiB` / `5,860,554 bytes`, `155.06 seconds`, `1920x1080` H.264 + 44.1 kHz Stereo AAC Mandarin Voice Track, `mean_volume: -21.0 dB`, `max_volume: -5.7 dB`)  
> **Companion Subtitles:** `marketing/exports/CloudPilot_Promo.srt` (12 time-aligned SRT entries) + Burned-in high-contrast bilingual captions  
> **Raw Continuous Live App Recording:** `marketing/footage/live_app_recording.mp4` (`1.50 MiB` / `1,569,848 bytes`, 36 sequential live interactive frames)  
> **Voice Synthesis:** 100% offline macOS Mandarin TTS (`/usr/bin/say -v Tingting -r 210`) synchronized chapter-by-chapter with live recorded `CloudPilot.app` frames and A/B/C benchmark charts (`agent.md` Section 15).

## Six Voiced Chapters: "What the Product Is & What Engineering Work Was Done"

| Chapter | Timecode | Visual Footage | Full Spoken Mandarin Narration (`Tingting` Offline TTS) |
| --- | --- | --- | --- |
| **第一章 (1/6)：产品定位（产品是什么？）** | `00:00.0 – 00:18.6` | Live interactive frames `frame_0001..0006` (`1. Home / Chat` progressive typing of user request) | *“欢迎了解 CloudPilot 云领航。这是一款百分之百运行在苹果 Mac 本地的离线 AI 文件整理智能体。它不需要任何云端 API 密钥，也不上传任何私人文件，所有任务规划、模型推理与安全执行全部在您的 Mac 本地完成。”* |
| **第二章 (2/6)：产品四层架构（它是怎么工作的？）** | `00:18.6 – 00:45.9` | Live interactive frames `frame_0007..0017` (`2. Plan Preview` step-by-step compilation of 10-step DAG `S1..S10` and `USER APPROVED` gate) | *“在产品架构上，CloudPilot 采用四层本地安全闭环：第一层，本地规划器将自然语言指令拆解为十步结构化计划；第二层，所有写入步骤必须经过用户预览和审批；第三层，由本机微调模型生成工具调用；第四层，由确定性沙盒执行非破坏性复制，并对每个文件进行 SHA-256 哈希校验。”* |
| **第三章 (3/6)：实机断网执行演示** | `00:45.9 – 01:10.5` | Live interactive frames `frame_0018..0029` (`3. Execution Monitor` real-time streaming of Model B tool calls `S1..S10` at `168 tok/s` with network sockets blocked) | *“现在您看到的是在彻底封锁网络连接的实机环境下，应用调用内置微调模型 Model B 的实时执行过程。模型在苹果 M4 Metal GPU 上以每秒 168 个 token 的速度流式输出工具调用，自动创建分类目录、安全复制学习文档、笔记和表格，全部通过哈希校验并生成审计清单。”* |
| **第四章 (4/6)：我们做了什么 ① — 本地数据集与本机 MLX 微调** | `01:10.5 – 01:36.0` | Live frame `frame_0030` + `04_local_models.png` & `03_execution_monitor.png` (`265.18 MiB` fused `model.safetensors` & `5.61 MiB` LoRA `adapters.safetensors`) | *“在工程研发中，我们坚持零云端算力。我们在本机合成并规则校验了 1320 条覆盖八大任务族的零泄漏数据集；直接在这台 24 GB 内存的 M4 Mac 上，使用 Apple MLX 完成 160 步 LoRA 微调训练并融合导出部署权重，验证集损失从 3.728 降至最低 0.348。”* |
| **第五章 (5/6)：我们做了什么 ② — 三模型评测与双层安全验证** | `01:36.0 – 02:09.4` | Real A/B/C benchmark charts (`accuracy_comparison.png`, `family_breakdown.png`, `latency_memory_comparison.png`) | *“我们对基座模型 A、本机微调模型 B 和独立小模型 C 进行了同机离线评测。微调后，模型 B 的工具精确接地率从 56.25% 提升至 95.31%；在不依赖规则拦截器的纯模型安全测试中，模型 B 自身对路径穿越和未授权覆盖的拒答率从 0% 提升到 92.86%；配合第二层确定性策略校验器，16 项越权攻击被百分之百拦截。”* |
| **第六章 (6/6)：我们做了什么 ③ — 自包含 DMG 打包与自动化交付** | `02:09.4 – 02:35.0` | Live interactive frames `frame_0031..0036` (`5. Security & Settings` + `6. SQLite Audit History` streaming audit events `#1..#5`) | *“最后，我们将原生 SwiftUI 应用、独立 Python 3.13 解释器、MLX 运行时和微调权重全部打包进 487 兆的 DMG 安装包，验证了在干净 Mac 环境下断网即可独立运行；并通过任务调度器、26 项自动化测试和 Git 检查点，完成了中英文档、静态网站与 GitHub Release 全套交付。”* |
