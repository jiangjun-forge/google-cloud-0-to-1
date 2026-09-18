# 진단 및 분석 리포트: gemini-enterprise-usage-by-account

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
[데모 실행] --dry-run 모드가 활성화되어 가상 Model Armor 분석을 시뮬레이션한다.
========================================================================
[진단 결과] 제미나이 엔터프라이즈 Model Armor 감사 및 토큰 통계
  - 대상 프로젝트: sample-project-id
  - BigQuery 데이터세트: gcp_logs
  - 조회 기간: 최근 7일
========================================================================

[Model Armor 보안 검사 기반 사용자별 활동 및 추정 토큰량 순위]
┌───────────────────────────────────────────┬────────────┬──────────────────┬─────────────────┬──────────────────┐
│ 사용자/클라이언트 식별자 (Principal)     │ 검사 횟수  │ 추정 입력 토큰   │ 추정 출력 토큰  │ 총 추정 토큰     │
├───────────────────────────────────────────┼────────────┼──────────────────┼─────────────────┼──────────────────┤
│ enterprise-agent-bot@company.com          │ 5,420회    │ 16,260,000       │ 2,710,000       │ 18,970,000       │
│ finance-advisor@company.com               │ 1,120회    │  3,360,000       │   560,000       │  3,920,000       │
│ hr-assistant@company.com                  │   780회    │  1,560,000       │   390,000       │  1,950,000       │
│ external-partner-eval@partner.com         │   110회    │    220,000       │    55,000       │    275,000       │
└───────────────────────────────────────────┴────────────┴──────────────────┴─────────────────┴──────────────────┘

------------------------------------------------------------------------
[BigQuery 표준 집계 SQL]
SELECT 
    COALESCE(
        JSON_VALUE(jsonPayload.metadata.client_correlation_id),
        JSON_VALUE(labels["modelarmor.googleapis.com/client_name"]),
        'unknown_principal'
    ) AS principal_identity,
    COUNT(1) AS inspection_count,
    SUM(CAST(ROUND(CHARACTER_LENGTH(JSON_VALUE(jsonPayload.userPrompt.content)) * 1.2) AS INT64)) AS estimated_prompt_tokens,
    SUM(CAST(ROUND(CHARACTER_LENGTH(JSON_VALUE(jsonPayload.modelResponse.content)) * 1.5) AS INT64)) AS estimated_response_tokens,
    SUM(CAST(ROUND((CHARACTER_LENGTH(JSON_VALUE(jsonPayload.userPrompt.content)) * 1.2) + (CHARACTER_LENGTH(JSON_VALUE(jsonPayload.modelResponse.content)) * 1.5)) AS INT64)) AS estimated_total_tokens
FROM `sample-project-id.gcp_logs.modelarmor_googleapis_com_sanitize_operations_*`
WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))
GROUP BY principal_identity
ORDER BY estimated_total_tokens DESC;
========================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
