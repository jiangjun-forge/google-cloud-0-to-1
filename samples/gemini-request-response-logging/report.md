# 진단 및 분석 리포트: gemini-request-response-logging

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
[데모 실행] --dry-run 모드가 활성화되어 가상 BigQuery 로깅 분석을 시뮬레이션한다.
========================================================================
[시뮬레이션] BigQuery 자동 로깅 및 토큰 사용량 집계 리포트
  - 대상 프로젝트: sample-project-id
  - BigQuery 대상 데이터세트: gcp_logs
========================================================================

[가상 쿼리 실행 결과: 사용자/서비스 계정별 토큰 소모량]
┌───────────────────────────────────────────┬────────────┬──────────────────┬─────────────────┬────────────────┐
│ 사용자 계정 (Principal Email)            │ 호출 횟수  │ 입력 토큰 (Prompt)│ 출력 토큰 (Cand)│ 총 토큰 (Total)│
├───────────────────────────────────────────┼────────────┼──────────────────┼─────────────────┼────────────────┤
│ data-analyst@example.com                  │ 1,240회    │ 12,450,000       │ 1,820,000       │ 14,270,000     │
│ sa-prod-worker@project.iam.gserviceaccount│ 3,890회    │  5,210,000       │ 4,110,000       │  9,320,000     │
│ dev-engineer@example.com                  │   450회    │    920,000       │   180,000       │  1,100,000     │
└───────────────────────────────────────────┴────────────┴──────────────────┴─────────────────┴────────────────┘

------------------------------------------------------------------------
[BigQuery 토큰 분석 표준 SQL 쿼리문]
SELECT 
    JSON_VALUE(full_request, '$.labels.user_email') AS user_email,
    COUNT(1) AS call_count,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.promptTokenCount') AS INT64)) AS total_prompt_tokens,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.candidatesTokenCount') AS INT64)) AS total_candidate_tokens,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.totalTokenCount') AS INT64)) AS total_tokens
FROM `sample-project-id.gcp_logs.model_request_response_logs`
WHERE logging_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY user_email
ORDER BY total_tokens DESC;

========================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
