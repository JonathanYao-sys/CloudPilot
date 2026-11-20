#!/usr/bin/env bash
set -euo pipefail
RES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export CLOUDPILOT_OFFLINE_ONLY=1
export CLOUDPILOT_BUNDLED_MODEL_DIR="${RES_DIR}/model/deployment"
export CLOUDPILOT_BUNDLED_ADAPTER_DIR="${RES_DIR}/model/adapters"
export PYTHONPATH="${RES_DIR}/backend:/Users/yao/CloudPilot/.venv/lib/python3.13/site-packages"
cd "${RES_DIR}/backend"
exec "/Users/yao/CloudPilot/.venv/bin/python" -m app.local_executor.orchestration_loop "$@"
