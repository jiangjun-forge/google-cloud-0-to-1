---
name: korea-ai-security-checklist
description: "Autopilot, hands-on diagnostics, and self-healing for korea-ai-security-checklist: Gemini 및 Gemini Enterprise 도입 시 사내 정보보호팀과 CISO 보안성 심의에 대응하기 위해 구글 공식 무학습(No-Training), 인적 검토 배제, ISO 42001 및 사내 GCP 인프라 실제 설정을 종합 대조하여 20대 핵심 보안 체크리스트 완제품 소명서를 자동 생성하는 도구다."
---

<!-- disableFinding(LINE_OVER_80) -->
<!-- disableFinding(WHITESPACE_TRAILING) -->

# Korea AI Security Checklist Skill

본 스킬은 고객사 엔지니어와 실무자가 사내 정보보호팀 및 CISO의 생성형 AI 도입 보안성 심의를 통과할 수 있도록, 20대 핵심 보안 체크리스트를 자동 진단하고 완제품 소명서(`report.md`)를 신속하게 확보할 수 있도록 돕는 실습/진단 가이드다.

```
                   [고객 실습 워크플로우 (3단계)]
 ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
 │ 1. 예습 (Mock)  │ ──> │ 2. 실습 (Live)  │ ──> │ 3. 복습 (Action)│
 │  --dry-run 실행  │     │   실환경 진단   │     │  report.md 검토 │
 └─────────────────┘     └─────────────────┘     └─────────────────┘
```

> [!IMPORTANT]
> **실습 환경 보존 및 자동 정리(Teardown) 금지 안내**:
> 본 도구는 순수 읽기 전용 진단 도구이며, 생성된 소명서는 사용자가 직접 보안팀에 제출할 수 있도록 임의로 삭제하지 않는다.

---

## 1. 사전 점검 (Preflight Checks)

1. **작업 디렉터리 확인**:
   ```bash
   pwd
   # /.../google-cloud-0-to-1/samples/korea-ai-security-checklist 경로 확인
   ```

2. **필수 API 활성화 상태 점검**:
   - `cloudresourcemanager.googleapis.com`
   - `logging.googleapis.com`

3. **필요 최소 IAM 권한**:
   - `roles/resourcemanager.organizationViewer`
   - `roles/logging.viewer`

---

## 2. 3단계 실습 실행 절차

### 1단계: 예습 (Dry-run 가상 모의 실행)
실제 GCP 호출 없이 20대 전 항목 완제품 소명서 생성을 1초 만에 검증한다:
```bash
python diagnose.py --dry-run
```

### 2단계: 실습 (사내 실환경 보안 심의 진단)
사내 활성 프로젝트의 기술적 보안 설정을 실시간 감사하고 맞춤형 소명서를 생성한다:
```bash
python diagnose.py -p <대상_프로젝트_ID> -r asia-northeast3
```

### 3단계: 복습 (산출물 검토 및 보안팀 제출)
- `report.md`를 열어 20대 항목의 실측 증적과 공식 약관 소명 확인
- 사내 정보보호팀 또는 금융당국 심의 서류로 첨부 제출
