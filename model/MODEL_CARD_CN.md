# 模型卡 (Model Card) — CloudPilot-Qwen2.5-0.5B-Executor-LoRA-v1 (模型 B · 中文版)

> **英文版模型卡：** [`model/MODEL_CARD.md`](MODEL_CARD.md)

## 1. 模型身份与本机来源

- **模型名称：** `CloudPilot-Qwen2.5-0.5B-Executor-LoRA-v1`（模型 B）
- **父基座模型（模型 A）：** `mlx-community/Qwen2.5-0.5B-Instruct-4bit`（4-bit 量化 MLX 权重）
- **基座权重 SHA-256：** `ddffab9cbc7bf6dde941c6724841eeca8981fcfa81ca20ff8efff1396326d153`
- **开源许可证：** Apache-2.0
- **本机训练硬件：** Apple M4 MacBook Air（`Mac16,12`，10 核 CPU，10 核 Metal 4 GPU，24 GB 统一内存）
- **本机训练框架：** Apple MLX (`mlx_lm.lora` & `mlx_lm.fuse`) —— **100% 本机 Metal GPU 训练（0 云端 GPU / 0 远程 API）**

## 2. 权重产物区分：LoRA 适配器 vs. 融合独立部署模型

按照 `agent.md` 第 10.7 节要求，CloudPilot 同时导出并明确区分以下两种权重形态：

| 产物形态 | 相对路径 | 文件大小 | SHA-256 校验值 | 用途说明 |
| --- | --- | --- | --- | --- |
| **LoRA 适配器权重** | `model/adapters/adapters.safetensors` | `5.61 MiB` (`5,877,295 B`) | `49b6f62a9838ff4e69b62249a7eb10ce6430d8f7a4f0ce8a3eaa43d6512b66e9` | Rank-8 轻量级微调增量权重，可叠加在基座模型 A 上加载 |
| **LoRA 适配器配置** | `model/adapters/adapter_config.json` | `1,028 B` | `3073feb99647600c1c45b9e066bf6e6b98a069d2aa53e0051c530a917338150d` | 记录微调超参数与目标层配置 |
| **融合独立部署模型** | `model/deployment/model.safetensors` | `265.18 MiB` (`278,064,766 B`) | `97cd74ed52a094ff05068216e67c48be9415cc58c4bde29cb95a3cc0983e7706` | 通过 `mlx_lm.fuse` 融合后的完整独立权重，已内置于 `CloudPilot.app` |

## 3. 本机合成数据集与训练超参数

- **训练集 (`train.jsonl`)：** `1,000` 条经规则验证的本机合成样本（平均覆盖 8 大任务族，每族 125 条）
- **验证集 (`validation.jsonl`)：** `160` 条样本（每族 20 条，仅用于训练过程中的 Loss 监控与检查点选择）
- **冻结测试集 (`test.jsonl`)：** `160` 条样本（每族 20 条，在 M3 阶段于微调前生成并冻结，训练过程从未接触，跨集重叠率为 `0`）
- **超参数配置 (`training/configs/lora_config.yaml`)：**
  - `num_layers`: `8`，`lora_parameters`: `rank=8, scale=20.0, dropout=0.0`
  - `batch_size`: `4`，`iters`: `160`，`learning_rate`: `1e-4` (Adam)，`max_seq_length`: `512`，`seed`: `42`

## 4. 本机训练收敛曲线实测

- **可训练参数量：** `0.297% (1.466M / 494.033M)`
- **本机训练耗时：** `210.05 秒`（融合导出耗时 `1.57 秒`）
- **验证集损失 (`val_loss`)：** `3.728` (iter 1) → **`0.348` (best, iter 120)** / **`0.366` (final, iter 160)**
- **训练集损失 (`train_loss`)：** `0.962` (iter 10) → **`0.070` (iter 160)**

## 5. 适用范围、安全边界与局限性

- **适用角色：** 作为 CloudPilot 离线架构中的本地执行模型（Model B），将已批准的计划步骤与工作区观测映射为 6 个白名单工具调用（`list_files`、`get_file_info`、`create_folder`、`copy_file`、`verify_file`、`generate_manifest`）或结构化拒答/报错（`abstain`、`report_error`）。
- **安全边界：** 模型的输出始终被视为不可信数据，必须通过确定性 `PolicyValidator` 二次校验后才能执行。
