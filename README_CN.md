# CloudPilot 云领航 — 100% 本地规划与本地执行的 macOS AI 智能体（中文版总览）

> **规范版本：** `agent.md` v4.0 — **LOCAL-ONLY（纯本地计算与纯本地 AI）**  
> **自动化开发工作流：** `agent.md → Orchestrator (任务调度器 orchestrator.py) → Coding Agent → progress.json + Git Checkpoints`  
> **实测主机硬件：** Apple M4 MacBook Air (`Mac16,12`, 10 核 CPU, 10 核 Metal 4 GPU, 24 GB 统一内存, macOS `27.2.1`)  
> **云端算力 / 云端 API 密钥：** **零（0 次远程调用，强制 `HF_HUB_OFFLINE=1`）**  
> **语言切换：** [English README](README.md) | **中文版 README**

---

## 一、 这个产品是什么？（Product Overview）

**CloudPilot（云领航）** 是一款完全运行在苹果 Mac 本地的离线桌面文件整理 AI 智能体：
1. **零云端依赖、零隐私泄漏：** 不需要配置任何 OpenAI / Anthropic / Google 等云端 API Key，您的文件名、目录结构、指令和审计日志永远不会离开这台 Mac。
2. **四层本地安全闭环架构：**
   - **第一层 · 本地规划器 (`Local Planner P`)：** 将用户的自然语言整理需求与当前目录文件列表转化为严格符合 JSON Schema 的有界 DAG 执行计划（`TaskPlanV1`）。
   - **第二层 · 用户预览与审批门禁 (`Plan Preview & Approval Gate`)：** 默认采用非破坏性复制 `copy_file`（`on_conflict="skip"`），所有写入操作必须先经用户预览并点击批准才会执行。
   - **第三层 · 本机微调执行模型 (`Fine-Tuned Executor Model B`)：** 在本机 Apple M4 Metal GPU 上通过 MLX LoRA 微调出的 `CloudPilot-Qwen2.5-0.5B-Executor-LoRA-v1`，根据计划步骤和工作区状态实时输出 JSON 工具调用或安全拒答。
   - **第四层 · 确定性策略校验与工具运行时 (`PolicyValidator & DeterministicToolRuntime`)：** 强制将所有路径限制在授权工作区根目录内，确定性拦截 `..` 路径穿越、外部软链接逃逸与未授权覆盖，逐个文件比对复制前后的 SHA-256 哈希值，并将全过程持久化到本地 SQLite 审计数据库（`.cloudpilot_state.db`）。

---

## 二、 我们在这个项目里具体做了什么？（Engineering Work & Seven Deliverables）

严格遵循上传的开发工作流图（`agent.md → Orchestrator → Coding Agent → progress.json + Git Checkpoints`），我们在本机完成了以下 7 项强制交付物并全部通过 26 项离线自动化测试：

| # | 交付物名称 | 本地验证路径与公网直链 | 状态 | 核心工程成果与验证证据 |
| --- | --- | --- | --- | --- |
| **1** | **本机微调模型权重 (Model B)** | LoRA 适配器：`model/adapters/adapters.safetensors` (`5.61 MiB`)<br>融合部署模型：`model/deployment/model.safetensors` (`265.18 MiB`)<br>中文模型卡：[`model/MODEL_CARD_CN.md`](model/MODEL_CARD_CN.md) | `DONE` | 在本机 Apple M4 Metal GPU 上运行 `mlx_lm.lora` 微调 160 步（耗时 `210.05s`），验证集 Loss 从 `3.728` (iter 1) 降至 **`0.348` (best, iter 120)** / **`0.366` (final, iter 160)** |
| **2** | **自包含原生 macOS 应用 (`.app` & `.dmg`)** | 应用包：`release/artifacts/CloudPilot.app`<br>安装镜像：`release/artifacts/CloudPilot-v1.0-macOS.dmg` (`487.01 MiB` / `510,661,870 B`)<br>[GitHub Release 下载](https://github.com/JonathanYao-sys/CloudPilot/releases/download/v1.0.0/CloudPilot-v1.0-macOS.dmg) | `DONE` | 原生 SwiftUI (`arm64`)，**包内自带独立 Python 3.13.18 解释器 (`python_runtime`)、MLX 运行时、265.18 MiB 微调权重与后端**；在挂载 DMG、拷贝至隔离目录、剥离环境变量 (`PATH=/usr/bin:/bin`) 并封锁网络 Socket 的干净 Mac 模拟环境下离线验收通过 |
| **3** | **中英双语用户与技术文档** | [`README_CN.md`](README_CN.md)、[`README.md`](README.md)、[`docs/user_guide.md`](docs/user_guide.md)、[`docs/architecture.md`](docs/architecture.md)、[`docs/security.md`](docs/security.md)、[`docs/offline_compliance.md`](docs/offline_compliance.md) | `DONE` | 完整涵盖中英快速开始、离线安装、架构设计、安全边界、隐私政策、故障排查与离线合规报告 |
| **4** | **GitHub 开源仓库与 Release 发布** | 仓库：[`https://github.com/JonathanYao-sys/CloudPilot`](https://github.com/JonathanYao-sys/CloudPilot)<br>Release：[`https://github.com/JonathanYao-sys/CloudPilot/releases/tag/v1.0.0`](https://github.com/JonathanYao-sys/CloudPilot/releases/tag/v1.0.0) | `DONE` | 包含 `checkpoint-M0` 至 `checkpoint-M8` 全部里程碑标签、全套自动化测试及远端 SHA-256 校验通过的 Release 资产 |
| **5** | **三模型 (A/B/C) 同机离线基准评测报告** | 中文报告：[`evaluation/EVALUATION_REPORT_CN.md`](evaluation/EVALUATION_REPORT_CN.md)<br>英文报告：[`evaluation/EVALUATION_REPORT.md`](evaluation/EVALUATION_REPORT.md)<br>中文图表：`evaluation/charts/*_cn.png` | `DONE` | 微调模型 B 精确工具接地率达 **`95.31%`**（基座 A 为 `56.25%`，小模型 C 为 `0.0%`）；**纯模型安全拒答率从 `0.0%` 提升至 `92.86%` (`26/28`)**，叠加第二层 `PolicyValidator` 后 `16/16` 越权攻击 100% 拦截；如实披露事后补测未修改 A/C 基线与自测榜单声明 |
| **6** | **静态产品发布网站（中/英双版）** | 中文版：[`website/index_cn.html`](website/index_cn.html) ([在线访问](https://jonathanyao-sys.github.io/CloudPilot/website/index_cn.html))<br>英文版：[`website/index.html`](website/index.html) ([在线访问](https://jonathanyao-sys.github.io/CloudPilot/website/)) | `DONE` | 100% 本地构建，内嵌 6 张不同界面的真实应用截图、中英评测图表与有声宣传片，零外部 CDN 依赖 |
| **7** | **中文普通话有声宣传片与实机连续录屏** | 中文有声宣传片：`marketing/exports/CloudPilot_Promo_CN.mp4` (`5.61 MiB`, `155.06s`)<br>同步字幕：`marketing/exports/CloudPilot_Promo_CN.srt`<br>实机连续交互录屏：`marketing/footage/live_app_recording.mp4` (`1.50 MiB`) | `DONE` | 由 36 帧实机连续交互操作录屏 + 全中文评测图表 + macOS 本地离线中文语音 (`Tingting`) + 内嵌同步字幕合成，清晰讲解产品定位与全部研发工作 |

---

## 三、 三步离线安装与复现指南

### 1. 安装并运行 macOS 桌面应用
1. 下载或打开 `release/artifacts/CloudPilot-v1.0-macOS.dmg`（`487.01 MiB`），将 `CloudPilot.app` 拖入 `Applications` 文件夹。
2. 首次启动如遇 macOS Gatekeeper 提示（应用已在本地完成 Ad-hoc 签名，未做付费 Apple Developer ID 公证），请右键点击 `CloudPilot.app` 选择 **“打开 (Open)”**。
3. 选择一个本地测试文件夹作为沙盒工作区，输入整理指令，点击 **Generate Local Plan Preview** 预览计划，确认后点击 **Approve & Execute with Bundled Model B** 即可在完全断网状态下完成整理与 SHA-256 校验。

### 2. 在终端离线复现全套工作流与 26 项门禁测试
```bash
# 1. 查看 Orchestrator 任务调度器状态与 M0..M8 检查点
.venv/bin/python orchestrator.py status

# 2. 在完全断网模式 (HF_HUB_OFFLINE=1) 下运行全套 26 项 Pytest 自动化门禁测试
HF_HUB_OFFLINE=1 .venv/bin/pytest -v
```
