# Google Cloud 0 to 1

```text
.
├─ scripts/
│ ├─ gemini-api-usage-by-account.sh        # 제미나이 API 호출 로그 적재 및 사용자 쿼리
│ └─ gemini-enterprise-usage-by-account.sh # 제미나이 엔터프라이즈 앱 로그 적재 및 사용자 쿼리
└─ README.md
```

---

## 📋 GCP Gemini 사용량 모니터링 적용 가이드

이 프로젝트는 **Google Cloud에서 Gemini 사용량을 사용자별로 모니터링**하는 파이프라인을 구성합니다.

| 스크립트 | 용도 |
|---|---|
| `gemini-api-usage-by-account.sh` | **Gemini API (Vertex AI)** 호출 로그 수집 및 사용자별 사용량 조회 |
| `gemini-enterprise-usage-by-account.sh` | **Gemini Enterprise 앱** (Cloud Console 내 Gemini 기능) 로그 수집 및 사용자별 사용량 조회 |

두 스크립트 모두 동일한 4단계 파이프라인을 따릅니다:

```
1️⃣ 감사 로그 활성화 → 2️⃣ Cloud Logging 필터 확인 → 3️⃣ Log Sink → BigQuery → 4️⃣ BigQuery SQL 조회
```

---

## 🔧 사전 준비

### 필수 조건
- Google Cloud 프로젝트 생성 완료
- `gcloud` CLI 설치 및 인증 완료
- 아래 IAM 역할을 가진 계정으로 로그인:
  - `roles/logging.admin` (로그 싱크 생성)
  - `roles/bigquery.admin` (데이터셋 관리)
  - `roles/iam.securityAdmin` (IAM 바인딩 추가)

### gcloud 인증 및 프로젝트 설정

```bash
# 1. gcloud 로그인
gcloud auth login

# 2. 프로젝트 설정 (your-project-id를 실제 프로젝트 ID로 변경)
gcloud config set project your-project-id

# 3. 현재 설정 확인
gcloud config list
```

---

## 🚀 적용 단계 (Step-by-Step)

> ⚠️ **중요**: 아래 모든 명령에서 `your-project-id`를 **실제 Google Cloud 프로젝트 ID**로 반드시 변경하세요.

### Step 1️⃣ — 데이터 액세스 감사 로그(Data Access Audit Logs) 활성화

Gemini API 및 Enterprise 앱 로그를 수집하려면 **Vertex AI 서비스의 Data Access Audit Logs**를 활성화해야 합니다.

#### 방법 A: Google Cloud Console (권장)

1. [IAM 감사 로그 콘솔](https://console.cloud.google.com/iam-admin/audit)로 이동
2. 서비스 목록에서 **`Vertex AI API`** 검색 후 선택
3. 다음 로그 유형을 모두 체크:
   - ✅ Admin Read
   - ✅ Data Read  
   - ✅ Data Write
4. **저장** 클릭

#### 방법 B: gcloud CLI

```bash
PROJECT_ID="your-project-id"

# 현재 감사 정책 확인
gcloud projects get-iam-policy ${PROJECT_ID} --format=json > /tmp/policy.json

# policy.json 파일에 아래 auditConfigs 블록을 추가 후 적용
# {
#   "auditConfigs": [
#     {
#       "service": "aiplatform.googleapis.com",
#       "auditLogConfigs": [
#         { "logType": "ADMIN_READ" },
#         { "logType": "DATA_READ" },
#         { "logType": "DATA_WRITE" }
#       ]
#     }
#   ]
# }

gcloud projects set-iam-policy ${PROJECT_ID} /tmp/policy.json
```

> ⚠️ **주의**: `set-iam-policy`는 기존 정책을 **덮어쓰기**합니다. 반드시 기존 정책을 먼저 다운로드한 후 `auditConfigs`만 추가/수정하세요.

---

### Step 2️⃣ — Cloud Logging에서 로그 수집 확인

감사 로그 활성화 후, 실제 Gemini 사용이 발생하면 로그가 수집됩니다. 아래 필터로 로그를 확인합니다.

#### Gemini API (Vertex AI) 로그 확인

[Cloud Logging 콘솔](https://console.cloud.google.com/logs/query)에서:
```
resource.type="audited_resource" AND protoPayload.serviceName="aiplatform.googleapis.com"
```

#### Gemini Enterprise 앱 로그 확인

```
resource.type="gemini_enterprise_resource"
```

> 💡 **팁**: 로그가 보이지 않는다면 실제 Gemini 사용(API 호출 또는 Console에서 Gemini 기능 사용)을 한 뒤 **1~2분 후** 다시 확인하세요.

---

### Step 3️⃣ — BigQuery로 로그 싱크(Log Sink) 생성

이 단계에서는 Cloud Logging의 로그를 BigQuery 데이터셋으로 자동 전송하는 **Log Router Sink**를 생성합니다.

> ℹ️ **참고**: 두 스크립트가 동일한 `LOG_SINK_NAME`과 `BIGQUERY_DATASET_ID`를 사용합니다. 두 종류의 로그를 **모두** 수집하려면 싱크 이름을 다르게 설정하거나, 하나의 싱크에서 두 필터를 OR 조건으로 합치세요.

#### 옵션 A: 개별 싱크 생성 (스크립트별 분리)

```bash
PROJECT_ID="your-project-id"
BIGQUERY_DATASET_ID="gcp_logs"
BIGQUERY_LOCATION="asia-northeast3"

# BigQuery 데이터셋 먼저 생성
bq --location=${BIGQUERY_LOCATION} mk \
  --dataset ${PROJECT_ID}:${BIGQUERY_DATASET_ID}

# Gemini API 로그 싱크
gcloud logging sinks create "gemini-api-logs-sink" \
  "bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/${BIGQUERY_DATASET_ID}" \
  --log-filter='resource.type="audited_resource" AND protoPayload.serviceName="aiplatform.googleapis.com"' \
  --project="${PROJECT_ID}"

# Gemini Enterprise 앱 로그 싱크
gcloud logging sinks create "gemini-enterprise-logs-sink" \
  "bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/${BIGQUERY_DATASET_ID}" \
  --log-filter='resource.type="gemini_enterprise_resource"' \
  --project="${PROJECT_ID}"
```

#### 옵션 B: 통합 싱크 (하나로 합치기)

```bash
gcloud logging sinks create "gcp-logs-sink" \
  "bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/${BIGQUERY_DATASET_ID}" \
  --log-filter='(resource.type="audited_resource" AND protoPayload.serviceName="aiplatform.googleapis.com") OR resource.type="gemini_enterprise_resource"' \
  --project="${PROJECT_ID}"
```

---

### Step 3-b — 싱크 서비스 계정에 BigQuery 권한 부여

Log Sink가 생성되면 자동으로 **Writer Service Account**가 발급됩니다. 이 계정에 BigQuery 데이터셋 쓰기 권한을 부여해야 합니다.

```bash
# 각 싱크의 서비스 계정 확인
# (옵션 A를 사용한 경우 두 싱크 모두에 대해 수행)
SINK_SA_API=$(gcloud logging sinks describe "gemini-api-logs-sink" \
  --project="${PROJECT_ID}" \
  --format="value(writerIdentity)")

SINK_SA_ENTERPRISE=$(gcloud logging sinks describe "gemini-enterprise-logs-sink" \
  --project="${PROJECT_ID}" \
  --format="value(writerIdentity)")

# IAM 바인딩 추가
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="${SINK_SA_API}" \
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="${SINK_SA_ENTERPRISE}" \
  --role="roles/bigquery.dataEditor"
```

> 💡 **팁**: 통합 싱크(옵션 B)를 선택한 경우 싱크 이름을 `gcp-logs-sink`로 변경하여 한 번만 실행하면 됩니다.

---

### Step 4️⃣ — BigQuery에서 사용자별 사용량 조회

로그가 BigQuery로 적재되기 시작하면 (보통 **5~10분 소요**) 아래 SQL로 사용자별 사용량을 조회할 수 있습니다.

#### Gemini API 사용량 조회

```sql
-- BigQuery 콘솔: https://console.cloud.google.com/bigquery
SELECT 
  protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
  COUNT(1) AS request_count
FROM `your-project-id.gcp_logs.cloudaudit_googleapis_com_data_access_*`
WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND resource.type = 'audited_resource'
  AND protopayload_auditlog.serviceName = 'aiplatform.googleapis.com'
GROUP BY user_email
ORDER BY request_count DESC;
```

#### Gemini Enterprise 앱 사용량 조회

```sql
SELECT 
  protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
  COUNT(1) AS request_count
FROM `your-project-id.gcp_logs.cloudaudit_googleapis_com_data_access_*`
WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND resource.type = 'gemini_enterprise_resource'
GROUP BY user_email
ORDER BY request_count DESC;
```

#### CLI로 조회

```bash
bq query --use_legacy_sql=false "
SELECT protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
       COUNT(1) AS request_count
  FROM \`${PROJECT_ID}.${BIGQUERY_DATASET_ID}.cloudaudit_googleapis_com_data_access_*\`
 WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
   AND resource.type = 'audited_resource'
   AND protopayload_auditlog.serviceName = 'aiplatform.googleapis.com'
 GROUP BY user_email
 ORDER BY request_count DESC;
"
```

---

## ⚠️ 주의사항

| 항목 | 설명 |
|---|---|
| **비용** | BigQuery 적재 자체는 무료이나, 쿼리 시 스캔한 데이터량에 따라 비용 발생. `_PARTITIONDATE` 필터 필수 사용 |
| **로그 지연** | 감사 로그 활성화 후 실제 로그 수집까지 최대 **수 분** 소요 |
| **싱크 이름 충돌** | 두 스크립트가 동일한 싱크 이름(`gcp-logs-sink`)을 사용하므로, 순차 실행 시 두 번째 실행에서 오류 발생. 이름을 분리하거나 통합 싱크 사용 권장 |
| **리전** | 데이터셋 리전이 `asia-northeast3` (서울)로 설정됨. 필요 시 변경 |
| **권한** | `set-iam-policy`는 전체 정책을 덮어쓰므로 주의. `add-iam-policy-binding`은 안전하게 추가만 수행 |

---

## ✅ 적용 체크리스트

- [ ] `PROJECT_ID` 변수를 실제 프로젝트 ID로 변경
- [ ] gcloud 인증 및 프로젝트 설정 완료
- [ ] Vertex AI 데이터 액세스 감사 로그 활성화
- [ ] Cloud Logging에서 로그 수집 확인
- [ ] BigQuery 데이터셋(`gcp_logs`) 생성
- [ ] Log Router Sink 생성 완료
- [ ] Sink 서비스 계정에 BigQuery 권한 부여
- [ ] BigQuery에서 사용량 쿼리 정상 동작 확인
