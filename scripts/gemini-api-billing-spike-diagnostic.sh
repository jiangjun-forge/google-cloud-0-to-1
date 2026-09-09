#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# gemini-api-billing-spike-diagnostic.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드 스크립트다.
# 용도: 구글 클라우드(Google Cloud )에서 데이터 액세스 감사 로그가 꺼져 있어도, 클라우드 모니터링(Cloud Monitoring ) 지표를 기반으로 자격 증명(Credential )별 제미나이(Gemini ) 호출 추이를 실시간 분석하여 비용 급증 원인을 규명한다.

# 전역 변수 선언 영역이다.
DAYS=90 # 분석 대상 조회 기간(일 수)이다.
METRIC_FILTER="metric.type=\"serviceruntime.googleapis.com/api/request_count\" AND (resource.labels.service=\"aiplatform.googleapis.com\" OR resource.labels.service=\"generativelanguage.googleapis.com\")" # 수집 타겟 메트릭 필터다.
PROJECT_ID=$(gcloud config get-value project 2>/dev/null) # 분석 대상 활성 GCP 프로젝트 ID다.
RAW_METRIC_PATH="tmp/gemini_raw_metrics.json" # 수집한 메트릭이 저장될 임시 JSON 파일 경로다.



# DAYS 옵션값 유효성 검증을 처리한다.
if ! [[ "${DAYS}" =~ ^[0-9]+$ ]] || [ "${DAYS}" -le 0 ]; then
  DAYS=90
fi

# GCP 프로젝트 ID 감지 여부를 점검한다.
if [ -z "${PROJECT_ID}" ]; then
  echo "[오류] 활성화된 GCP 프로젝트 ID를 감지하지 못했다. gcloud config set project 명령어로 설정하거나 PROJECT_ID 변수를 직접 지정하기 바란다."
  echo "     (참고: gcloud 로그인 필요 시 GCP 콘솔(https://console.cloud.google.com/ )에서 직접 확인 가능하다.)"
  exit 1
fi

# 임시 로그 디렉토리가 없으면 자동으로 미리 생성한다.
mkdir -p "$(dirname "${RAW_METRIC_PATH}")"

echo "========================================================================"
echo "[1단계: 클라우드 모니터링 API 메트릭 수집]"
# (메트릭 탐색 콘솔 주소: https://console.cloud.google.com/monitoring/metrics-explorer )
echo "프로젝트 '${PROJECT_ID}'에서 최근 ${DAYS}일간 발생한 시스템 메트릭 데이터를 수집하는 중이다..."

# 수집 시작 시간과 종료 시간을 RFC 3339 규격으로 생성한다.
START_TIME=$(date -u -d "${DAYS} days ago" +%Y-%m-%dT%H:%M:%SZ)
END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ACCESS_TOKEN=$(gcloud auth print-access-token 2>/dev/null)

# 감사 로그가 꺼져 있어도 수집 가능한 플랫폼 REST API를 사용하여 지표 데이터 수집 진행
curl -s -G -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://monitoring.googleapis.com/v3/projects/${PROJECT_ID}/timeSeries" \
  --data-urlencode "filter=${METRIC_FILTER}" \
  --data-urlencode "interval.startTime=${START_TIME}" \
  --data-urlencode "interval.endTime=${END_TIME}" > "${RAW_METRIC_PATH}"

if [ ! -s "${RAW_METRIC_PATH}" ] || [ "$(grep -o "timeSeries" "${RAW_METRIC_PATH}" | wc -l)" -eq 0 ]; then
  echo "[경고] 최근 ${DAYS}일 동안 대상 API 호출 메트릭을 감지하지 못했다."
  echo "     (참고: 해당 기간에 메트릭 탐색기 지표 데이터가 아직 쌓이지 않았거나 호출 자체가 없었을 수 있다.)"
  echo "========================================================================"
  exit 0
fi

echo "[성공] 플랫폼 지표 데이터가 정상적으로 수집되어 로컬 파일에 적재되었다."

echo "========================================================================"
echo "[2단계: 파이썬 기반 메트릭 자격 증명 정밀 진단 실행]"

python3 -c '
import collections
import json
import sys

def parse_metrics(file_path):
  try:
    with open(file_path, "r", encoding="utf-8") as f:
      raw_data = json.load(f)
  except Exception as e:
    print(f"[오류] 메트릭 파일을 읽는 중 예외가 발생했다: {e}")
    sys.exit(1)

  data = raw_data.get("timeSeries", [])
  if not data:
    print("[안내] 분석할 메트릭 데이터가 비어 있다.")
    return

  credential_counts = collections.defaultdict(int)
  method_counts = collections.defaultdict(int)
  service_counts = collections.defaultdict(int)

  for ts in data:
    metric = ts.get("metric", {})
    resource = ts.get("resource", {})
    labels = metric.get("labels", {})
    r_labels = resource.get("labels", {})

    # 자격 증명 ID 및 메서드 정보는 resource.labels와 metric.labels 모두에 위치할 수 있어 유기적으로 매핑 처리
    cred_id = r_labels.get("credential_id") or labels.get("credential_id", "unknown-credential")
    service_name = r_labels.get("service") or labels.get("service", "unknown-service")
    method_name = r_labels.get("method") or labels.get("method", "unknown-method")

    points = ts.get("points", [])
    total_val = 0
    for pt in points:
      val_dict = pt.get("value", {})
      val_str = val_dict.get("int64Value", "0")
      try:
        total_val += int(val_str)
      except ValueError:
        pass

    credential_counts[cred_id] += total_val
    method_counts[method_name] += total_val
    service_counts[service_name] += total_val

  print("========================================================================")
  print("             클라우드 모니터링 기반 제미나이 사용량 진단 결과")
  print("========================================================================")
  print(f"매핑된 총 시계열 레코드: {len(data)}건")
  print()

  print("[1. API Services]")
  for service in sorted(service_counts.keys()):
    print(f"  - {service}: {service_counts[service]}회 호출")
  print()

  print("[2. Credentials and Keys]")
  for cred in sorted(credential_counts.keys()):
    print(f"  - {cred}: {credential_counts[cred]}회 호출")
  print()

  print("[3. Method Call Statistics]")
  for method in sorted(method_counts.keys()):
    print(f"  - {method}: {method_counts[method]}회 호출")
  print()
  print("========================================================================")

if len(sys.argv) > 1:
  parse_metrics(sys.argv[1])
' "${RAW_METRIC_PATH}"

echo "========================================================================"
echo "[3단계: 식별된 자격 증명(Credential ID ) 해석 방법]"
# (사용자 인증 정보 콘솔 링크: https://console.cloud.google.com/apis/credentials )
echo "출력된 자격 증명 ID 결과를 기반으로 어떤 인증 수단에서 비용이 발생했는지 추적하는 가이드다."
echo ""
echo "  - 'apikey:AIzaSy...' 형태인 경우:"
echo "    구글 클라우드 콘솔의 'API 및 서비스 > 사용자 인증 정보'에서 일치하는 API 키(API Key )를 찾아 삭제하거나 제한 조치한다."
echo "    * 콘솔 링크: (https://console.cloud.google.com/apis/credentials?project=${PROJECT_ID} )"
echo "  - 'serviceAccount:...' 형태인 경우:"
echo "    해당하는 서비스 계정이 사용 중인 프라이빗 키(Private Key )가 외부로 유출되었거나 비정상적인 백엔드 시스템에서 오호출 중인지 진단한다."
echo "    * 콘솔 링크: (https://console.cloud.google.com/iam-admin/serviceaccounts?project=${PROJECT_ID} )"
echo "  - 'oauth2:...' 형태인 경우:"
echo "    웹 앱 또는 클라이언트 애플리케이션에 발급된 OAuth 2.0 클라이언트 ID를 추적하여 호출 주체를 규명한다."
echo "    * 콘솔 링크: (https://console.cloud.google.com/apis/credentials?project=${PROJECT_ID} )"
echo "========================================================================"
