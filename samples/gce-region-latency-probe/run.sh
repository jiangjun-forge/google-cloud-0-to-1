#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# 로컬 .env가 존재하면 로드
if [ -f "${SCRIPT_DIR}/.env" ]; then
  set -a
  source "${SCRIPT_DIR}/.env" 2>/dev/null || true
  set +a
fi

# 파이썬 진단 스크립트 실행
python3 diagnose.py "$@"
