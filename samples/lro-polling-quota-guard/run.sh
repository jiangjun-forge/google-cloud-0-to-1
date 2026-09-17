#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# lro-polling-quota-guard 실행 래퍼 스크립트

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

# .env 파일이 존재할 경우 로드
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck source=/dev/null
  set -a
  source "${ENV_FILE}"
  set +a
fi

# 가상 환경 점검 및 실행
PYTHON_CMD="python3"
if [[ -n "${VIRTUAL_ENV:-}" ]] && [[ -x "${VIRTUAL_ENV}/bin/python3" ]]; then
  PYTHON_CMD="${VIRTUAL_ENV}/bin/python3"
fi

export PYTHONUNBUFFERED=1
exec "${PYTHON_CMD}" -u "${SCRIPT_DIR}/diagnose.py" "$@"
