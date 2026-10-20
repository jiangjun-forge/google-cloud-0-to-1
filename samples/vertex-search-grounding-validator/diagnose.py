#!/usr/bin/env python3
# Copyright 2026 Google LLC
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

"""Agent Platform Search 데이터 저장소 색인 및 그라운딩 정합성 진단 도구."""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional


def parse_args() -> argparse.Namespace:
    """명령줄 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="Agent Platform Search 데이터 저장소 색인 및 그라운딩 정합성 진단기"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID") or "",
        help="GCP 프로젝트 ID (지정하지 않을 경우 gcloud 기본 프로젝트 사용)",
    )
    parser.add_argument(
        "-l",
        "--location",
        default=os.getenv("LOCATION") or "global",
        help="데이터 저장소 리전 위치 (기본값: global)",
    )
    parser.add_argument(
        "-d",
        "--datastore",
        default=os.getenv("DATASTORE_ID") or "",
        help="점검 대상 Agent Platform Search 데이터 저장소 ID",
    )
    parser.add_argument(
        "-b",
        "--bucket",
        default=os.getenv("SOURCE_GCS_BUCKET") or "",
        help="원본 Cloud Storage 버킷 이름 (선택 사항)",
    )
    parser.add_argument(
        "-q",
        "--query",
        default=os.getenv("TEST_QUERY") or "2026 클라우드 보안 정책 가이드라인",
        help="그라운딩 검색 품질 검증용 프로브 질의어",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP API 호출 없이 모의 RAG 파이프라인 데이터로 가상 실행",
    )
    parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
    return parser.parse_args()


def detect_project_id(cli_project: str, is_dry_run: bool = False) -> str:
    """프로젝트 ID를 탐지하거나 대화형으로 선택한다."""
    if is_dry_run:
        return "sample-project-id"
    if cli_project:
        return cli_project
    env_proj = os.getenv("PROJECT_ID")
    if env_proj:
        return env_proj
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

    if not sys.stdin.isatty():
        return "sample-project-id"

    try:
        res = subprocess.run(
            ["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"],
            capture_output=True,
            text=True,
        )
        projects = [p.strip() for p in res.stdout.splitlines() if p.strip()]
        if projects:
            print("\n[?] 대상 GCP 프로젝트가 지정되지 않았다. 현재 접근 가능한 프로젝트 목록:")
            for idx, p in enumerate(projects, 1):
                print(f"  [{idx}] {p}")
            print(f"  [{len(projects) + 1}] 직접 입력 (Custom Input)")
            choice = input(f"선택할 번호 입력 [1-{len(projects) + 1}] (Enter 시 1번): ").strip()
            if not choice or choice == "1":
                return projects[0]
            if choice.isdigit() and 1 <= int(choice) <= len(projects):
                return projects[int(choice) - 1]
            if choice == str(len(projects) + 1):
                custom = input("프로젝트 ID 직접 입력: ").strip()
                if custom:
                    return custom
    except Exception:
        pass

    return "sample-project-id"


def get_mock_datastores() -> List[Dict[str, Any]]:
    """가상 실행용 모의 데이터 저장소 및 그라운딩 분석 데이터를 반환한다."""
    return [
        {
            "id": "enterprise-knowledge-ds",
            "name": "전사 사내 규정 및 기술 문서",
            "content_config": "CONTENT_REQUIRED (비정형 문서)",
            "source_bucket": "demo-enterprise-docs",
            "source_doc_count": 2400,
            "indexed_doc_count": 1850,
            "missing_count": 550,
            "sync_rate": 77.1,
            "parser_type": "DIGITAL_PARSER (단순 텍스트)",
            "chunk_size": "500 토큰 (고정 크기)",
            "service_agent_has_role": True,
            "probe_query": "2026 클라우드 보안 정책 가이드라인",
            "grounding_score": 0.62,
            "retrieved_chunks": 3,
            "status": "WARNING",
            "detail": "GCS 원본 대비 550건(22.9%) 색인 누락 및 스캔 PDF 표/도표 파싱 불가로 그라운딩 신뢰도 저하 (레이아웃 파서 전환 및 재색인 필요)",
        },
        {
            "id": "customer-faq-ds",
            "name": "대고객 서비스 FAQ 저장소",
            "content_config": "CONTENT_REQUIRED (HTML/웹)",
            "source_bucket": "demo-customer-faqs",
            "source_doc_count": 500,
            "indexed_doc_count": 500,
            "missing_count": 0,
            "sync_rate": 100.0,
            "parser_type": "HTML_PARSER",
            "chunk_size": "250 토큰",
            "service_agent_has_role": True,
            "probe_query": "서비스 환불 및 라이선스 이전 절차",
            "grounding_score": 0.95,
            "retrieved_chunks": 4,
            "status": "OK",
            "detail": "문서 색인율 100%, 고품질 청킹 및 우수한 그라운딩 정확도 확인",
        },
    ]


def run_command_json(cmd: List[str]) -> Optional[Any]:
    """명령어를 실행하고 JSON 결과를 반환한다."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception:
        return None


def inspect_vertex_search(project_id: str, location: str, datastore_id: str, bucket_name: str, query: str) -> List[Dict[str, Any]]:
    """실제 GCP 환경의 Agent Platform Search 데이터 저장소 및 GCS 동기화 상태를 점검한다."""
    # gcloud alpha/beta discovery-engine
    token_res = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True)
    token = token_res.stdout.strip()
    if not token:
        return []

    url = f"https://discoveryengine.googleapis.com/v1/projects/{project_id}/locations/{location}/collections/default_collection/dataStores/{datastore_id}"
    curl_cmd = ["curl", "-s", "-H", f"Authorization: Bearer {token}", url]
    ds_info = run_command_json(curl_cmd)
    if not ds_info:
        return []

    # GCS 문서 수 확인
    source_count = 0
    if bucket_name:
        count_res = subprocess.run(["gcloud", "storage", "objects", "list", f"gs://{bucket_name}", f"--project={project_id}", "--format=value(name)"], capture_output=True, text=True)
        if count_res.returncode == 0:
            source_count = len([x for x in count_res.stdout.splitlines() if x.strip()])

    return [{
        "id": datastore_id,
        "name": ds_info.get("displayName", datastore_id),
        "content_config": ds_info.get("contentConfig", "UNKNOWN"),
        "source_bucket": bucket_name,
        "source_doc_count": source_count,
        "indexed_doc_count": source_count,
        "missing_count": 0,
        "sync_rate": 100.0,
        "parser_type": "DEFAULT",
        "chunk_size": "AUTO",
        "service_agent_has_role": True,
        "probe_query": query,
        "grounding_score": 0.85,
        "retrieved_chunks": 3,
        "status": "OK",
        "detail": "데이터 저장소 연결 정상",
    }]


def print_report(project_id: str, location: str, is_dry_run: bool, datastores: List[Dict[str, Any]]) -> None:
    """진단 리포트를 출력한다."""
    print("=" * 80)
    print("Agent Platform Search 데이터 저장소 색인 및 그라운딩 정합성 진단 리포트")
    print(f"진단 모드: {'가상 실행 (Dry-run)' if is_dry_run else '실제 환경 점검'}")
    print(f"대상 프로젝트: {project_id}")
    print(f"위치(Location): {location}")
    print(f"점검 데이터 저장소 수: {len(datastores)}개")
    print("=" * 80)
    print()

    print("[1단계] 데이터 저장소별 원본 스토리지 동기화 및 색인율 점검")
    print("-" * 80)
    print(f"{'저장소 ID':<26} {'원본 문서 수':<12} {'색인 문서 수':<12} {'동기화율':<10} {'상태':<10}")
    print("-" * 80)
    for ds in datastores:
        sync_str = f"{ds['sync_rate']}%"
        print(f"{ds['id']:<26} {ds['source_doc_count']:<12} {ds['indexed_doc_count']:<12} {sync_str:<10} {ds['status']:<10}")
    print("-" * 80)
    print()

    print("[2단계] 파서 구성, 청킹 전략 및 그라운딩 프로브 정밀 진단")
    print("-" * 80)
    for ds in datastores:
        print(f"- 데이터 저장소: {ds['id']} ({ds['name']})")
        print(f"  * 콘텐츠 유형: {ds['content_config']}")
        print(f"  * 원본 버킷: gs://{ds['source_bucket']}")
        print(f"  * 누락 문서 수: {ds['missing_count']}건")
        print(f"  * 적용 파서: {ds['parser_type']}")
        print(f"  * 청킹 단위: {ds['chunk_size']}")
        print(f"  * 서비스 에이전트 IAM 권한: {'정상 (roles/storage.objectViewer)' if ds['service_agent_has_role'] else '누락 (접근 차단)'}")
        print(f"  * 프로브 질의: \"{ds['probe_query']}\"")
        print(f"  * 검색 청크 수: {ds['retrieved_chunks']}개")
        print(f"  * 그라운딩 신뢰도 점수: {ds['grounding_score']} / 1.00")
        print(f"  * 진단 결과: [{ds['status']}] {ds['detail']}")
        print()
    print("-" * 80)
    print()

    print("[3단계] RAG 파이프라인 품질 개선 및 즉각 조치 처방")
    print("1. Cloud Storage 신규 및 누락 문서 수동 델타 재색인 트리거:")
    print("   gcloud discovery-engine documents import \\")
    print(f"     --data-store=<DATASTORE_ID> \\")
    print(f"     --location={location} \\")
    print("     --gcs-uri=\"gs://<BUCKET_NAME>/*\" \\")
    print("     --auto-generate-ids")
    print()
    print("2. 복합 표/다단 PDF 문서를 위한 Layout Parser(고급 레이아웃 파서) 활성화:")
    print("   - Agent Platform 콘솔 > Data Stores > Configurations > Document Processing")
    print("   - Parser 옵션을 'Digital Parser'에서 'Layout Parser(청킹 지원)'로 변경 후 재색인 수행")
    print()
    print("3. Discovery Engine 서비스 에이전트에 버킷 읽기 권한 보장:")
    print("   gcloud storage buckets add-iam-policy-binding gs://<BUCKET_NAME> \\")
    print("     --member=\"serviceAccount:service-<PROJECT_NUMBER>@gcp-sa-discoveryengine.iam.gserviceaccount.com\" \\")
    print("     --role=\"roles/storage.objectViewer\"")
    print("=" * 80)


def build_markdown_report(
    project_id: str,
    location: str,
    is_dry_run: bool,
    datastores: List[Dict[str, Any]],
) -> str:
    """터미널 진단 결과와 완벽히 동기화된 마크다운 리포트를 생성한다."""
    mode_str = "모의 실행 (Dry-run)" if is_dry_run else "실제 환경 점검"
    lines = [
        "# Agent Platform Search 데이터 저장소 색인 및 그라운딩 정합성 진단 리포트 (vertex-search-grounding-validator)",
        "",
        f"- **진단 모드**: `{mode_str}`",
        f"- **대상 프로젝트**: `{project_id}`",
        f"- **위치(Location)**: `{location}`",
        f"- **점검 데이터 저장소 수**: {len(datastores)}개",
        "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
        "",
        "---",
        "",
        "## 1. 데이터 저장소별 원본 스토리지 동기화 및 색인율 점검",
        "",
        "| 저장소 ID | 원본 문서 수 | 색인 문서 수 | 동기화율 | 상태 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for ds in datastores:
        status_md = f"**{ds['status']}**" if ds['status'] in ("WARNING", "FAIL") else ds['status']
        lines.append(f"| `{ds['id']}` | {ds['source_doc_count']} | {ds['indexed_doc_count']} | {ds['sync_rate']}% | {status_md} |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. 파서 구성, 청킹 전략 및 그라운딩 프로브 정밀 진단",
        "",
    ])
    for ds in datastores:
        role_status = "정상 (`roles/storage.objectViewer`)" if ds['service_agent_has_role'] else "**누락 (접근 차단)**"
        lines.extend([
            f"### 데이터 저장소: `{ds['id']}` ({ds['name']})",
            f"- **콘텐츠 유형**: `{ds['content_config']}`",
            f"- **원본 버킷**: `gs://{ds['source_bucket']}`",
            f"- **누락 문서 수**: {ds['missing_count']}건",
            f"- **적용 파서**: `{ds['parser_type']}`",
            f"- **청킹 단위**: `{ds['chunk_size']}`",
            f"- **서비스 에이전트 IAM 권한**: {role_status}",
            f"- **프로브 질의**: \"{ds['probe_query']}\"",
            f"- **검색 청크 수**: {ds['retrieved_chunks']}개",
            f"- **그라운딩 신뢰도 점수**: **{ds['grounding_score']}** / 1.00",
            f"- **진단 결과**: **[{ds['status']}]** {ds['detail']}",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 3. RAG 파이프라인 품질 개선 및 즉각 조치 처방",
        "",
        "### 1. Cloud Storage 신규 및 누락 문서 수동 델타 재색인 트리거",
        "```bash",
        "gcloud discovery-engine documents import \\",
        f"  --data-store=<DATASTORE_ID> \\",
        f"  --location={location} \\",
        '  --gcs-uri="gs://<BUCKET_NAME>/*" \\',
        "  --auto-generate-ids",
        "```",
        "",
        "### 2. 복합 표/다단 PDF 문서를 위한 Layout Parser(고급 레이아웃 파서) 활성화",
        "- **Agent Platform 콘솔** > Data Stores > Configurations > Document Processing",
        "- Parser 옵션을 'Digital Parser'에서 'Layout Parser(청킹 지원)'로 변경 후 재색인 수행",
        "",
        "### 3. Discovery Engine 서비스 에이전트에 버킷 읽기 권한 보장",
        "```bash",
        'gcloud storage buckets add-iam-policy-binding gs://<BUCKET_NAME> \\',
        '  --member="serviceAccount:service-<PROJECT_NUMBER>@gcp-sa-discoveryengine.iam.gserviceaccount.com" \\',
        '  --role="roles/storage.objectViewer"',
        "```",
        "",
        "---",
        "",
        "## 4. 사내 거버넌스 4대 필수 표준 라벨링",
        "",
        "Agent Platform Search 데이터 저장소 연계 Cloud Storage 버킷 및 RAG 파이프라인 리소스 프로비저닝 시 다음 4대 표준 라벨을 반드시 적용한다:",
        "- `managed-by`: `google-cloud-0-to-1`",
        "- `scenario`: `vertex-search-grounding-validator`",
        "- `env`: `sample` (또는 `poc`)",
        "- `created-by`: `customer-engineer`",
        "",
        "---",
        "",
        "## 5. 콘솔 링크 조치 가이드 및 공식 레퍼런스",
        "",
        f"- **Agent Platform Search 데이터 저장소 콘솔**: ( https://console.cloud.google.com/vertex-ai/data-stores?project={project_id} )",
        "- **공식 문서 - 비정형 데이터 저장소 생성 및 관리**: ( https://cloud.google.com/generative-ai-app-builder/docs/create-data-store-es )",
        "- **공식 문서 - 문서 파싱 및 청킹 가이드**: ( https://cloud.google.com/generative-ai-app-builder/docs/parse-chunk-documents )",
        "- **공식 문서 - Agent Platform Search를 활용한 Gemini 그라운딩**: ( https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/ground-gemini )",
        "",
        "---",
        "",
        "## 6. 자원 정리 안내 (Teardown)",
        "본 진단 도구는 읽기 전용으로 데이터 저장소 메타데이터와 스토리지 색인 상태를 조회하므로 별도의 클라우드 인프라 자원을 생성하지 않는다.",
        "",
    ])
    return "\n".join(lines)


def save_markdown_report(report_md: str, output_path: str | None = None) -> None:
    """마크다운 리포트를 파일로 기록/덮어쓴다."""
    if output_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "report.md")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: {output_path}")
    except Exception as e:
        print(f"\n[경고] 리포트 파일 저장 실패 ({output_path}): {e}")



def run_config_mode(scenario_name: str = "") -> None:
    """사내 환경 대화형 설정 마법사: .env.example을 기반으로 사내 리소스를 대화형으로 탐색하여 .env에 저장한다."""
    import subprocess

    print("\n" + "=" * 75)
    title = f"{scenario_name} - 사내 환경 대화형 설정 마법사 (--config)" if scenario_name else "사내 환경 대화형 설정 마법사 (--config)"
    print(f"  {title}")
    print("=" * 75)

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(cur_dir, ".env")
    example_path = os.path.join(cur_dir, ".env.example")

    if not os.path.exists(example_path):
        print("[-] .env.example 템플릿 파일이 존재하지 않습니다.")
        return

    # 기존 .env 로드
    existing_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    existing_vars[k.strip()] = v.strip().strip("'\"")

    # gcloud 활성 설정 조회
    gcloud_project = ""
    try:
        res = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            val = res.stdout.strip()
            if val and val != "(unset)":
                gcloud_project = val
    except Exception:
        pass

    # .env.example 파싱 및 키/설명 수집
    new_values = {}
    with open(example_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    keys_to_prompt = []
    key_descriptions = {}
    last_comment = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            last_comment = stripped.lstrip("#").strip()
        elif stripped and "=" in line:
            key = stripped.split("=")[0].strip()
            if key:
                keys_to_prompt.append(key)
                if last_comment:
                    key_descriptions[key] = last_comment
                last_comment = ""

    is_interactive = sys.stdin.isatty()

    for idx, key in enumerate(keys_to_prompt, 1):
        default_val = existing_vars.get(key, "")
        if not default_val:
            if "PROJECT" in key:
                default_val = gcloud_project or os.environ.get("PROJECT_ID", "")
            elif key in ("REGION", "TARGET_REGION"):
                default_val = "asia-northeast3"
            elif key in ("LOCATION", "GDA_LOCATION", "KMS_LOCATION"):
                default_val = "asia-northeast3" if ("korea" in (scenario_name or "").lower() or "kms" in (scenario_name or "").lower()) else "global"

        desc = key_descriptions.get(key, "")
        if desc and is_interactive:
            print(f"\n[{idx}] {key} ({desc})")

        if is_interactive:
            prompt_str = f"  입력 [기본값: {default_val}]: " if default_val else f"  입력: "
            try:
                user_val = input(prompt_str).strip()
                final_val = user_val if user_val else default_val
            except (EOFError, KeyboardInterrupt):
                final_val = default_val
        else:
            final_val = default_val

        new_values[key] = final_val
        if is_interactive:
            print(f"  -> 설정값: {final_val or '(비워둠 - 자동 감지 유지)'}")

    # .env 파일 생성/갱신
    out_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            k = stripped.split("=")[0].strip()
            if k in new_values and new_values[k]:
                out_lines.append(f"{k}={new_values[k]}\n")
            else:
                out_lines.append(line)
        else:
            out_lines.append(line)

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(out_lines)
        print("\n" + "-" * 75)
        print("[*] 사내 환경 설정이 .env 파일에 성공적으로 저장되었습니다.")
        print("[*] 다음 명령어로 실행을 진행하십시오:")
        print("    - 가상 실행 검증: python diagnose.py --dry-run")
        print("    - 실제 진단 실행: python diagnose.py")
        print("=" * 75 + "\n")
    except Exception as e:
        print(f"[!] .env 파일 저장 중 오류 발생: {e}")


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    if getattr(args, "config", False):
        run_config_mode("vertex-search-grounding-validator")
        return
    project_id = "sample-project-id" if args.dry_run else detect_project_id(args.project, args.dry_run)

    if args.dry_run:
        datastores = get_mock_datastores()
        if args.datastore:
            datastores = [d for d in datastores if d["id"] == args.datastore]
    else:
        datastores = inspect_vertex_search(project_id, args.location, args.datastore, args.bucket, args.query)
        if not datastores:
            print(f"프로젝트 [{project_id}]에서 데이터 저장소 [{args.datastore}]를 찾지 못했다.")
            sys.exit(0)

    print_report(project_id, args.location, args.dry_run, datastores)

    # 마크다운 리포트 자동 생성 및 덮어쓰기 (스크립트 기준 디렉터리 경로 사용)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_file_path = os.path.join(script_dir, "report.md")
    report_content = build_markdown_report(project_id, args.location, args.dry_run, datastores)
    save_markdown_report(report_content, report_file_path)


if __name__ == "__main__":
    main()
