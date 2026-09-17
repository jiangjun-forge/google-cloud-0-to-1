#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# gemini-api-resilience-checker.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드다.
# 용도: 제미나이(Gemini ) API 호출 코드 내 429 에러 방어를 위한 지수 백오프, 지터, 폴백 모델 적용 여부를 진단한다.

# 전역 변수 선언 영역이다.
FOUND_COUNT=0 # 복원력 패턴 미흡 항목 개수다.
SCAN_PATH="." # 스캔할 대상 디렉터리 경로다.



# 탐색 대상 경로 유효성 검사를 수행한다.
if [ ! -d "${SCAN_PATH}" ]; then
  echo "[오류] 지정한 경로가 디렉터리가 아니거나 존재하지 않는다: ${SCAN_PATH}"
  exit 1
fi

echo "[검사 시작] 제미나이 API 호출 부위의 429 방어 복원력(Resilience ) 패턴 자가 진단을 시작한다..."
echo "대상 디렉터리: ${SCAN_PATH}"
echo "------------------------------------------------------------------------"

# 탐색 대상 파일의 확장자 필터를 정의한다.
TARGET_FILES=$(find "${SCAN_PATH}" -type f \( -name "*.py" -o -name "*.sh" \) -not -path '*/.*')

for FILE_PATH in ${TARGET_FILES}; do
  # 스크립트 자체는 진단 대상에서 안전하게 제외한다.
  if [[ "${FILE_PATH}" == *"$0"* || "${FILE_PATH}" == *"gemini-api-resilience-checker.sh"* ]]; then
    continue
  fi

  # 1. 제미나이 API 호출 구문 감지
  HAS_GEMINI_CALL=$(grep -q -E "generate_content|generate_content_stream|generate_content_async" "${FILE_PATH}" && echo "yes" || echo "no")

  if [ "${HAS_GEMINI_CALL}" = "yes" ]; then
    echo "[진단 대상 발견] 파일: ${FILE_PATH}"

    # 2. 지수 백오프 및 재시도(Exponential Backoff & Retry ) 패턴 검증
    HAS_RETRY=$(grep -q -i -E "retry|tenacity|backoff|sleep" "${FILE_PATH}" && echo "yes" || echo "no")

    # 3. 지터(Jitter ) 무작위 대기 기법 검증
    HAS_JITTER=$(grep -q -i -E "jitter|random|wait_random" "${FILE_PATH}" && echo "yes" || echo "no")

    # 4. 최대 재시도 횟수 제한 설정 검사
    HAS_MAX_RETRIES=$(grep -q -i -E "stop_after|max_retries|stop=" "${FILE_PATH}" && echo "yes" || echo "no")

    # 5. 폴백 모델(Fallback Model ) 예외 복구 우회 검사
    HAS_FALLBACK=$(grep -q -i -E "fallback|try:|except" "${FILE_PATH}" && echo "yes" || echo "no")

    if [ "${HAS_RETRY}" = "no" ]; then
      echo "  [▲ 경고] 지수 백오프 및 재시도 누락 의심!"
      echo "           - 백오프나 재시도 제어 로직이 검출되지 않았다."
      FOUND_COUNT=$((FOUND_COUNT + 1))
    else
      echo "  [통과] 지수 백오프 및 재시도 제어 패턴 정상 감지"
    fi

    if [ "${HAS_JITTER}" = "no" ]; then
      echo "  [경고] 지터 무작위 대기 기법 누락 의심!"
      echo "           - 요청 폭주를 예방하는 지터 대기 로직이 검출되지 않았다."
      FOUND_COUNT=$((FOUND_COUNT + 1))
    else
      echo "  [통과] 지터 무작위 대기 기법 정상 감지"
    fi

    if [ "${HAS_MAX_RETRIES}" = "no" ]; then
      echo "  [경고] 최대 재시도 횟수 제한 설정 누락 의심!"
      echo "           - 무한 재시도로 인한 비용 폭증을 방지하는 재시도 제한 장치가 검출되지 않았다."
      FOUND_COUNT=$((FOUND_COUNT + 1))
    else
      echo "  [통과] 최대 재시도 횟수 제한 설정 정상 감지"
    fi

    if [ "${HAS_FALLBACK}" = "no" ]; then
      echo "  [권장] 폴백 모델 예외 복구 패턴 적용 검토"
      echo "           - 가용성 유지를 위한 폴백 체인이 검출되지 않았다."
      FOUND_COUNT=$((FOUND_COUNT + 1))
    else
      echo "  [통과] 폴백 모델 예외 복구 패턴 정상 감지"
    fi
    echo "------------------------------------------------------------------------"
  fi
done

if [ ${FOUND_COUNT} -eq 0 ]; then
  echo "[성공] 프로젝트의 모든 제미나이 API 호출부가 429 장애 극복 회복탄력성 패턴을 안전하게 구비하고 있다!"
else
  echo "[완료] 총 ${FOUND_COUNT}개의 복원력 패턴 미흡 및 개선 권장 사항이 발견되었다."
  echo "     (참고: 할당량 한도 및 가용 잔여량은 GCP 할당량 제어 콘솔 주소(https://console.cloud.google.com/iam-admin/quotas )를 통해 실시간으로 확인 가능하다.)"
  echo ""
  echo "========================================================================"
  echo "[추천 표준 처방 가이드 - 파이썬(Python) tenacity 데코레이터 표준 템플릿]"
  echo "========================================================================"
  echo "import google.genai"
  echo "from google.genai import types"
  echo "from tenacity import retry, stop_after_attempt, wait_random_exponential"
  echo ""
  echo "# tenacity 패키지를 사용한 지수 백오프, 지터, 최대 재시도 안전 결합 표준 예시다."
  echo "@retry("
  echo "  wait=wait_random_exponential(min=1, max=60), # 지수 백오프 및 무작위성(지터) 추가"
  echo "  stop=stop_after_attempt(5)                    # 최대 5회까지만 재시도 제한"
  echo ")"
  echo "def generate_with_retry(client, model_id, prompt):"
  echo "  return client.models.generate_content("
  echo "    model=model_id,"
  echo "    contents=prompt"
  echo "  )"
  echo ""
  echo "# 주 모델(Gemini 3.5 Pro) 실패 시 차선 가용 모델(Gemini 3.5 Flash)로 우회 처리하는 폴백 예시다."
  echo "def generate_with_fallback(client, prompt):"
  echo "  try:"
  echo "    return generate_with_retry(client, 'gemini-3.5-pro', prompt)"
  echo "  except Exception as e:"
  echo "    print(f'[안내] 주 모델 호출 실패로 폴백 모델 호출로 즉시 우회한다: {e}')"
  echo "    return generate_with_retry(client, 'gemini-3.5-flash', prompt)"
  echo "========================================================================"
fi
