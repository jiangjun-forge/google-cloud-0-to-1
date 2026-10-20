# Gemini Enterprise 공식 프롬프트/응답 로깅 및 계정별 사용량 분석 보고서

- **생성 일시**: 2026-10-20 02:22:16 UTC
- **실행 모드**: 가상 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **BigQuery 데이터세트**: `gemini_enterprise_logs`

---

## 1. Gemini Enterprise app 공식 로깅 기반 진단 결과

```text
[가상 실행] --dry-run 모드가 활성화되어 Gemini Enterprise app 공식 로깅 집계를 시뮬레이션한다.
========================================================================
  Gemini Enterprise 공식 프롬프트 로깅 기반 계정별 토큰 사용량 진단
  - 대상 프로젝트      : sample-project-id
  - BigQuery 데이터세트: gemini_enterprise_logs
  - 분석 대상 기간    : 최근 7일
========================================================================

[Gemini Enterprise app 공식 로깅 수집 기반 사용자별 프롬프트 호출 및 토큰 사용량 순위]
┌───────────────────────────────────────────┬────────────┬──────────────────┬─────────────────┬──────────────────┬──────────────┐
│ 사용자 계정 (User Identity)               │ 호출 횟수  │ 입력 토큰 합계   │ 출력 토큰 합계  │ 총 토큰 사용량   │ 평균 지연시간│
├───────────────────────────────────────────┼────────────┼──────────────────┼─────────────────┼──────────────────┼──────────────┤
│ enterprise-marketing-lead@company.com     │ 4,820회    │ 14,460,000       │ 2,410,000       │ 16,870,000       │ 820.5ms      │
│ finance-audit-bot@company.com             │ 1,250회    │  3,750,000       │   625,000       │  4,375,000       │ 640.2ms      │
│ hr-operations@company.com                 │   890회    │  1,780,000       │   445,000       │  2,225,000       │ 510.8ms      │
│ tech-support-agent@company.com            │   340회    │    680,000       │   170,000       │    850,000       │ 490.1ms      │
└───────────────────────────────────────────┴────────────┴──────────────────┴─────────────────┴──────────────────┴──────────────┘

------------------------------------------------------------------------
[BigQuery 공식 집계 SQL]
SELECT 
    COALESCE(user_email, principal_id, 'unknown_user') AS user_identity,
    COUNT(1) AS request_count,
    SUM(prompt_token_count) AS total_prompt_tokens,
    SUM(response_token_count) AS total_response_tokens,
    SUM(total_token_count) AS grand_total_tokens,
    ROUND(AVG(latency_ms), 1) AS avg_latency_ms
FROM `sample-project-id.gemini_enterprise_logs.gemini_enterprise_prompt_logs_*`
WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))
GROUP BY user_identity
ORDER BY grand_total_tokens DESC;
========================================================================
```

---

## 2. Gemini Enterprise app 공식 내장 프롬프트/응답 로깅 활성화 가이드

구글 클라우드 공식 관리형 기능을 통해 프롬프트와 LLM 출력을 BigQuery로 영구 보관하려면 아래 절차를 수행한다:

1. **Gemini Enterprise 관리 콘솔 접속**: `https://gemini.google.com` (또는 Cloud Console > Gemini Enterprise)
2. **감사 설정 이동**: [Settings] > [Audit & Compliance] 메뉴 선택
3. **프롬프트 및 응답 로깅 활성화**: 'Enable Prompt & Response Logging' 토글 ON
4. **BigQuery 데이터세트 지정**: 로그를 수집할 대상 프로젝트 및 BigQuery 데이터세트(`gemini_enterprise_logs`) 입력 및 저장

---

## 3. 실습 명령어 안내

```bash
# 가상 실행 검증
python diagnose.py --dry-run

# 실제 사내 BigQuery 로그 집계 실행
python diagnose.py --project="sample-project-id" --dataset="gemini_enterprise_logs" --days=7
```

---

## 4. 사내 거버넌스 4대 필수 표준 라벨링

BigQuery 로그 데이터세트 및 관련 클라우드 인프라 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-usage-by-account`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 5. 콘솔 링크 조치 가이드

- **Gemini Enterprise 관리 콘솔**: ( https://gemini.google.com )
- **BigQuery 콘솔**: ( https://console.cloud.google.com/bigquery )
- **IAM 및 관리자 콘솔**: ( https://console.cloud.google.com/iam-admin/iam )

---

## 6. 자원 정리 안내 (Teardown)

본 솔루션은 구글 공식 관리형 로깅 기능을 활용하므로 별도의 상주 가상머신(VM)이나 서버리스 인스턴스가 존재하지 않는다.
더 이상 로깅이 필요하지 않을 경우 아래 절차를 수행한다:

1. **Gemini Enterprise app 로깅 비활성화**: Gemini Enterprise app 관리 콘솔 > [Settings] > [Audit & Compliance]에서 'Prompt & Response Logging' 토글 OFF
2. **BigQuery 로그 데이터세트 정리 (선택 사항)**: `bq rm -r -f -d ${PROJECT_ID}:gemini_enterprise_logs`