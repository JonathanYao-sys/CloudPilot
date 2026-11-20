# CloudPilot — User Guide / 用户使用指南 (`docs/user_guide.md`)

## 第一部分：中文用户指南 (Chinese User Guide)

### 1. 核心设计理念：先预览审批，再本地执行
CloudPilot 严格遵循 **“零云端传输、零静默覆盖、先审批后执行”** 的安全原则：
- **不索要任何云端 API Key：** 打开应用即可直接使用内置的 Apple MLX 本地微调模型（`CloudPilot-Qwen2.5-0.5B-Executor-LoRA-v1`）。
- **默认非破坏性复制 (`copy_file`)：** 整理文件时默认将源文件安全复制到目标分类文件夹（`on_conflict="skip"`），绝不删除或覆盖您的原始文件。
- **逐文件 SHA-256 校验 (`verify_file`)：** 每个文件复制完成后，系统都会自动比对源文件与目标文件的 SHA-256 哈希值，并生成 `organization_manifest.json` 审计清单。

### 2. 六大功能界面说明
1. **Home / Chat（离线任务首页）：** 设置授权的本地工作区路径，输入自然语言文件整理指令。
2. **Plan Preview（计划预览与审批）：** 查看 Local Planner 生成的分步执行计划（`s1`, `s2`, ...），清楚区分“只读/校验步骤”与“写入步骤”。
3. **Execution Monitor（执行监控）：** 实时查看微调模型 Model B 的 JSON 工具调用输出、Policy Validator 安全检查结果以及文件 SHA-256 校验状态。
4. **Local Models（本地模型库）：** 查看本地存储的 P / B / A / C 四个模型角色、磁盘占用（MB）及 SHA-256 校验值。
5. **Settings & Privacy（安全与隐私设置）：** 查看沙盒边界策略、允许的工具白名单及离线环境变量（`HF_HUB_OFFLINE=1`）。
6. **Audit History（SQLite 审计历史）：** 查看持久化的任务执行记录与状态变迁（`AWAITING_APPROVAL` → `RUNNING` → `COMPLETED`）。

---

## Part 2: English User Guide & CLI Workflow

### 1. First-Run Offline Walkthrough

1. Launch `CloudPilot.app` or use the local CLI with Wi-Fi / network disconnected.
2. Point the workspace path to a test folder (for example, `tmp_sandbox/my_study_files`).
3. Enter a task request:
   > *"Organize my study PDFs, markdown notes, and CSV spreadsheets into category folders and verify checksums."*
4. Click **Generate Local Plan Preview**. Review the generated steps in **Plan Preview**:
   - `create_folder` creates category directories (`PDF_Docs`, `Notes`, `Data_Sheets`).
   - `copy_file` copies each file with `on_conflict: "skip"`.
   - `verify_file` checks the copied file's SHA-256 hash against the original file.
   - `generate_manifest` writes `organization_manifest.json`.
5. Click **Approve & Execute with Model B**. Inspect the verified results in **Execution Monitor** and **Audit History**.

### 2. Command-Line Interface (CLI) Usage

You can also run the exact same offline workflow from the terminal:

```bash
# Draft an unapproved plan preview (Dry-Run):
HF_HUB_OFFLINE=1 .venv/bin/python -m app.local_executor.orchestration_loop plan \
  --workspace ./tmp_sandbox/demo_ws \
  --request "Organize my PDFs and notes by category"

# Approve and execute the plan offline using Fine-Tuned Model B:
HF_HUB_OFFLINE=1 .venv/bin/python -m app.local_executor.orchestration_loop run \
  --workspace ./tmp_sandbox/demo_ws \
  --request "Organize my PDFs and notes by category" \
  --role B

# Inspect the SQLite audit log for the workspace:
HF_HUB_OFFLINE=1 .venv/bin/python -m app.local_executor.orchestration_loop history \
  --workspace ./tmp_sandbox/demo_ws
```

### 3. Known MVP Limitations

- **Bounded Tool Scope:** The MVP intentionally supports only the 6 safe file-organization tools (`list_files`, `get_file_info`, `create_folder`, `copy_file`, `verify_file`, `generate_manifest`). Arbitrary shell execution, file deletion, system settings modification, and browser automation are excluded by design.
- **Top-Level Workspace Organization:** The default planner organizes top-level files within the selected workspace root into category or user-named folders to prevent recursive copy loops.
