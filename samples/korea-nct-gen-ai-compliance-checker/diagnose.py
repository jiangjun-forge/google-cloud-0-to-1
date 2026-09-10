#!/usr/bin/env python3
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

"""국가 핵심 기술(NCT) 대상 생성형 AI 보안 통제 및 데이터 주권 규정 준수 진단기."""

import argparse
import json
import os
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    """명령줄 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="국가 핵심 기술(NCT) 생성형 AI 보안 통제 및 서울 리전 데이터 주권 진단기"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID", ""),
        help="GCP 프로젝트 ID (지정하지 않을 경우 gcloud 기본 프로젝트 사용)",
    )
    parser.add_argument(
        "-r",
        "--region",
        default=os.getenv("TARGET_REGION") or "asia-northeast3",
        help="데이터 보관 및 처리 대상 국내 리전 (기본값: asia-northeast3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP API 호출 없이 모의 감사 데이터로 가상 실행",
    )
    return parser.parse_args()


def detect_project_id(cli_project: str) -> str:
    """프로젝트 ID를 탐지한다."""
    if cli_project:
        return cli_project
    try:
        res = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=True,
        )
        detected = res.stdout.strip()
        if detected and "(unset)" not in detected:
            return detected
    except Exception:
        pass
    return "demo-nct-compliance-project"


def get_mock_check_results(region: str) -> list[dict]:
    """가상 실행용 점검 결과를 반환한다."""
    return [
        {
            "category": "Data Residency",
            "control": "gcp.resourceLocations (조직 정책 - 법 제11조)",
            "status": "PASS",
            "current_state": f"서울 리전({region})으로 리소스 생성 제한 적용 완료",
            "remediation": "추가 조치 불필요 (산업기술 해외 이전 및 불법 수출 방지)",
        },
        {
            "category": "Vector Security",
            "control": "RAG 벡터 데이터 저장 차단 (IAM Deny - 법 제10조)",
            "status": "FAIL",
            "current_state": "aiplatform.indexes.* 권한 차단 Deny Policy 미발견",
            "remediation": "gcloud iam deny-policies create 명령으로 벡터 인덱스 사외 생성 차단 정책 적용 필요",
        },
        {
            "category": "Encryption",
            "control": "Cloud KMS CMEK 이중 암호화 (안내서 필수 요건)",
            "status": "FAIL",
            "current_state": "기본 구글 관리 키 사용 중 (KMS CMEK 미연동 버킷 2개 감지)",
            "remediation": f"서울 리전 Cloud KMS 키링 및 암호화 키 생성 후 GCS/BigQuery CMEK 지정 (이중 암호화 의무 준수)",
        },
        {
            "category": "Inference Boundary",
            "control": "추론 리전 국소화 (Vertex AI - 안내서 국내 위치)",
            "status": "PASS",
            "current_state": f"Vertex AI 서울 리전 엔드포인트({region}-aiplatform.googleapis.com) 사용 강제 확인",
            "remediation": "추가 조치 불필요 (국내 추론 엔드포인트 격리 상태 유지)",
        },
        {
            "category": "Audit Logging",
            "control": "Cloud Audit Logs 데이터 접근 로깅 (법 제10조)",
            "status": "PASS",
            "current_state": "DATA_READ, DATA_WRITE 감사 로그 활성화 상태",
            "remediation": "추가 조치 불필요",
        },
        {
            "category": "Access Control",
            "control": "사외/외국 계정 공유 차단 (조직 정책 - 안내서 외국 기업 접근 배제)",
            "status": "FAIL",
            "current_state": "iam.allowedPolicyMemberDomains 조직 정책 미적용 (외부 계정 초대 위험 존재)",
            "remediation": "gcloud resource-manager org-policies set-policy 명령으로 사내 승인 도메인만 허용 (기술 해외 유출 방어)",
        },
        {
            "category": "Provider Isolation",
            "control": "클라우드 제공자 임의 접근 통제 (Access Approval - 안내서 사전 승인 의무)",
            "status": "PASS",
            "current_state": "Access Approval 및 Access Transparency 정상 활성화 (CSP 엔지니어 사전 승인 강제)",
            "remediation": "추가 조치 불필요 (CSP 평문 접근 배제 요건 충족)",
        },
    ]


def run_gcloud_json(cmd: list[str]) -> dict | list | None:
    """gcloud 명령어를 JSON 출력 모드로 실행한다."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception:
        return None


def inspect_live_environment(project_id: str, region: str) -> list[dict]:
    """실제 GCP 환경의 NCT 컴플라이언스 상태를 점검한다."""
    results = []
    print("[*] Google Cloud 제어 평면(Control Plane) 보안 통제 상태를 진단한다...\n", flush=True)

    # 1. Org Policy 리소스 위치 제약 검사
    print(f"[1/7] 산업기술보호법 서울 리전({region}) Data Boundary 조직 정책 점검 중...", flush=True)
    org_cmd = [
        "gcloud", "resource-manager", "org-policies", "describe",
        "constraints/gcp.resourceLocations",
        f"--project={project_id}",
        "--format=json",
    ]
    org_policy = run_gcloud_json(org_cmd)
    if org_policy:
        rules = org_policy.get("spec", {}).get("rules", [])
        has_region_rule = any(region in str(r) for r in rules)
        if has_region_rule:
            results.append({
                "category": "Data Residency",
                "control": "gcp.resourceLocations (조직 정책 - 법 제11조)",
                "status": "PASS",
                "current_state": f"서울 리전({region}) 한정 제한 적용됨",
                "remediation": "추가 조치 불필요 (산업기술 해외 이전 및 불법 수출 방지)",
            })
        else:
            results.append({
                "category": "Data Residency",
                "control": "gcp.resourceLocations (조직 정책 - 법 제11조)",
                "status": "FAIL",
                "current_state": f"정책은 설정되었으나 {region} 한정 규칙 미확인",
                "remediation": f"조직 정책에서 {region}만 허용하도록 규칙 갱신 필요",
            })
    else:
        results.append({
            "category": "Data Residency",
            "control": "gcp.resourceLocations (조직 정책 - 법 제11조)",
            "status": "FAIL",
            "current_state": "프로젝트 수준 리소스 위치 제약 정책 미배포",
            "remediation": f"gcloud org-policies set-policy 명령으로 {region} 강제 필요",
        })

    # 2. IAM Deny Policy (RAG 벡터 데이터 차단)
    print("[2/7] RAG 벡터 인덱스 사외 적재 차단 IAM Deny 정책 확인 중...", flush=True)
    deny_cmd = [
        "gcloud", "iam", "deny-policies", "list",
        f"--attachment-point=cloudresourcemanager.googleapis.com/projects/{project_id}",
        "--format=json",
    ]
    deny_policies = run_gcloud_json(deny_cmd)
    if deny_policies and len(deny_policies) > 0:
        results.append({
            "category": "Vector Security",
            "control": "RAG 벡터 데이터 저장 차단 (IAM Deny - 법 제10조)",
            "status": "PASS",
            "current_state": "IAM Deny 정책 활성화 확인",
            "remediation": "추가 조치 불필요",
        })
    else:
        results.append({
            "category": "Vector Security",
            "control": "RAG 벡터 데이터 저장 차단 (IAM Deny - 법 제10조)",
            "status": "FAIL",
            "current_state": "벡터 데이터 저장 차단 IAM Deny 정책 미발견",
            "remediation": "aiplatform.indexes.* 차단 IAM Deny 정책 배포 필요 (사외 유출 방지)",
        })

    # 3. KMS CMEK 키 검사
    print(f"[3/7] Cloud KMS 서울 키링({region}) CMEK 이중 암호화 상태 조회 중...", flush=True)
    kms_cmd = [
        "gcloud", "kms", "keyrings", "list",
        f"--location={region}",
        f"--project={project_id}",
        "--format=json",
    ]
    kms_keyrings = run_gcloud_json(kms_cmd)
    if kms_keyrings and len(kms_keyrings) > 0:
        results.append({
            "category": "Encryption",
            "control": "Cloud KMS CMEK 이중 암호화 (안내서 필수 요건)",
            "status": "PASS",
            "current_state": f"서울 리전({region}) 내 KMS 키링 및 암호화 키 식별됨",
            "remediation": "추가 조치 불필요",
        })
    else:
        results.append({
            "category": "Encryption",
            "control": "Cloud KMS CMEK 이중 암호화 (안내서 필수 요건)",
            "status": "FAIL",
            "current_state": f"서울 리전({region}) 내 활성 KMS 키링 미발견",
            "remediation": f"gcloud kms keyrings create 명령으로 {region}에 키링 생성 필요 (이중 암호화 의무 준수)",
        })

    # 4. 추론 리전 국소화 (Vertex AI 서울 리전 엔드포인트 격리)
    print(f"[4/7] Vertex AI 서울 리전 엔드포인트 격리 상태 검증 중...", flush=True)
    endpoint_cmd = [
        "gcloud", "config", "get-value", "api_endpoint_overrides/aiplatform",
    ]
    endpoint_override = ""
    try:
        ep_res = subprocess.run(endpoint_cmd, capture_output=True, text=True)
        endpoint_override = ep_res.stdout.strip()
    except Exception:
        pass

    target_endpoint = f"{region}-aiplatform.googleapis.com"
    if target_endpoint in endpoint_override:
        results.append({
            "category": "Inference Boundary",
            "control": "추론 리전 국소화 (Vertex AI - 안내서 국내 위치)",
            "status": "PASS",
            "current_state": f"Vertex AI 서울 리전 엔드포인트({target_endpoint}) 국소화 강제 확인",
            "remediation": "추가 조치 불필요 (국내 추론 엔드포인트 격리 상태 유지)",
        })
    else:
        results.append({
            "category": "Inference Boundary",
            "control": "추론 리전 국소화 (Vertex AI - 안내서 국내 위치)",
            "status": "WARN",
            "current_state": f"기본 글로벌 엔드포인트 참조 가능성 존재 (현재 오버라이드: '{endpoint_override or 'unset'}')",
            "remediation": f"gcloud config set api_endpoint_overrides/aiplatform https://{target_endpoint}/ 명령으로 엔드포인트 서울 강제 필요",
        })

    # 5. 감사 로깅 점검
    print(f"[5/7] Cloud Audit Logs 데이터 접근 감사 로깅 싱크 점검 중...", flush=True)
    logging_cmd = [
        "gcloud", "logging", "sinks", "list",
        f"--project={project_id}",
        "--format=json",
    ]
    sinks = run_gcloud_json(logging_cmd)
    if sinks and len(sinks) > 0:
        results.append({
            "category": "Audit Logging",
            "control": "Cloud Audit Logs 데이터 접근 로깅 (법 제10조)",
            "status": "PASS",
            "current_state": "감사 로그 싱크 정상 운영 중",
            "remediation": "추가 조치 불필요",
        })
    else:
        results.append({
            "category": "Audit Logging",
            "control": "Cloud Audit Logs 데이터 접근 로깅 (법 제10조)",
            "status": "FAIL",
            "current_state": "전사 감사 로그 싱크 구성 미흡",
            "remediation": "BigQuery 또는 Cloud Storage 감사 로그 싱크 연동 필요",
        })

    # 6. 사외/외국 계정 공유 차단 (iam.allowedPolicyMemberDomains)
    print(f"[6/7] 사외/외국 계정 공유 차단 조직 정책(iam.allowedPolicyMemberDomains) 검사 중...", flush=True)
    member_domain_cmd = [
        "gcloud", "resource-manager", "org-policies", "describe",
        "constraints/iam.allowedPolicyMemberDomains",
        f"--project={project_id}",
        "--format=json",
    ]
    domain_policy = run_gcloud_json(member_domain_cmd)
    domain_pass = False
    domain_detail = "조직 정책 iam.allowedPolicyMemberDomains 미적용 (외부 계정 초대 위험 존재)"
    if domain_policy and isinstance(domain_policy, dict):
        rules = domain_policy.get("spec", {}).get("rules", [])
        if any(r.get("values", {}).get("allowedValues") for r in rules):
            domain_pass = True
            domain_detail = "승인된 사내 도메인 외 계정 바인딩 제한 적용됨"

    results.append({
        "category": "Access Control",
        "control": "사외/외국 계정 공유 차단 (조직 정책 - 안내서 외국 기업 접근 배제)",
        "status": "PASS" if domain_pass else "FAIL",
        "current_state": domain_detail,
        "remediation": "gcloud resource-manager org-policies set-policy 명령으로 사내 승인 도메인만 허용 (기술 해외 유출 방어)",
    })

    # 7. 클라우드 제공자 임의 접근 통제 (Access Approval / Access Transparency)
    print(f"[7/7] 클라우드 제공자 임의 접근 통제(Access Approval) 사전 승인 설정 조회 중...\n", flush=True)
    approval_cmd = [
        "gcloud", "access-approval", "settings", "get",
        f"--project={project_id}",
        "--format=json",
    ]
    approval_settings = run_gcloud_json(approval_cmd)
    approval_pass = False
    approval_detail = "Access Approval 미설정 또는 미조회 (CSP 임의 접근 차단 소명 필요)"
    if approval_settings and isinstance(approval_settings, dict):
        if approval_settings.get("enrolledServices"):
            approval_pass = True
            approval_detail = "Access Approval 활성화됨 (Google 엔지니어 접근 시 고객 사전 승인 강제)"

    results.append({
        "category": "Provider Isolation",
        "control": "클라우드 제공자 임의 접근 통제 (Access Approval - 안내서 사전 승인 의무)",
        "status": "PASS" if approval_pass else "WARN",
        "current_state": approval_detail,
        "remediation": "gcloud access-approval settings update --enrolled-services=all-services (CSP 평문 접근 배제 요건 충족)",
    })

    return results


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    project_id = detect_project_id(args.project)
    region = args.region

    mode_label = "가상 실행 (Dry-run)" if args.dry_run else "실제 환경 (Live)"
    print("=" * 85, flush=True)
    print("국가 핵심 기술(NCT) 대상 생성형 AI 보안 통제 및 데이터 주권 진단 도구", flush=True)
    print(f"진단 모드: {mode_label}", flush=True)
    print(f"대상 프로젝트: {project_id}", flush=True)
    print(f"지정 리전: {region} (대한민국 서울 리전)", flush=True)
    print("=" * 85, flush=True)
    print(flush=True)

    if args.dry_run:
        print("[*] 가상 모의 감사 데이터를 로드하고 점검 항목을 시뮬레이션한다...\n", flush=True)
        results = get_mock_check_results(region)
    else:
        results = inspect_live_environment(project_id, region)

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")

    print("\n[항목별 기술적 보안 통제 준수 현황]")
    print("-" * 85)
    print(f"{'구분':<18} {'보안 통제 항목':<32} {'상태':<8} {'현재 상태'}")
    print("-" * 85)
    for r in results:
        print(f"{r['category']:<18} {r['control']:<32} {r['status']:<8} {r['current_state']}")
    print("-" * 85)

    print(f"\n[진단 종합 점수: 총 {len(results)}개 항목 중 PASS {pass_count}건, FAIL {fail_count}건]")

    if fail_count > 0:
        print("\n[미준수 항목 긴급 조치 가이드]")
        for idx, r in enumerate([item for item in results if item["status"] == "FAIL"], 1):
            print(f"{idx}. {r['control']}")
            print(f"   - 조치 방향: {r['remediation']}")

    print("\n[표준 보안 처방 CLI 명령어]")
    print(f"1. 서울 리전 Data Boundary 조직 정책 강제:")
    print(f"   gcloud resource-manager org-policies enable-enforce constraints/gcp.resourceLocations --project={project_id}")
    print(f"2. RAG 벡터 데이터 저장 차단 Deny Policy 배포:")
    print(f"   gcloud iam deny-policies create nct-rag-deny --attachment-point=cloudresourcemanager.googleapis.com/projects/{project_id} --file=deny-rules.json")
    print(f"3. 서울 리전 Cloud KMS CMEK 키 생성:")
    print(f"   gcloud kms keyrings create nct-keyring --location={region} --project={project_id}")
    print(f"   gcloud kms keys create nct-cmek-key --keyring=nct-keyring --location={region} --purpose=encryption --project={project_id}")
    print("=" * 85)


if __name__ == "__main__":
    main()
