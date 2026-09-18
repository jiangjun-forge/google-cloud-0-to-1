# 진단 및 분석 리포트: gemini-enterprise-analytics-exporter

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
Gemini Enterprise 채택률 및 유휴 라이선스 진단 시작 (프로젝트: sample-project-id)
--> 가상 실행 모드 (--dry-run) 활성화: 사전 정의된 부서별 사용자 채택 지표를 분석한다.

=========================================================================================================
사용자 이메일                        소속 부서                  활성일(30d)     프롬프트       등급         회수 대상
---------------------------------------------------------------------------------------------------------
kim.minsoo@company.com         R&D Software           24           412        High       정상 유지
lee.jiwon@company.com          R&D Software           19           285        High       정상 유지
park.chul@company.com          R&D Software           0            0          Dormant    [회수 권고]
choi.eunji@company.com         Marketing              12           140        Moderate   정상 유지
jung.homin@company.com         Marketing              0            0          Dormant    [회수 권고]
kang.sohee@company.com         HR & Culture           8            65         Moderate   정상 유지
yoon.daehan@company.com        HR & Culture           0            0          Dormant    [회수 권고]
han.kyung@company.com          Finance & Accounting   15           190        High       정상 유지
song.taewoo@company.com        Finance & Accounting   0            0          Dormant    [회수 권고]
jang.seungmin@company.com      Operations             0            0          Dormant    [회수 권고]
=========================================================================================================

[부서별 라이선스 채택률 및 유휴 현황]
---------------------------------------------------------------------------
부서명                        부여 좌석        활성 좌석        유휴 좌석        채택률
---------------------------------------------------------------------------
Finance & Accounting       2            1            1            50.0%
HR & Culture               2            1            1            50.0%
Marketing                  2            1            1            50.0%
Operations                 1            0            1            0.0%
R&D Software               3            2            1            66.7%
---------------------------------------------------------------------------

[전사 라이선스 FinOps 요약 (유휴 기준: 30일 이상 미사용)]
* 전체 배포 좌석: 10개
* 실제 활성 좌석: 5개 (실질 채택률: 50.0%)
* 미사용 유휴 좌석: 5개 (회수 권고 대상)
* 추정 월간 비용 누수: $150 / 월 (연간 환산 약 $1,800)

[유휴 라이선스 회수 권고 조치]
* park.chul@company.com (R&D Software): 최근 45일간 프롬프트 0건 (회수 대상)
* jung.homin@company.com (Marketing): 최근 62일간 프롬프트 0건 (회수 대상)
* yoon.daehan@company.com (HR & Culture): 최근 38일간 프롬프트 0건 (회수 대상)
* song.taewoo@company.com (Finance & Accounting): 최근 50일간 프롬프트 0건 (회수 대상)
* jang.seungmin@company.com (Operations): 최근 80일간 프롬프트 0건 (회수 대상)

[BigQuery 적재 DDL 스키마 (`gemini_analytics.user_adoption_metrics`)]
-- Gemini Enterprise User Adoption Metrics Table DDL
CREATE TABLE IF NOT EXISTS `gemini_analytics.user_adoption_metrics` (
  user_email STRING NOT NULL,
  department STRING,
  license_type STRING NOT NULL,
  days_active_last_30d INT64,
  total_prompts INT64,
  total_tokens INT64,
  last_active_date DATE,
  inactive_days INT64,
  activity_tier STRING,
  reclaim_candidate BOOL,
  snapshot_timestamp TIMESTAMP NOT NULL
)
PARTITION BY DATE(snapshot_timestamp)
CLUSTER BY department, activity_tier;
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
