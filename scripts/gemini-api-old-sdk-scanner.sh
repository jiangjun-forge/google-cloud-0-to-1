#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# gemini-api-old-sdk-scanner.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드다.
# 용도: 구형 제미나이(Gemini ) 모델 SDK 호출 부위를 탐색해 주는 스캐닝 도구다.

# 전역 변수 선언 영역이다.
FOUND_COUNT=0 # 검출된 구형 코드 라인 개수다.
SCAN_PATH="." # 스캔할 대상 디렉터리 경로다.



# 탐색 대상 경로 유효성 검사를 수행한다.
if [ ! -d "${SCAN_PATH}" ]; then
  echo "[오류] 지정한 경로가 디렉터리가 아니거나 존재하지 않는다: ${SCAN_PATH}"
  exit 1
fi

echo "[검사 시작] 구형 제미나이 SDK 코드 스캔을 시작한다..."
echo "대상 디렉터리: ${SCAN_PATH}"
echo "------------------------------------------------------------------------"

# 파이썬(*.py), 쉘 스크립트(*.sh) 및 주피터 노트북(*.ipynb) 소스 코드를 대상으로 한다.
TARGET_FILES=$(find "${SCAN_PATH}" -type f \( -name "*.py" -o -name "*.sh" -o -name "*.ipynb" \) -not -path '*/.*')

# 검출에 사용할 구형 제미나이 SDK 정규식 패턴 모음이다.
LEGACY_PATTERNS="from vertexai\..*generative_models|genai\.configure|import google\.generativeai|model = genai\.GenerativeModel|model\.generate_content|vertexai\.init"

for FILE_PATH in ${TARGET_FILES}; do
  # 스캐너 자체 스크립트 파일은 진단 대상에서 안전하게 제외한다.
  if [[ "${FILE_PATH}" == *"$0"* || "${FILE_PATH}" == *"gemini-api-old-sdk-scanner"* ]]; then
    continue
  fi

  # 파일 내부에서 구형 패턴을 검색하여 라인 번호와 내용을 매칭한다.
  MATCHES=$(grep -n -E "${LEGACY_PATTERNS}" "${FILE_PATH}" 2>/dev/null)

  if [ -n "${MATCHES}" ]; then
    echo "[발견] 파일: ${FILE_PATH}"
    # 각 검출 행에 대해 이쁘게 출력한다.
    while IFS= read -r line; do
      LINE_NUM=$(echo "${line}" | cut -d: -f1)
      LINE_CONTENT=$(echo "${line}" | cut -d: -f2-)
      # 공백 제거 후 깔끔하게 소스 라인을 출력한다.
      if [[ "${FILE_PATH}" == *.ipynb ]]; then
        # .ipynb 파일의 경우 JSON 문자열 구조 기호를 다듬어 가독성을 높인다.
        LINE_CONTENT=${LINE_CONTENT#*\"} # 앞쪽 큰따옴표 및 공백 제거
        LINE_CONTENT=${LINE_CONTENT%\"*} # 뒤쪽 큰따옴표 제거
        LINE_CONTENT=${LINE_CONTENT/\\n/} # 개행 기호 제거
        LINE_CONTENT=${LINE_CONTENT//\\\\/\\} # 이중 백슬래시 복원
      fi
      echo "  - 행 번호 ${LINE_NUM}: ${LINE_CONTENT}"
      FOUND_COUNT=$((FOUND_COUNT + 1))
    done <<< "${MATCHES}"
    echo "------------------------------------------------------------------------"
  fi
done

if [ ${FOUND_COUNT} -eq 0 ]; then
  echo "[성공] 구형 제미나이 SDK 사용처가 발견되지 않았다. 안전하다!"
else
  echo "[완료] 총 ${FOUND_COUNT}개의 구형 호출 의심 행이 발견되었다."
  echo "     (주의: 구형 SDK는 2026년 6월 24일에 종료되므로 신형 google-genai SDK로 수동 변환을 권장한다.)"
fi
