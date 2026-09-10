#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# gemini-enterprise-overage-guard 원클릭 실행 스크립트

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

VENV_DIR="${SCRIPT_DIR}/.venv"

if [ ! -d "${VENV_DIR}" ]; then
  echo "[INFO] 파이썬 가상 환경을 생성한다..."
  python3 -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"

echo "[INFO] 필수 패키지 설치 상태를 확인한다..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "[INFO] 진단 스크립트를 실행한다..."
export PYTHONUNBUFFERED=1
exec python3 -u diagnose.py "$@"
