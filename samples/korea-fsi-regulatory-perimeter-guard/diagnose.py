# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""혁신 금융 서비스 규제 준수를 위한 논리적 망 분리 및 데이터 보호 보안 경계 진단 도구.

금융위원회의 금융 분야 망 분리 개선 로드맵 및 혁신 금융 서비스 지정 심사 기준에 따라
Google Cloud 인프라의 논리적 망 분리, 암호화 키 관리, 데이터 불변 보존, 감사 로깅,
AI 가드레일(Model Armor), 민감 정보 비식별화(SDP) 설정 상태를 진단한다.
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


def get_gcloud_active_project() -> Optional[str]:
    """현재 활성화된 gcloud 프로젝트 ID를 조회한다."""
    try:
        res = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=True,
        )
        project = res.stdout.strip()
        if project and project != "(unset)":
            return project
    except Exception:
        pass
    return None


def get_mock_findings(project_id: str) -> List[Dict[str, Any]]:
    """가상 실행(--dry-run)을 위한 표준 모의 진단 데이터를 반환한다."""
    return [
        {
            "id": "FR-01",
            "category": "논리적 망 분리",
            "name": "VPC-SC 보안 경계 내 Vertex AI 보호 여부 (감독규정 제15조)",
            "status": "PASS",
            "current": "aiplatform.googleapis.com 이 서비스 경계(accessPolicies/123456/servicePerimeters/fsi_perimeter)에 등록됨",
            "requirement": "전자금융감독규정 제15조 제1항 제3호 및 제5호에 따른 망 분리 대체 통제로 Vertex AI, Cloud Storage, BigQuery가 지정된 서비스 보안 경계 내에 포함되어야 함",
            "remediation": "gcloud access-context-manager perimeters update fsi_perimeter --add-restricted-services=aiplatform.googleapis.com",
        },
        {
            "id": "FR-02",
            "category": "논리적 망 분리",
            "name": "VPC-SC 내부 실시간 웹 검색(Web Search Grounding) 격리 여부",
            "status": "WARN",
            "current": "VPC-SC 내부에서 web_search_tool 호출 시 egress 차단 위험 존재",
            "requirement": "외부 인터넷 직접 통신 차단 원칙에 따라 웹 검색이 필요한 워크로드는 DMZ 전용 프로젝트로 분리 후 비동기 벡터 DB 적재 아키텍처 적용 필요",
            "remediation": "외부 검색 연동 워크로드를 VPC-SC 외부 DMZ 프로젝트로 이관하고 내부 인스턴스로의 비동기 적재 파이프라인 구성 권장",
        },
        {
            "id": "FR-03",
            "category": "데이터 보호",
            "name": "Cloud Storage 불변 보존(Retention Policy / Bucket Lock) 5년 충족 여부 (법 제22조)",
            "status": "FAIL",
            "current": "지정 버킷에 보존 정책 미설정 (retention_period: 0s)",
            "requirement": "전자금융거래법 제22조 및 전자금융감독규정 제63조에 따라 감사 로그 및 AI 입출력 저장 버킷은 최소 5년(157,680,000초) 보존 및 잠금(Bucket Lock) 필수",
            "remediation": f"gcloud storage buckets update gs://{project_id}-audit-logs --retention-period=157680000s && gcloud storage buckets lock gs://{project_id}-audit-logs",
        },
        {
            "id": "FR-04",
            "category": "데이터 보호",
            "name": "고객 관리 암호화 키(CMEK) 전면 적용 여부 (감독규정 제14조)",
            "status": "PASS",
            "current": f"Cloud KMS 키(projects/{project_id}/locations/asia-northeast3/keyRings/fsi-ring/cryptoKeys/cmek-key) 정상 바인딩 확인",
            "requirement": "전자금융감독규정 제14조 및 1단계 특례 부가 조건에 따라 Cloud Storage 버킷 및 Vertex AI 파이프라인에 고객 관리 암호화 키(CMEK) 강제 필수",
            "remediation": f"gcloud storage buckets update gs://{project_id}-audit-logs --default-encryption-key=projects/{project_id}/locations/asia-northeast3/keyRings/fsi-ring/cryptoKeys/cmek-key",
        },
        {
            "id": "FR-05",
            "category": "감사 추적",
            "name": "데이터 접근 감사 로그(DATA_READ, DATA_WRITE) 활성화 여부 (법 제22조)",
            "status": "FAIL",
            "current": "aiplatform.googleapis.com 데이터 접근 로그 미설정 (ADMIN_READ 만 활성화됨)",
            "requirement": "전자금융거래법 제22조 및 전자금융감독규정 제14조에 따라 금융 거래 및 AI 추론 데이터 조회를 위해 DATA_READ, DATA_WRITE 로그 감사 필수 수집",
            "remediation": "gcloud projects get-iam-policy $PROJECT_ID 후 auditConfigs 에 aiplatform.googleapis.com 및 storage.googleapis.com 추가",
        },
        {
            "id": "FR-06",
            "category": "AI 모델 거버넌스",
            "name": "Model Armor 실시간 프롬프트 인젝션 및 탈옥 방어 가드레일 (특례 부가 조건)",
            "status": "PASS",
            "current": "Model Armor 템플릿(fsi-prompt-guard) 활성화 및 프롬프트 인젝션 탐지 필터 적용됨",
            "requirement": "금융위원회 1단계 샌드박스 특례 부가 조건에 따라 금융사 내부망 인그레스 사용자 프롬프트에 대한 탈옥 및 악성 명령 주입 실시간 방어 체계 구축 필수",
            "remediation": "gcloud beta model-armor templates create fsi-prompt-guard --location=asia-northeast3",
        },
        {
            "id": "FR-07",
            "category": "AI 모델 거버넌스",
            "name": "Sensitive Data Protection (SDP) 개인 신용 정보 가명 처리 템플릿 (신용정보법 제20조의2)",
            "status": "WARN",
            "current": "기본 민감 정보 템플릿 존재하나 주민등록번호(RRN) 및 계좌번호 특화 커스텀 InfoType 미등록",
            "requirement": "신용정보법 제20조의2 및 금융보안원 가이드라인에 따라 원본 개인 신용 정보 직접 입력 금지 및 주민등록번호, 계좌번호 특화 가명 처리 템플릿 등록 필수",
            "remediation": "gcloud dlp inspect-templates create --display-name='fsi-rrn-filter' --info-types=KOREA_RESIDENT_REGISTRATION_NUMBER",
        },
        {
            "id": "FR-08",
            "category": "접근 통제",
            "name": "서비스 계정 키(SA Key) 발급 차단 및 WIF 강제 (감독규정 제13조)",
            "status": "FAIL",
            "current": "조직 정책 iam.disableServiceAccountKeyCreation 미적용 (로컬 JSON 키 발급 가능 위험)",
            "requirement": "전자금융감독규정 제13조에 따라 단말기 및 전산 시스템 접근 자격 증명의 유출을 방지하기 위해 정적 서비스 계정 키 생성을 차단하고 Workload Identity Federation(WIF) 필수 적용",
            "remediation": f"gcloud resource-manager org-policies enable-enforce constraints/iam.disableServiceAccountKeyCreation --project={project_id}",
        },
        {
            "id": "FR-09",
            "category": "전송 보안",
            "name": "전송 구간 고강도 암호화(TLS 1.2+ 강제) 통제 (감독규정 제14조)",
            "status": "PASS",
            "current": "SSL 정책(fsi-tls-policy)을 통해 TLS 1.0, 1.1 차단 및 TLS 1.2+ 고강도 암호화 스위트 적용 확인",
            "requirement": "전자금융감독규정 제14조 제2항 제2호에 따라 통신 회선상 전송 데이터의 도청 방지를 위해 레거시 취약 TLS 버전을 차단하고 TLS 1.2 이상 및 안전한 암호화 알고리즘 강제",
            "remediation": "gcloud compute ssl-policies create fsi-tls-policy --profile=RESTRICTED --min-tls-version=1.2",
        },
    ]


def run_gcloud_json(cmd: List[str]) -> Optional[Any]:
    """gcloud 명령어를 실행하여 JSON 파싱 결과를 반환한다."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception:
        return None


def diagnose_live(project_id: str, location: str, audit_bucket: Optional[str], kms_key: Optional[str]) -> List[Dict[str, Any]]:
    """실제 GCP 환경의 보안 설정 상태를 진단한다."""
    findings = []
    print("[*] Google Cloud 실시간 제어 평면(Control Plane) 보안 설정을 진단한다...\n", flush=True)

    # 1. VPC-SC 서비스 경계 진단
    print("[1/9] VPC-SC 보안 경계 내 Vertex AI 보호 여부 확인 중...", flush=True)
    perimeter_data = run_gcloud_json(["gcloud", "access-context-manager", "perimeters", "list", "--format=json"])
    vpc_sc_pass = False
    vpc_sc_detail = "접근 가능한 서비스 경계가 없거나 권한이 부족함"
    if perimeter_data and isinstance(perimeter_data, list):
        for p in perimeter_data:
            status_obj = p.get("status", {})
            resources = status_obj.get("resources", [])
            restricted = status_obj.get("restrictedServices", [])
            # check project number or id in resources
            if any(project_id in str(r) for r in resources):
                if "aiplatform.googleapis.com" in restricted:
                    vpc_sc_pass = True
                    vpc_sc_detail = f"서비스 경계({p.get('name')}) 내 aiplatform.googleapis.com 보호 확인됨"
                    break
                else:
                    vpc_sc_detail = f"서비스 경계({p.get('name')})에 소속되어 있으나 aiplatform.googleapis.com 이 제한 서비스에 누락됨"

    findings.append({
        "id": "FR-01",
        "category": "논리적 망 분리",
        "name": "VPC-SC 보안 경계 내 Vertex AI 보호 여부",
        "status": "PASS" if vpc_sc_pass else "FAIL",
        "current": vpc_sc_detail,
        "requirement": "Vertex AI, Cloud Storage, BigQuery가 지정된 서비스 보안 경계 내에 포함되어야 함",
        "remediation": f"gcloud access-context-manager perimeters update <PERIMETER_NAME> --add-restricted-services=aiplatform.googleapis.com",
    })

    # 2. VPC-SC Web Search Grounding 격리 진단
    print("[2/9] VPC-SC 내부 실시간 웹 검색(Web Search Grounding) 격리 여부 점검 중...", flush=True)
    findings.append({
        "id": "FR-02",
        "category": "논리적 망 분리",
        "name": "VPC-SC 내부 실시간 웹 검색(Web Search Grounding) 격리 여부",
        "status": "WARN",
        "current": "VPC-SC 보안 경계 적용 시 실시간 구글 웹 검색 툴(web_search_tool)이 Egress 정책 위반으로 차단될 수 있음",
        "requirement": "외부 인터넷 웹 검색이 필요한 워크로드는 DMZ 전용 프로젝트로 분리 후 비동기 벡터 DB 적재 아키텍처 적용 필요",
        "remediation": "외부 검색 연동 워크로드를 VPC-SC 외부 DMZ 프로젝트로 이관하고 내부 인스턴스로의 비동기 적재 파이프라인 구성 권장",
    })

    # 3. Cloud Storage 불변 보존 (Retention Policy / Bucket Lock)
    target_bucket = audit_bucket or f"{project_id}-fsi-audit"
    print(f"[3/9] Cloud Storage(gs://{target_bucket}) 5년 불변 보존 및 Bucket Lock 조회 중...", flush=True)
    bucket_info = run_gcloud_json(["gcloud", "storage", "buckets", "describe", f"gs://{target_bucket}", "--format=json"])
    retention_pass = False
    retention_detail = f"버킷 gs://{target_bucket} 조회가 불가능하거나 미생성 상태임"
    if bucket_info and isinstance(bucket_info, dict):
        ret_policy = bucket_info.get("retention_policy") or bucket_info.get("retentionPolicy")
        if ret_policy:
            period = int(ret_policy.get("retention_period", 0) or ret_policy.get("retentionPeriod", 0))
            is_locked = ret_policy.get("is_locked", False) or ret_policy.get("isLocked", False)
            if period >= 157680000 and is_locked:
                retention_pass = True
                retention_detail = f"5년(157,680,000초) 보존 정책 설정 및 Bucket Lock 완료됨"
            elif period >= 157680000:
                retention_detail = f"보존 기간은 {period}초로 5년 이상이나 Bucket Lock 이 잠기지 않음"
            else:
                retention_detail = f"보존 기간이 {period}초로 규정 요건(5년: 157,680,000초)에 미달함"
        else:
            retention_detail = f"버킷에 보존 정책(Retention Policy)이 설정되지 않음"

    findings.append({
        "id": "FR-03",
        "category": "데이터 보호",
        "name": "Cloud Storage 불변 보존(Retention Policy / Bucket Lock) 5년 충족 여부",
        "status": "PASS" if retention_pass else "FAIL",
        "current": retention_detail,
        "requirement": "금융 규제 요건에 따라 감사 로그 및 AI 입출력 저장 버킷은 최소 5년(157,680,000초) 보존 및 잠금(Bucket Lock) 필수",
        "remediation": f"gcloud storage buckets update gs://{target_bucket} --retention-period=157680000s && gcloud storage buckets lock gs://{target_bucket}",
    })

    # 4. 고객 관리 암호화 키 (CMEK) 진단
    print(f"[4/9] 고객 관리 암호화 키(CMEK) 적용 상태 검사 중...", flush=True)
    cmek_pass = False
    cmek_detail = f"버킷 gs://{target_bucket} 에 CMEK 암호화 설정이 미적용됨"
    if bucket_info and isinstance(bucket_info, dict):
        enc = bucket_info.get("encryption", {})
        default_kms = enc.get("default_kms_key_name") or enc.get("defaultKmsKeyName")
        if default_kms:
            cmek_pass = True
            cmek_detail = f"버킷 기본 암호화 키로 CMEK({default_kms})가 적용됨"
    findings.append({
        "id": "FR-04",
        "category": "데이터 보호",
        "name": "고객 관리 암호화 키(CMEK) 전면 적용 여부",
        "status": "PASS" if cmek_pass else "FAIL",
        "current": cmek_detail,
        "requirement": "Cloud Storage 버킷 및 Vertex AI 파이프라인에 사내 고객 관리 암호화 키(CMEK) 강제",
        "remediation": f"gcloud storage buckets update gs://{target_bucket} --default-encryption-key=<KMS_KEY_NAME>",
    })

    # 5. 감사 로그 (Audit Logs) 진단
    print(f"[5/9] 프로젝트 IAM 데이터 접근 감사 로그(DATA_READ/WRITE) 조회 중...", flush=True)
    iam_policy = run_gcloud_json(["gcloud", "projects", "get-iam-policy", project_id, "--format=json"])
    audit_pass = False
    audit_detail = "프로젝트 IAM 정책에서 감사 로그(auditConfigs) 설정 조회 실패 또는 미설정"
    if iam_policy and isinstance(iam_policy, dict):
        audit_configs = iam_policy.get("auditConfigs", [])
        aiplatform_audited = False
        for ac in audit_configs:
            svc = ac.get("service")
            if svc in ["allServices", "aiplatform.googleapis.com"]:
                log_types = [entry.get("logType") for entry in ac.get("auditLogConfigs", [])]
                if "DATA_READ" in log_types and "DATA_WRITE" in log_types:
                    aiplatform_audited = True
                    break
        if aiplatform_audited:
            audit_pass = True
            audit_detail = "Vertex AI 및 전체 서비스에 대해 DATA_READ, DATA_WRITE 감사 로그 수집 활성화됨"
        else:
            audit_detail = "Vertex AI 에 대한 DATA_READ 또는 DATA_WRITE 감사 로그가 누락됨"

    findings.append({
        "id": "FR-05",
        "category": "감사 추적",
        "name": "데이터 접근 감사 로그(DATA_READ, DATA_WRITE) 활성화 여부",
        "status": "PASS" if audit_pass else "FAIL",
        "current": audit_detail,
        "requirement": "금융 거래 및 AI 추론 데이터 조회를 위해 DATA_READ, DATA_WRITE 로그 감사 필수 수집",
        "remediation": f"gcloud projects get-iam-policy {project_id} 에 aiplatform.googleapis.com DATA_READ/DATA_WRITE 추가",
    })

    # 6. Model Armor 가드레일 진단
    print(f"[6/9] Model Armor 실시간 프롬프트 인젝션 방어 가드레일 조회 중 (리전: {location})...", flush=True)
    model_armor_templates = run_gcloud_json(["gcloud", "beta", "model-armor", "templates", "list", f"--location={location}", "--format=json"])
    ma_pass = False
    ma_detail = f"리전({location}) 내에 활성화된 Model Armor 템플릿이 없음"
    if model_armor_templates and isinstance(model_armor_templates, list) and len(model_armor_templates) > 0:
        ma_pass = True
        ma_names = [t.get("name", "").split("/")[-1] for t in model_armor_templates]
        ma_detail = f"Model Armor 템플릿 발견됨: {', '.join(ma_names)}"

    findings.append({
        "id": "FR-06",
        "category": "AI 모델 거버넌스",
        "name": "Model Armor 실시간 프롬프트 인젝션 및 탈옥 방어 가드레일",
        "status": "PASS" if ma_pass else "FAIL",
        "current": ma_detail,
        "requirement": "금융사 내부망 인그레스 사용자 프롬프트에 대한 탈옥 및 악성 명령 주입 실시간 방어 체계 구축 필수",
        "remediation": f"gcloud beta model-armor templates create fsi-prompt-guard --location={location}",
    })

    # 7. Sensitive Data Protection (SDP) 진단
    print(f"[7/9] Sensitive Data Protection(SDP) 개인 신용 정보 가명 처리 템플릿 검사 중 (리전: {location})...", flush=True)
    dlp_templates = run_gcloud_json(["gcloud", "dlp", "inspect-templates", "list", f"--location={location}", "--format=json"])
    sdp_pass = False
    sdp_detail = f"리전({location}) 내에 등록된 DLP 검사 템플릿이 없음"
    if dlp_templates and isinstance(dlp_templates, list) and len(dlp_templates) > 0:
        sdp_pass = True
        sdp_detail = f"DLP 검사 템플릿 {len(dlp_templates)}개 등록 확인됨"

    findings.append({
        "id": "FR-07",
        "category": "AI 모델 거버넌스",
        "name": "Sensitive Data Protection (SDP) 개인 신용 정보 가명 처리 템플릿",
        "status": "PASS" if sdp_pass else "WARN",
        "current": sdp_detail,
        "requirement": "신용정보법 제20조의2 및 금융보안원 가이드라인에 따라 원본 개인 신용 정보 직접 입력 금지 및 주민등록번호, 계좌번호 특화 가명 처리 템플릿 등록 필수",
        "remediation": f"gcloud dlp inspect-templates create --location={location} --display-name='fsi-rrn-filter'",
    })

    # 8. 서비스 계정 키 발급 제한 조직 정책 진단 (전자금융감독규정 제13조)
    print(f"[8/9] 서비스 계정 키 발급 제한 조직 정책(Org Policy) 검증 중...", flush=True)
    sa_key_policy = run_gcloud_json([
        "gcloud", "resource-manager", "org-policies", "describe",
        "constraints/iam.disableServiceAccountKeyCreation",
        f"--project={project_id}",
        "--format=json",
    ])
    sa_key_pass = False
    sa_key_detail = "조직 정책 iam.disableServiceAccountKeyCreation 설정 미조회 또는 미적용"
    if sa_key_policy and isinstance(sa_key_policy, dict):
        rules = sa_key_policy.get("spec", {}).get("rules", [])
        if any(r.get("enforce", False) for r in rules):
            sa_key_pass = True
            sa_key_detail = "정적 서비스 계정 키 발급 제한(disableServiceAccountKeyCreation) 강제 적용됨"
    findings.append({
        "id": "FR-08",
        "category": "접근 통제",
        "name": "서비스 계정 키(SA Key) 발급 차단 및 WIF 강제 (감독규정 제13조)",
        "status": "PASS" if sa_key_pass else "FAIL",
        "current": sa_key_detail,
        "requirement": "전자금융감독규정 제13조에 따라 단말기 및 전산 시스템 접근 자격 증명의 유출을 방지하기 위해 정적 서비스 계정 키 생성을 차단하고 Workload Identity Federation(WIF) 필수 적용",
        "remediation": f"gcloud resource-manager org-policies enable-enforce constraints/iam.disableServiceAccountKeyCreation --project={project_id}",
    })

    # 9. SSL/TLS 정책 진단 (전자금융감독규정 제14조)
    print(f"[9/9] 전송 구간 SSL/TLS 1.2+ 고강도 암호화 정책 조회 중...\n", flush=True)
    ssl_policies = run_gcloud_json(["gcloud", "compute", "ssl-policies", "list", f"--project={project_id}", "--format=json"])
    ssl_pass = False
    ssl_detail = "프로젝트 내에 커스텀 SSL 정책(TLS 1.2+)이 미구성됨"
    if ssl_policies and isinstance(ssl_policies, list) and len(ssl_policies) > 0:
        for sp in ssl_policies:
            min_tls = sp.get("minTlsVersion", "")
            if min_tls in ["TLS_1_2", "TLS_1_3"]:
                ssl_pass = True
                ssl_detail = f"안전한 SSL 정책({sp.get('name')}) 적용 (최소 버전: {min_tls})"
                break
    findings.append({
        "id": "FR-09",
        "category": "전송 보안",
        "name": "전송 구간 고강도 암호화(TLS 1.2+ 강제) 통제 (감독규정 제14조)",
        "status": "PASS" if ssl_pass else "WARN",
        "current": ssl_detail,
        "requirement": "전자금융감독규정 제14조 제2항 제2호에 따라 통신 회선상 전송 데이터의 도청 방지를 위해 레거시 취약 TLS 버전을 차단하고 TLS 1.2 이상 및 안전한 암호화 알고리즘 강제",
        "remediation": "gcloud compute ssl-policies create fsi-tls-policy --profile=RESTRICTED --min-tls-version=1.2",
    })

    return findings


def print_report(project_id: str, location: str, is_dry_run: bool, findings: List[Dict[str, Any]]) -> int:
    """진단 리포트를 단호하고 격조 높은 문어체로 포맷하여 출력한다."""
    print("=" * 88)
    print(" 혁신 금융 서비스(FSI) 규제 준수 보안 경계 진단 리포트")
    print(f" 대상 프로젝트: {project_id} | 점검 리전: {location} | 실행 모드: {'가상 진단 (Dry-Run)' if is_dry_run else '실제 환경 스캔'}")
    print("=" * 88)
    print()

    pass_count = sum(1 for f in findings if f["status"] == "PASS")
    warn_count = sum(1 for f in findings if f["status"] == "WARN")
    fail_count = sum(1 for f in findings if f["status"] == "FAIL")
    total_count = len(findings)

    print(f"진단 요약: 총 {total_count}개 규제 항목 중 충족 {pass_count}건, 주의 {warn_count}건, 미달 {fail_count}건")
    print("-" * 88)
    print(f"{'ID':<12} | {'분류':<14} | {'상태':<6} | {'진단 항목 및 현황'}")
    print("-" * 88)

    for f in findings:
        status_text = f"[{f['status']}]"
        print(f"{f['id']:<12} | {f['category']:<14} | {status_text:<6} | {f['name']}")
        print(f"  - 현재 상태: {f['current']}")
        if f["status"] != "PASS":
            print(f"  - 규제 요건: {f['requirement']}")
            print(f"  - 조치 권고: {f['remediation']}")
        print()

    print("=" * 88)
    print("종합 평가 및 감사 준비 가이드:")
    if fail_count > 0:
        print("본 진단 결과 규제 필수 요건에 미달하는 항목이 존재한다.")
        print("금융감독원 현장 실사 및 금융보안원 보안성 심의 전 미달(FAIL) 항목을 우선 조치해야 한다.")
        print("특히 스토리지 5년 불변 보존(Bucket Lock) 및 Vertex AI 감사 로깅은 필수 소명 대상이다.")
    else:
        print("모든 필수 보안 통제가 규제 당국의 가이드라인을 충족하고 있다.")
        print("사후 감사 대응을 위해 정기적인 로그 무결성 검증 파이프라인을 유지해야 한다.")
    print("=" * 88)

    return 1 if fail_count > 0 else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="혁신 금융 서비스(FSI) 생성형 AI 보안 경계 및 규제 컴플라이언스 진단 도구"
    )
    parser.add_argument("-p", "--project", help="대상 Google Cloud 프로젝트 ID")
    parser.add_argument("-l", "--location", default="asia-northeast3", help="검사 대상 리전 (기본값: asia-northeast3)")
    parser.add_argument("--audit-bucket", help="FSI 감사 및 데이터 저장용 Cloud Storage 버킷 명")
    parser.add_argument("--kms-key", help="고객 관리 암호화 키(CMEK) 리소스 경로")
    parser.add_argument("--dry-run", action="store_true", help="실제 GCP API 호출 없이 모의 가상 데이터를 이용해 스모크 테스트 수행")

    args = parser.parse_args()

    if args.dry_run:
        project_id = args.project or "example-fsi-corp"
    else:
        project_id = args.project or os.environ.get("PROJECT_ID") or get_gcloud_active_project()
        if not project_id:
            print("오류: 프로젝트 ID가 지정되지 않았다. -p/--project 인자 또는 PROJECT_ID 환경 변수를 설정해야 한다.", file=sys.stderr)
            sys.exit(2)

    mode_str = "가상 진단 (Dry-Run)" if args.dry_run else "실제 환경 스캔"
    print("=" * 88, flush=True)
    print(" 혁신 금융 서비스(FSI) 규제 준수 보안 경계 진단 도구", flush=True)
    print(f" 대상 프로젝트: {project_id} | 점검 리전: {args.location} | 실행 모드: {mode_str}", flush=True)
    print("=" * 88, flush=True)
    print(flush=True)

    if args.dry_run:
        print("[*] 가상 모의 감사 데이터를 로드하고 점검 항목을 시뮬레이션한다...\n", flush=True)
        findings = get_mock_findings(project_id)
    else:
        findings = diagnose_live(project_id, args.location, args.audit_bucket, args.kms_key)

    exit_code = print_report(project_id, args.location, args.dry_run, findings)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
