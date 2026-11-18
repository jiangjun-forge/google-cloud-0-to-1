#!/usr/bin/env python3
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
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

"""Cloud Armor 기반 Java4Shell (CVE-2026-114938) 가상 패치 및 노출 진단기."""

import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

SCENARIO_SLUG = "cloud-armor-java4shell-guard"
STANDARD_LABELS = (
    f"managed-by=google-cloud-0-to-1,scenario={SCENARIO_SLUG},"
    "env=sample,created-by=customer-engineer"
)
AVX512_VBMI_SERIES = {
    "n2",
    "c3",
    "c3d",
    "c4",
    "c4d",
    "n4",
    "n4d",
    "m3",
    "m4",
    "a3",
    "a4",
    "g4",
    "h3",
    "x4",
    "z3",
}


def load_dotenv_file(env_path: pathlib.Path) -> None:
    """로컬 .env 파일이 존재하면 환경 변수에 적재한다."""
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and val and key not in os.environ:
            os.environ[key] = val


def parse_args() -> argparse.Namespace:
    """명령줄 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="Cloud Armor 기반 Java4Shell (CVE-2026-114938) 가상 패치 및 노출 진단기"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID", ""),
        help="GCP 프로젝트 ID (미입력 시 gcloud 활성 프로젝트 자동 감지)",
    )
    parser.add_argument(
        "-r",
        "--region",
        default=os.getenv("REGION") or "asia-northeast3",
        help="점검 대상 리전 (기본값: asia-northeast3)",
    )
    parser.add_argument(
        "--policy",
        default=os.getenv("CLOUD_ARMOR_POLICY", ""),
        help="점검 대상 Cloud Armor Security Policy 이름",
    )
    parser.add_argument(
        "--backend-service",
        default=os.getenv("BACKEND_SERVICE", ""),
        help="점검 대상 External ALB Backend Service 이름",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP API 호출 없이 모의 데이터로 진단 시뮬레이션 실행",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        default=False,
        help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장",
    )
    return parser.parse_args()


def run_gcloud_json(cmd: List[str]) -> Optional[Any]:
    """gcloud CLI를 --format=json으로 안전하게 실행하고 파싱 결과를 반환한다."""
    try:
        res = subprocess.run(
            cmd + ["--format=json"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return json.loads(res.stdout) if res.stdout.strip() else []
    except Exception:
        return None


def get_gcloud_config_value(key: str) -> str:
    """gcloud config get-value 결과를 반환한다."""
    try:
        res = subprocess.run(
            ["gcloud", "config", "get-value", key],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        val = res.stdout.strip()
        return "" if not val or "(unset)" in val else val
    except Exception:
        return ""


def select_from_candidates(title: str, items: List[str]) -> str:
    """복수 후보가 있을 때 대화형 번호 선택기 또는 첫 번째 후보를 반환한다."""
    if not items:
        return ""
    if len(items) == 1 or not sys.stdin.isatty():
        return items[0]
    print(f"\n[선택] {title} 후보 목록:")
    for idx, item in enumerate(items, 1):
        print(f"  [{idx}] {item}")
    choice = input("번호 입력 (Enter 시 1번 자동 선택): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(items):
        return items[int(choice) - 1]
    return items[0]


def resolve_project_id(cli_project: str, dry_run: bool) -> str:
    """계층형 폴백으로 프로젝트 ID를 확정한다."""
    if dry_run:
        return "sample-project-id"
    if cli_project:
        return cli_project
    detected = get_gcloud_config_value("project")
    if detected:
        return detected
    projects = run_gcloud_json(["gcloud", "projects", "list"])
    if isinstance(projects, list) and projects:
        candidates = [p["projectId"] for p in projects if "projectId" in p]
        return select_from_candidates("Google Cloud 프로젝트", candidates)
    return ""


def run_config_mode(base_dir: pathlib.Path) -> None:
    """대화형 설정 마법사로 .env 파일을 생성한다."""
    print("=" * 72)
    print(f"[{SCENARIO_SLUG}] 대화형 환경 설정 마법사")
    print("=" * 72)
    default_proj = get_gcloud_config_value("project")
    default_region = get_gcloud_config_value("compute/region") or "asia-northeast3"

    proj_in = input(f"1. PROJECT_ID [{default_proj or '미지정'}]: ").strip()
    project_id = proj_in or default_proj

    region_in = input(f"2. REGION [{default_region}]: ").strip()
    region = region_in or default_region

    policy_name = ""
    backend_name = ""
    if project_id:
        policies = run_gcloud_json(
            ["gcloud", "compute", "security-policies", "list", f"--project={project_id}"]
        )
        if isinstance(policies, list) and policies:
            policy_names = [p.get("name", "") for p in policies if p.get("name")]
            policy_name = select_from_candidates("Cloud Armor Security Policy", policy_names)

        backends = run_gcloud_json(
            ["gcloud", "compute", "backend-services", "list", f"--project={project_id}"]
        )
        if isinstance(backends, list) and backends:
            backend_names = [b.get("name", "") for b in backends if b.get("name")]
            backend_name = select_from_candidates("External ALB Backend Service", backend_names)

    env_lines = [
        f"PROJECT_ID={project_id}",
        f"REGION={region}",
        f"CLOUD_ARMOR_POLICY={policy_name}",
        f"BACKEND_SERVICE={backend_name}",
        "",
    ]
    env_path = base_dir / ".env"
    env_path.write_text("\n".join(env_lines), encoding="utf-8")
    print(f"\n[완료] 환경 설정이 저장되었다: {env_path}")


def is_avx512_vbmi_machine(machine_type: str) -> bool:
    """머신 타입 문자열에서 AVX-512 VBMI 지원 시리즈 여부를 판별한다."""
    short_name = machine_type.rsplit("/", 1)[-1].lower()
    series = short_name.split("-", 1)[0]
    return series in AVX512_VBMI_SERIES


def inspect_cel_pitfalls(rules: List[Dict[str, Any]], body_size: str) -> List[Dict[str, str]]:
    """Cloud Armor Custom CEL 규칙의 4대 실환경 함정을 정적 감사한다."""
    findings: List[Dict[str, str]] = []
    has_header_rule = False
    has_raw_body_rule = False
    has_form_rule = False

    if body_size != "64KB":
        findings.append(
            {
                "category": "본문 검사 상한",
                "target": f"request-body-inspection-size ({body_size or '기본값 8KB'})",
                "status": "WARN",
                "detail": "본문 검사 상한이 64KB 미만이어서 8KB~64KB 구간 우회 위험이 있다.",
            }
        )
    else:
        findings.append(
            {
                "category": "본문 검사 상한",
                "target": "request-body-inspection-size (64KB)",
                "status": "PASS",
                "detail": "최대 본문 검사 상한(64KB)이 정상 적용되어 있다.",
            }
        )

    for rule in rules:
        priority = rule.get("priority", 0)
        if priority == 2147483647:
            continue
        expr = (rule.get("match", {}).get("expr", {}) or {}).get("expression", "")
        if not expr:
            continue

        preview = bool(rule.get("preview", False))
        mode_label = "Preview" if preview else "Enforce"

        if "base64Decode" in expr and re.search(r"base64Decode\s*\([^)]*\)\s*==\s*['\"]['\"]", expr):
            findings.append(
                {
                    "category": "CEL 우회 함정",
                    "target": f"Priority {priority} ({mode_label})",
                    "status": "FAIL",
                    "detail": "base64Decode() == '' 패턴은 앞 64B 부분 디코딩 시 우회되므로 contains('=') && matches(...)로 교체가 필요하다.",
                }
            )

        if "cookie" in expr.lower() and ".urlDecode()" in expr:
            findings.append(
                {
                    "category": "CEL 오탐 함정",
                    "target": f"Priority {priority} ({mode_label})",
                    "status": "FAIL",
                    "detail": "Cookie/표준 Base64에 .urlDecode() 사용 시 '+'가 공백으로 치환되어 오탐이 발생한다.",
                }
            )

        if "request.body" in expr and "application/x-www-form-urlencoded" not in expr:
            findings.append(
                {
                    "category": "Form 본문 미분리",
                    "target": f"Priority {priority} ({mode_label})",
                    "status": "WARN",
                    "detail": "Raw request.body 규칙에서 application/x-www-form-urlencoded 분리가 누락되어 %2B/%2F 오탐 위험이 있다.",
                }
            )

        for m in re.finditer(r"\.matches\s*\(\s*r?['\"]([^'\"]+)['\"]", expr):
            regex_body = m.group(1)
            if re.search(r"(?<!\\)\((?!\?[:i=!])", regex_body):
                findings.append(
                    {
                        "category": "RE2 문법 제약",
                        "target": f"Priority {priority} ({mode_label})",
                        "status": "FAIL",
                        "detail": "일반 캡처 그룹 (...) 사용 시 Cloud Armor에서 오류가 발생하므로 비캡처 그룹 (?:...)을 사용해야 한다.",
                    }
                )

        if "contains('=')" in expr or "[A-Za-z0-9+/_-]{64}" in expr or "[A-Za-z0-9+/_-]{4}" in expr:
            if "request.headers['authorization']" in expr or "request.headers['cookie']" in expr or "request.query" in expr:
                has_header_rule = True
            if "request.body" in expr and "!request.headers['content-type'].lower().startsWith('application/x-www-form-urlencoded')" in expr:
                has_raw_body_rule = True
            if "request.body.urlDecode()" in expr and "startsWith('application/x-www-form-urlencoded')" in expr:
                has_form_rule = True

    findings.append(
        {
            "category": "헤더/쿼리 방어 (GA)",
            "target": "Rule 1 (Authorization, Cookie, Query)",
            "status": "PASS" if has_header_rule else "FAIL",
            "detail": (
                "Authorization, Cookie, Query 대상 비정상 Base64 패딩 차단 규칙이 활성화되어 있다."
                if has_header_rule
                else "헤더 및 쿼리 대상 CVE-2026-114938 차단 규칙이 누락되었다."
            ),
        }
    )
    findings.append(
        {
            "category": "본문 방어 (Public Preview)",
            "target": "Rule 2a/2b (Raw/JSON/XML vs Form 분리)",
            "status": "PASS" if (has_raw_body_rule and has_form_rule) else "WARN",
            "detail": (
                "Raw 본문(Rule 2a)과 Form 본문(Rule 2b)이 Content-Type 기준으로 분리 적용되어 있다."
                if (has_raw_body_rule and has_form_rule)
                else "request.body 기반 Rule 2a/2b 분리 적용 여부를 확인하고 정책 선연결 후 추가해야 한다."
            ),
        }
    )
    return findings


def get_mock_diagnostics() -> Dict[str, Any]:
    """--dry-run 가상 실행용 모의 진단 데이터를 반환한다."""
    rules = [
        {
            "priority": 940,
            "preview": False,
            "match": {
                "expr": {
                    "expression": "has(request.headers['x-user-context']) && request.headers['x-user-context'].base64Decode() == ''"
                }
            },
        },
        {
            "priority": 1000,
            "preview": True,
            "match": {
                "expr": {
                    "expression": "(has(request.headers['authorization']) && request.headers['authorization'].matches('(?:^|[^A-Za-z0-9+/_-])(?:[A-Za-z0-9+/_-]{4}){8,}[A-Za-z0-9+/_=-]{0,2}=(?:$|[^A-Za-z0-9+/_=-])')) || (has(request.headers['cookie']) && request.headers['cookie'].urlDecode().matches('...')) || request.query.urlDecode().matches('...')"
                }
            },
        },
    ]
    return {
        "project_id": "sample-project-id",
        "region": "asia-northeast3",
        "workloads": [
            {
                "type": "GKE NodePool",
                "name": "app-cluster-prod / java-pool-1",
                "machine_type": "c3-standard-8",
                "exposed": True,
                "mitigated": False,
                "detail": "AVX-512 VBMI 지원 시리즈(C3), JDK_JAVA_OPTIONS 미확인",
            },
            {
                "type": "Compute Engine VM",
                "name": "legacy-api-vm-01",
                "machine_type": "n2-standard-4",
                "exposed": True,
                "mitigated": False,
                "detail": "AVX-512 VBMI 지원 시리즈(N2), JVM 플래그 점검 필요",
            },
            {
                "type": "Cloud Run (2nd Gen)",
                "name": "payment-gateway-svc",
                "machine_type": "managed-gen2",
                "exposed": False,
                "mitigated": True,
                "detail": "플랫폼 관리형 Java 런타임 AVX-512 마스킹 보호 대상 (커스텀 컨테이너 제외)",
            },
        ],
        "policies": [
            {
                "name": "prod-java-waf-policy",
                "attached_backends": ["prod-external-alb-bs"],
                "body_inspection_size": "8KB",
                "cel_findings": inspect_cel_pitfalls(rules, "8KB"),
            }
        ],
    }


def scan_live_diagnostics(
    project_id: str,
    region: str,
    target_policy: str,
    target_backend: str,
) -> Dict[str, Any]:
    """실제 GCP 프로젝트에서 워크로드 및 Cloud Armor 정책을 읽기 전용으로 진단한다."""
    workloads: List[Dict[str, Any]] = []

    print("[1/4] AVX-512 VBMI 지원 Compute Engine, GKE, Cloud Run 워크로드 점검 중...", flush=True)
    vms = run_gcloud_json(["gcloud", "compute", "instances", "list", f"--project={project_id}"])
    if isinstance(vms, list):
        for vm in vms:
            mtype = vm.get("machineType", "")
            exposed = is_avx512_vbmi_machine(mtype)
            items = vm.get("metadata", {}).get("items", [])
            meta_str = " ".join(str(i.get("value", "")) for i in items)
            mitigated = "-XX:UseAVX=2" in meta_str or "-XX:-UseBASE64Intrinsics" in meta_str
            workloads.append(
                {
                    "type": "Compute Engine VM",
                    "name": vm.get("name", "unknown"),
                    "machine_type": mtype.rsplit("/", 1)[-1],
                    "exposed": exposed,
                    "mitigated": mitigated,
                    "detail": (
                        "AVX-512 VBMI 지원 머신 시리즈 — JDK_JAVA_OPTIONS 또는 패치 확인 필요"
                        if exposed and not mitigated
                        else "AVX-512 VBMI 비해당 또는 완화 플래그 확인됨"
                    ),
                }
            )

    clusters = run_gcloud_json(["gcloud", "container", "clusters", "list", f"--project={project_id}"])
    if isinstance(clusters, list):
        for cl in clusters:
            cname = cl.get("name", "cluster")
            for np in cl.get("nodePools", []):
                mtype = np.get("config", {}).get("machineType", "")
                exposed = is_avx512_vbmi_machine(mtype)
                workloads.append(
                    {
                        "type": "GKE NodePool",
                        "name": f"{cname} / {np.get('name', 'pool')}",
                        "machine_type": mtype,
                        "exposed": exposed,
                        "mitigated": False,
                        "detail": (
                            "AVX-512 VBMI 지원 노드풀 — OpenJDK 17.0.6+ 파드 JDK_JAVA_OPTIONS 확인 필요"
                            if exposed
                            else "AVX-512 VBMI 비해당 머신 시리즈"
                        ),
                    }
                )

    run_svcs = run_gcloud_json(
        ["gcloud", "run", "services", "list", f"--project={project_id}", "--platform=managed"]
    )
    if isinstance(run_svcs, list):
        for svc in run_svcs:
            sname = svc.get("metadata", {}).get("name", "service")
            spec_str = json.dumps(svc.get("spec", {}), ensure_ascii=False)
            mitigated = "-XX:UseAVX=2" in spec_str or "-XX:-UseBASE64Intrinsics" in spec_str
            workloads.append(
                {
                    "type": "Cloud Run",
                    "name": sname,
                    "machine_type": "managed",
                    "exposed": not mitigated,
                    "mitigated": mitigated,
                    "detail": (
                        "완화 JVM 플래그 설정됨"
                        if mitigated
                        else "1세대 또는 커스텀 컨테이너인 경우 JDK_JAVA_OPTIONS 적용 권장"
                    ),
                }
            )

    print("[2/4] External ALB Backend Service 및 Cloud Armor Security Policy 연결 조회 중...", flush=True)
    backends = run_gcloud_json(["gcloud", "compute", "backend-services", "list", f"--project={project_id}"]) or []
    policy_to_backends: Dict[str, List[str]] = {}
    for bs in backends:
        bs_name = bs.get("name", "")
        if target_backend and bs_name != target_backend:
            continue
        sp_url = bs.get("securityPolicy", "")
        if sp_url:
            sp_name = sp_url.rsplit("/", 1)[-1]
            policy_to_backends.setdefault(sp_name, []).append(bs_name)

    policies_raw = run_gcloud_json(["gcloud", "compute", "security-policies", "list", f"--project={project_id}"]) or []
    policy_reports: List[Dict[str, Any]] = []

    print("[3/4] Cloud Armor Custom CEL 4대 실환경 함정 정적 감사 중...", flush=True)
    for pol in policies_raw:
        pname = pol.get("name", "")
        if target_policy and pname != target_policy:
            continue
        body_size = (pol.get("advancedOptionsConfig", {}) or {}).get("requestBodyInspectionSize", "8KB")
        rules = pol.get("rules", [])
        policy_reports.append(
            {
                "name": pname,
                "attached_backends": policy_to_backends.get(pname, []),
                "body_inspection_size": body_size,
                "cel_findings": inspect_cel_pitfalls(rules, body_size),
            }
        )

    return {
        "project_id": project_id,
        "region": region,
        "workloads": workloads,
        "policies": policy_reports,
    }


def generate_markdown_report(data: Dict[str, Any], is_dry_run: bool) -> str:
    """진단 결과와 표준 조치 가이드를 Markdown 리포트로 생성한다."""
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    mode_tag = "DRY-RUN (모의 시뮬레이션)" if is_dry_run else "LIVE (실환경 읽기 전용 진단)"
    project_id = data["project_id"]

    lines: List[str] = [
        "<!--",
        "Copyright 2026 Google LLC. All Rights Reserved.",
        "SPDX-License-Identifier: Apache-2.0",
        "",
        "NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.",
        "It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.",
        "-->",
        "",
        "> [!IMPORTANT]",
        "> **구글 (Google LLC) 참조용 샘플 고지 사항**:",
        "> 본 리포트는 Google LLC 참조용 샘플 진단기의 출력 결과이며, 프로덕션 환경 적용 전 반드시 Preview 모드 및 워크로드 테스트를 거쳐야 한다.",
        "",
        f"# Cloud Armor 기반 Java4Shell (CVE-2026-114938) 노출 및 WAF 진단 리포트",
        "",
        f"- **점검 일시**: {now_str}",
        f"- **점검 모드**: `{mode_tag}`",
        f"- **대상 프로젝트**: `{project_id}`",
        "",
        "---",
        "",
        "## 1. AVX-512 VBMI 워크로드 노출 현황 (GCP-2026-082)",
        "",
        "| 리소스 유형 | 워크로드 이름 | 머신 타입 | 노출 위험 | 상세 진단 내용 |",
        "| :--- | :--- | :--- | :---: | :--- |",
    ]

    if not data["workloads"]:
        lines.append("| - | 조회된 컴퓨트 워크로드 없음 | - | `PASS` | 해당 프로젝트에 Compute Engine/GKE/Cloud Run 워크로드가 없거나 조회 권한이 없다. |")
    else:
        for w in data["workloads"]:
            badge = "`WARN`" if w["exposed"] and not w["mitigated"] else "`PASS`"
            lines.append(
                f"| {w['type']} | `{w['name']}` | `{w['machine_type']}` | {badge} | {w['detail']} |"
            )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 2. Cloud Armor Security Policy 및 CEL 함정 감사 결과",
            "",
        ]
    )

    if not data["policies"]:
        lines.append("- **경고 (`FAIL`)**: 프로젝트 내 Cloud Armor Security Policy가 존재하지 않는다. 아래 권장 Virtual Patching 구성 절차를 참고하여 정책을 선연결 후 규칙을 배포한다.")
    else:
        for pol in data["policies"]:
            attached = ", ".join(f"`{b}`" for b in pol["attached_backends"]) or "미연결 (Backend Service 선연결 필수)"
            lines.append(f"### 정책: `{pol['name']}` (연결된 Backend Service: {attached})")
            lines.append("")
            lines.append("| 점검 항목 | 대상 | 상태 | 진단 상세 |")
            lines.append("| :--- | :--- | :---: | :--- |")
            for f in pol["cel_findings"]:
                lines.append(f"| {f['category']} | `{f['target']}` | `{f['status']}` | {f['detail']} |")
            lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## 3. 단계별 권장 조치 및 가상 패치 CLI 처방",
            "",
            "### 3.1 Cloud Armor 배포 순서 및 Custom CEL Virtual Patching",
            "`request.body` / `request.params` (Public Preview) 규칙을 추가하기 전에 **반드시 Security Policy를 Backend Service에 먼저 연결**해야 `undeclared reference to 'request'` 오류를 피할 수 있다.",
            "",
            "```bash",
            "# 1) 신규 테스트 정책 생성 및 64KB 본문 검사 상한 설정 (4대 표준 라벨 적용 권장)",
            f"gcloud compute security-policies create java4shell-waf-policy --project={project_id}",
            f"gcloud beta compute security-policies update java4shell-waf-policy --project={project_id} --request-body-inspection-size=64KB",
            "",
            "# 2) Backend Service에 정책 선연결 (request.body 규칙 추가 전 필수)",
            f"gcloud compute backend-services update <BACKEND_SERVICE_NAME> --project={project_id} --security-policy=java4shell-waf-policy --global",
            "",
            "# 3) Rule 1 (GA): Authorization, Cookie, Query 일괄 검사 (--preview 선배포)",
            f"gcloud compute security-policies rules create 1000 --project={project_id} \\",
            "  --security-policy=java4shell-waf-policy \\",
            "  --description=\"Mitigate CVE-2026-114938 malformed Base64 in Auth, Cookie, Query\" \\",
            "  --expression=\"(has(request.headers['authorization']) && request.headers['authorization'].matches('(?:^|[^A-Za-z0-9+/_-])(?:[A-Za-z0-9+/_-]{4}){8,}[A-Za-z0-9+/_=-]{0,2}=(?:$|[^A-Za-z0-9+/_=-])')) || (has(request.headers['cookie']) && request.headers['cookie'].matches('(?:^|[^A-Za-z0-9+/_-])(?:[A-Za-z0-9+/_-]{64})+[A-Za-z0-9+/_=-]{0,2}(?:=|%3[Dd])(?:$|[^A-Za-z0-9+/_=-])')) || request.query.urlDecode().matches('(?:^|[^A-Za-z0-9+/_-])(?:[A-Za-z0-9+/_-]{64})+[A-Za-z0-9+/_=-]{0,2}=(?:$|[^A-Za-z0-9+/_=-])')\" \\",
            "  --action=deny-403 --preview",
            "",
            "# 4) Rule 2a (Public Preview): Raw/JSON/XML 본문 검사 (Form 제외)",
            f"gcloud compute security-policies rules create 1010 --project={project_id} \\",
            "  --security-policy=java4shell-waf-policy \\",
            "  --description=\"Mitigate CVE-2026-114938 malformed Base64 in raw/JSON/XML body\" \\",
            "  --expression=\"(!has(request.headers['content-type']) || !request.headers['content-type'].lower().startsWith('application/x-www-form-urlencoded')) && size(request.body) > 64 && request.body.matches('(?:^|[^A-Za-z0-9+/_-])(?:[A-Za-z0-9+/_-]{64})+[A-Za-z0-9+/_=-]{0,2}(?:=|%3[Dd])(?:$|[^A-Za-z0-9+/_=-])')\" \\",
            "  --action=deny-403 --preview",
            "",
            "# 5) Rule 2b (Public Preview): Form POST 본문 검사",
            f"gcloud compute security-policies rules create 1015 --project={project_id} \\",
            "  --security-policy=java4shell-waf-policy \\",
            "  --description=\"Mitigate CVE-2026-114938 malformed Base64 in form-urlencoded body\" \\",
            "  --expression=\"has(request.headers['content-type']) && request.headers['content-type'].lower().startsWith('application/x-www-form-urlencoded') && size(request.body) > 64 && request.body.urlDecode().matches('(?:^|[^A-Za-z0-9+/_-])(?:[A-Za-z0-9+/_-]{64})+[A-Za-z0-9+/_=-]{0,2}=(?:$|[^A-Za-z0-9+/_=-])')\" \\",
            "  --action=deny-403 --preview",
            "",
            f"# 6) 테스트용 리소스 생성 시 4대 표준 라벨 적용 예시: --labels={STANDARD_LABELS}",
            "```",
            "",
            "### 3.2 워크로드 근본 조치 (GCP-2026-082)",
            "Cloud Armor WAF는 압축 본문, 이중 인코딩, 64KB 초과 영역에 한계가 있으므로 백엔드에 아래 JVM 플래그를 병행 적용한 뒤 패치된 OpenJDK로 업그레이드한다.",
            "",
            "```bash",
            "JDK_JAVA_OPTIONS=\"-XX:+IgnoreUnrecognizedVMOptions -XX:UseAVX=2\"",
            "```",
            "",
            "---",
            "",
            "## 4. 참고 콘솔 및 공식 문서",
            "- Cloud Armor Security Policies 콘솔 ( https://console.cloud.google.com/net-security/securitypolicies/list )",
            "- Google Cloud Security Bulletins GCP-2026-082 ( https://docs.cloud.google.com/support/bulletins#gcp-2026-082 )",
            "- Google Cloud Armor Custom Rules Language Reference ( https://cloud.google.com/armor/docs/create-security-policy-rules )",
            "",
        ]
    )
    return "\n".join(lines)


def save_markdown_report(base_dir: pathlib.Path, content: str) -> pathlib.Path:
    """표준 리포트 파일(report.md)을 생성 및 덮어쓴다."""
    report_path = base_dir / "report.md"
    report_path.write_text(content, encoding="utf-8")
    return report_path


def print_terminal_summary(data: Dict[str, Any], report_path: pathlib.Path) -> None:
    """터미널에 요약 진단 결과를 출력한다."""
    print("=" * 72)
    print("Cloud Armor Java4Shell (CVE-2026-114938) 노출 및 WAF 진단 결과")
    print("=" * 72)
    print(f"- 대상 프로젝트: {data['project_id']}")
    print(f"- 점검 워크로드 수: {len(data['workloads'])}개")
    exposed_cnt = sum(1 for w in data["workloads"] if w["exposed"] and not w["mitigated"])
    print(f"- AVX-512 VBMI 미완화 추정 워크로드: {exposed_cnt}개")
    print(f"- 점검 Cloud Armor 정책 수: {len(data['policies'])}개")
    for pol in data["policies"]:
        fails = sum(1 for f in pol["cel_findings"] if f["status"] == "FAIL")
        warns = sum(1 for f in pol["cel_findings"] if f["status"] == "WARN")
        print(f"  * 정책 [{pol['name']}] -> FAIL {fails}건, WARN {warns}건 (본문 검사: {pol['body_inspection_size']})")
    print("-" * 72)
    print(f"[완료] 상세 진단 및 처방 리포트가 저장되었다: {report_path}")


def main() -> None:
    """메인 실행 진입점."""
    base_dir = pathlib.Path(__file__).resolve().parent
    load_dotenv_file(base_dir / ".env")
    args = parse_args()

    if args.config:
        run_config_mode(base_dir)
        return

    project_id = resolve_project_id(args.project, args.dry_run)
    if not project_id:
        print("[오류] Google Cloud 프로젝트 ID를 확인할 수 없다. --project 또는 --config를 사용한다.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("[모의 실행] 가상 인프라 및 Cloud Armor 정책 데이터로 진단을 시뮬레이션한다...", flush=True)
        data = get_mock_diagnostics()
    else:
        data = scan_live_diagnostics(
            project_id=project_id,
            region=args.region,
            target_policy=args.policy,
            target_backend=args.backend_service,
        )

    print("[4/4] 진단 리포트(report.md) 생성 및 요약 출력 중...", flush=True)
    report_md = generate_markdown_report(data, args.dry_run)
    report_path = save_markdown_report(base_dir, report_md)
    print_terminal_summary(data, report_path)


if __name__ == "__main__":
    main()
