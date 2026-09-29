# 진단 및 분석 리포트: korea-nct-gen-ai-compliance-checker

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
=====================================================================================
국가 핵심 기술(NCT) 대상 생성형 AI 보안 통제 및 데이터 주권 진단 도구
진단 모드: 가상 실행 (Dry-run)
대상 프로젝트: sample-project-id
지정 리전: asia-northeast3 (대한민국 서울 리전)
=====================================================================================

[*] 가상 모의 감사 데이터를 로드하고 점검 항목을 시뮬레이션한다...


[항목별 기술적 보안 통제 준수 현황]
-------------------------------------------------------------------------------------
구분                 보안 통제 항목                         상태       현재 상태
-------------------------------------------------------------------------------------
Data Residency     gcp.resourceLocations (조직 정책 - 법 제11조) PASS     서울 리전(asia-northeast3)으로 리소스 생성 제한 적용 완료
Vector Security    RAG 벡터 데이터 저장 차단 (IAM Deny - 법 제10조) FAIL     aiplatform.indexes.* 권한 차단 Deny Policy 미발견
Encryption         Cloud KMS CMEK 이중 암호화 (안내서 필수 요건) FAIL     기본 구글 관리 키 사용 중 (KMS CMEK 미연동 버킷 2개 감지)
Inference Boundary 추론 리전 국소화 (Vertex AI - 안내서 국내 위치) PASS     Vertex AI 서울 리전 엔드포인트(asia-northeast3-aiplatform.googleapis.com) 사용 강제 확인
Audit Logging      Cloud Audit Logs 데이터 접근 로깅 (법 제10조) PASS     DATA_READ, DATA_WRITE 감사 로그 활성화 상태
Access Control     사외/외국 계정 공유 차단 (조직 정책 - 안내서 외국 기업 접근 배제) FAIL     iam.allowedPolicyMemberDomains 조직 정책 미적용 (외부 계정 초대 위험 존재)
Provider Isolation 클라우드 제공자 임의 접근 통제 (Access Approval - 안내서 사전 승인 의무) PASS     Access Approval 및 Access Transparency 정상 활성화 (CSP 엔지니어 사전 승인 강제)
-------------------------------------------------------------------------------------

[진단 종합 점수: 총 7개 항목 중 PASS 4건, FAIL 3건]

[미준수 항목 긴급 조치 가이드]
1. RAG 벡터 데이터 저장 차단 (IAM Deny - 법 제10조)
   - 조치 방향: gcloud iam deny-policies create 명령으로 벡터 인덱스 사외 생성 차단 정책 적용 필요
2. Cloud KMS CMEK 이중 암호화 (안내서 필수 요건)
   - 조치 방향: 서울 리전 Cloud KMS 키링 및 암호화 키 생성 후 GCS/BigQuery CMEK 지정 (이중 암호화 의무 준수)
3. 사외/외국 계정 공유 차단 (조직 정책 - 안내서 외국 기업 접근 배제)
   - 조치 방향: gcloud resource-manager org-policies set-policy 명령으로 사내 승인 도메인만 허용 (기술 해외 유출 방어)

[표준 보안 처방 CLI 명령어]
1. 서울 리전 Data Boundary 조직 정책 강제:
   gcloud resource-manager org-policies enable-enforce constraints/gcp.resourceLocations --project=sample-project-id
2. RAG 벡터 데이터 저장 차단 Deny Policy 배포:
   gcloud iam deny-policies create nct-rag-deny --attachment-point=cloudresourcemanager.googleapis.com/projects/sample-project-id --file=deny-rules.json
3. 서울 리전 Cloud KMS CMEK 키 생성:
   gcloud kms keyrings create nct-keyring --location=asia-northeast3 --project=sample-project-id
   gcloud kms keys create nct-cmek-key --keyring=nct-keyring --location=asia-northeast3 --purpose=encryption --project=sample-project-id
=====================================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
