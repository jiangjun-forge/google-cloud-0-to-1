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

"""Google Cloud 아키텍처 명세(*.md 전수 스캔) 실전 루브릭 평가기."""

import argparse
import collections
import datetime
import os
import pathlib
import re
import subprocess
import sys
from typing import Any, Dict, List, Tuple

SCENARIO_SLUG = "gcp-architecture-evaluator"
STANDARD_LABELS = (
    f"managed-by=google-cloud-0-to-1,scenario={SCENARIO_SLUG},"
    "env=sample,created-by=customer-engineer"
)
IGNORED_MD_NAMES = {"report.md"}
IGNORED_DIR_NAMES = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}


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
        description="Google Cloud 아키텍처 명세(*.md 전수 스캔) 실전 루브릭 평가기"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID", ""),
        help="참고용 Google Cloud 프로젝트 ID (미입력 시 gcloud 활성 프로젝트 사용)",
    )
    parser.add_argument(
        "--path",
        default=os.getenv("SPEC_PATH", ""),
        help="평가할 마크다운 파일 또는 디렉터리 경로 (디렉터리 지정 시 하위 *.md 전수 스캔, 쉼표 복수 가능)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="내장 모의 아키텍처 명세(결함 포함 표본)로 루브릭 채점 시뮬레이션 실행",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        default=False,
        help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장",
    )
    return parser.parse_args()


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


def resolve_project_id(cli_project: str, dry_run: bool) -> str:
    """계층형 폴백으로 프로젝트 ID를 확정한다."""
    if dry_run:
        return "sample-project-id"
    return cli_project or get_gcloud_config_value("project") or "sample-project-id"


def parse_path_list(raw_value: str) -> List[pathlib.Path]:
    """쉼표로 구분된 단일 또는 복수 파일/디렉터리 경로를 파싱한다."""
    return [pathlib.Path(p.strip()) for p in raw_value.split(",") if p.strip()]


def collect_markdown_files(paths: List[pathlib.Path]) -> List[pathlib.Path]:
    """지정된 파일 및 디렉터리 하위 모든 마크다운(*.md) 파일을 파일명 제약 없이 전수 수집한다."""
    found: List[pathlib.Path] = []
    seen = set()

    def _add(fp: pathlib.Path) -> None:
        resolved = fp.resolve()
        if resolved not in seen:
            seen.add(resolved)
            found.append(fp)

    for p in paths:
        if not p.exists():
            continue
        if p.is_file():
            _add(p)
        elif p.is_dir():
            for md in sorted(p.rglob("*.md")):
                if any(part in IGNORED_DIR_NAMES or part.startswith(".") for part in md.relative_to(p).parts[:-1]):
                    continue
                if md.name.lower() in IGNORED_MD_NAMES:
                    continue
                _add(md)
    return found


def auto_detect_docs(cwd: pathlib.Path, base_dir: pathlib.Path) -> List[pathlib.Path]:
    """미지정 시 현재 디렉터리의 docs/ 또는 현재 디렉터리 하위 모든 *.md를 전수 수집한다."""
    docs_dir = cwd / "docs"
    if docs_dir.is_dir():
        found = collect_markdown_files([docs_dir])
        if found:
            return found
    found = collect_markdown_files([cwd])
    if found:
        return found
    return collect_markdown_files([base_dir / "docs"])


def run_config_mode(base_dir: pathlib.Path) -> None:
    """대화형 설정 마법사로 .env 파일을 생성한다."""
    print("=" * 72)
    print(f"[{SCENARIO_SLUG}] 대화형 환경 설정 마법사")
    print("=" * 72)
    default_proj = get_gcloud_config_value("project")
    proj_in = input(f"1. PROJECT_ID [{default_proj or '선택 사항'}]: ").strip() or default_proj

    default_dir = pathlib.Path.cwd() / "docs"
    spec_default = str(default_dir) if default_dir.is_dir() else ""
    spec_path = input(f"2. SPEC_PATH (평가할 파일 또는 디렉터리, 하위 *.md 전수 스캔) [{spec_default or '자동 탐색'}]: ").strip() or spec_default

    env_lines = [
        f"PROJECT_ID={proj_in}",
        f"SPEC_PATH={spec_path}",
        "",
    ]
    env_path = base_dir / ".env"
    env_path.write_text("\n".join(env_lines), encoding="utf-8")
    print(f"\n[완료] 환경 설정이 저장되었다: {env_path.name}")


def get_mock_bundle() -> Tuple[str, str]:
    """--dry-run 검증용 모의 명세 표본을 반환한다 (일부 실무 결함 포함)."""
    mock_docs = """
# Business Requirements: sample-corp AI Compliance Copilot
- BR-01: Read-only agent analyzes customer claims without mutating ledgers.
- BR-02: Enforce bidirectional PII masking before model inference.
- BR-03: Separate deterministic payout service with HITL approval over $2,500.
- BR-04: Maintain 5-year WORM audit logs and full cost label taxonomy.

# Solution Design Document: sample-corp AI Compliance Copilot
## 1. Overview & Contradictions
Resolves BR-01, BR-02, BR-03 (BR-04 omitted from design trace).
Contradictions C1 (Read-Only vs Auto-Refund) resolved via Split Control Plane.

## 2. SLAs & Targets
- End-to-end p95 latency <= 2.5 seconds (Proposed).
- Token cost under $0.12 per turn with 80% BigQuery scan reduction.
- Phase 1 MVP internal launch; Phase 2 external scale.

## 3. Architecture & Guardrails
```mermaid
flowchart TB
    User --> ModelArmor --> AgentEngine --> ExecutionService
```
- Agent Engine uses Read-Only identity (IAM Deny on DML); Execution Service checks Idempotency and HITL Maker-Checker.
- Bidirectional PII masking via Sensitive Data Protection and Model Armor (HTTP 403 block).
- Security: CMEK (Cloud KMS), Secret Manager, VPC-SC perimeter, 5-year WORM Bucket Lock.
- Reliability: Multi-region failover with RTO < 60s, RPO = 0, exponential backoff.
- Observability: Cloud Trace OpenTelemetry, structured JSON logging, CI/CD drift gate.
- Legacy reference note: Vertex AI Agent Builder migration complete.
"""
    return mock_docs, "내장 모의 명세 표본 (sample-corp)"


def detect_internal_contradictions(sdd_text: str) -> List[str]:
    """설계 명세서 본문 내부의 논리적 모순을 교차 검출한다."""
    contradictions: List[str] = []
    has_ro = bool(re.search(r"(?:Read-Only|읽기\s*전용|IAM Deny)", sdd_text, re.I))
    has_direct_dml = bool(re.search(r"(?:direct\s+(?:SQL|DML|INSERT|UPDATE|DELETE)|에이전트가\s*직접\s*(?:INSERT|UPDATE|DELETE|수정))", sdd_text, re.I))
    has_split_exec = bool(re.search(r"(?:Split Control Plane|Execution Service|실행\s*서비스\s*분리|non-LLM)", sdd_text, re.I))
    if has_ro and has_direct_dml and not has_split_exec:
        contradictions.append("Read-Only 에이전트 선언과 직접 쓰기(DML) 동작이 실행 평면 분리 없이 충돌한다.")

    has_pii_mask = bool(re.search(r"(?:PII\s*마스킹|Sensitive Data Protection|비식별화)", sdd_text, re.I))
    has_raw_log = bool(re.search(r"(?:raw\s+prompt\s+log|원문\s*프롬프트\s*저장|마스킹\s*없이\s*로깅)", sdd_text, re.I))
    if has_pii_mask and has_raw_log:
        contradictions.append("PII 마스킹 정책과 비마스킹 원문 프롬프트 로깅이 상호 모순된다.")

    sla_match = re.search(r"(?:p95|E2E)[^\n]{0,30}(?:<=|<|이내)\s*(\d+(?:\.\d+)?)\s*(?:s|초)\b", sdd_text, re.I)
    timeout_match = re.search(r"(?:sync|동기)[^\n]{0,30}timeout[^\n]{0,15}(\d+)\s*(?:s|초)\b", sdd_text, re.I)
    if sla_match and timeout_match and float(timeout_match.group(1)) > float(sla_match.group(1)) * 2:
        contradictions.append(
            f"목표 SLA({sla_match.group(1)}s) 대비 동기 타임아웃({timeout_match.group(1)}s)이 과도하게 길어 모순된다."
        )
    return contradictions


def analyze_readability(sdd_text: str) -> Tuple[int, int, List[str]]:
    """가독성(만연체 장문 수, 모호어 건수, 헤딩 계층 오류)을 분석한다."""
    clean_lines: List[str] = []
    in_code = False
    headings: List[int] = []
    for raw in sdd_text.splitlines():
        s = raw.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not s:
            continue
        hm = re.match(r"^(#{1,6})\s+", s)
        if hm:
            headings.append(len(hm.group(1)))
            continue
        if s.startswith("|") or s.startswith("<!--"):
            continue
        clean_lines.append(s)

    long_sentences = sum(1 for ln in clean_lines if len(ln) > 180)
    weasel_words = re.findall(
        r"\b(?:best[- ]effort|as needed|securely|properly|fast enough|scalable)\b|적절히|빠르게|충분한|알아서",
        "\n".join(clean_lines),
        re.I,
    )
    heading_skips: List[str] = []
    for prev_h, curr_h in zip(headings, headings[1:]):
        if curr_h - prev_h > 1:
            heading_skips.append(f"H{prev_h}->H{curr_h}")
    return long_sentences, len(weasel_words), heading_skips


def detect_gcp_upgrade_recommendations(docs_text: str) -> List[str]:
    """구형 Google Cloud 서비스 명칭, 퇴역 AI 모델, 구형 SDK 및 레거시 인프라를 탐지하고 업그레이드 가이드를 생성한다."""
    guides: List[str] = []

    legacy_name_map = [
        (r"\bAgentspace\b", "Agentspace -> Gemini Enterprise"),
        (r"(?<!gcloud\s)(?<!google_)\bDataplex\b(?!\.googleapis\.com)", "Dataplex -> Knowledge Catalog"),
        (r"\b(?:Vertex AI Agent Builder|GEAP)\b", "Vertex AI Agent Builder/GEAP -> Agent Platform / Agent Engine"),
        (r"\bCloud DLP\b", "Cloud DLP -> Sensitive Data Protection"),
    ]
    for pattern, guide in legacy_name_map:
        if re.search(pattern, docs_text):
            guides.append(f"명칭 갱신({guide})")

    retired_gemini = sorted(set(re.findall(r"\bgemini-(?:1\.0|1\.5|2\.0)(?:-[a-z0-9.\-]+)?\b", docs_text, re.I)))
    if retired_gemini:
        guides.append(f"퇴역/구세대 모델({', '.join(retired_gemini)}) -> 최신 Gemini Flash/Pro 업그레이드 권고")

    retired_palm = sorted(set(re.findall(r"\b(?:text-bison|chat-bison|textembedding-gecko)(?:@[0-9]+|-[0-9]+)?\b", docs_text, re.I)))
    if retired_palm:
        guides.append(f"퇴역 모델({', '.join(retired_palm)}) -> 최신 Gemini 및 gemini-embedding-001 업그레이드 권고")

    if (
        "text-multilingual-embedding-002" in docs_text
        and re.search(r"(?:output_dimensionality|outputDimensionality|\bMRL\b)", docs_text)
        and "gemini-embedding-001" not in docs_text
    ):
        guides.append("임베딩 모델(text-multilingual-embedding-002는 MRL 미지원) -> gemini-embedding-001 업그레이드 권고")

    if (
        re.search(r"(?:google-generativeai|google\.generativeai|vertexai\.generative_models)", docs_text)
        and "google-genai" not in docs_text
    ):
        guides.append("구형 Gemini SDK -> 공식 통합 google-genai SDK 마이그레이션 권고")

    if (
        re.search(r"(?:Cloud Functions\s*1st\s*gen|--no-gen2)", docs_text, re.I)
        and not re.search(r"(?:Cloud Run|2nd\s*gen)", docs_text, re.I)
    ):
        guides.append("Cloud Functions 1st gen -> Cloud Run 또는 Cloud Run functions(2nd gen) 업그레이드 권고")

    if (
        re.search(r"Serverless VPC Access", docs_text, re.I)
        and not re.search(r"Direct VPC Egress", docs_text, re.I)
    ):
        guides.append("Serverless VPC Access 커넥터 -> Direct VPC Egress 전환 검토 권고")

    return guides


def evaluate_rubric(docs_text: str) -> List[Dict[str, Any]]:
    """지정 경로의 모든 *.md 합본을 대상으로 25개 실전 루브릭(항목당 4점 = 100점)을 채점한다."""
    results: List[Dict[str, Any]] = []

    def add_check(suite: str, check_id: str, title: str, status: str, detail: str) -> None:
        score = 4 if status == "PASS" else (2 if status == "WARN" else 0)
        results.append(
            {
                "suite": suite,
                "id": check_id,
                "title": title,
                "status": status,
                "score": score,
                "max_score": 4,
                "detail": detail,
            }
        )

    # 1. Autonomy Boundaries & Measurable Success Criteria (R-01 ~ R-04)
    id_counts = collections.Counter(re.findall(r"\b(?:BR|REQ|PRD|CON)-\d{2,}\b", docs_text))
    if not id_counts:
        id_counts = collections.Counter(re.findall(r"\b(?:FR|NFR)-\d{2,}\b", docs_text))
    orphans = sorted(k for k, v in id_counts.items() if v < 2)
    if id_counts and not orphans:
        add_check("1. 자율성 경계 및 성공 기준", "R-01", "요구 사항 ID 교차 참조 완전성", "PASS", f"전체 명세 내 {len(id_counts)}개 요구 사항 ID 전수 교차 참조됨")
    elif id_counts:
        add_check("1. 자율성 경계 및 성공 기준", "R-01", "요구 사항 ID 교차 참조 완전성", "FAIL", f"미참조 고아 요구 사항(1회만 등장) 존재: {', '.join(orphans)}")
    else:
        add_check("1. 자율성 경계 및 성공 기준", "R-01", "요구 사항 ID 교차 참조 완전성", "WARN", "표준 요구 사항 ID(BR-01, REQ-01, FR-01 등) 체계가 확인되지 않는다.")

    has_ro_split = bool(re.search(r"(?:Read-Only|읽기\s*전용|IAM Deny|Split Control Plane|실행\s*서비스\s*분리)", docs_text, re.I))
    add_check("1. 자율성 경계 및 성공 기준", "R-02", "읽기 전용 Agent와 실행 평면 분리", "PASS" if has_ro_split else "FAIL", "읽기 전용 에이전트 권한과 상태 변경 실행 평면 분리 확인" if has_ro_split else "에이전트 읽기 전용 경계 또는 실행 서비스 분리가 누락되었다.")

    has_hitl = bool(re.search(r"(?:HITL|Human-in-the-Loop|Maker-Checker|사람\s*승인|수동\s*승인)", docs_text, re.I))
    add_check("1. 자율성 경계 및 성공 기준", "R-03", "고위험 작업 HITL 승인 게이트", "PASS" if has_hitl else "WARN", "HITL 승인 임계치 및 게이트 명시됨" if has_hitl else "고위험 작업 대상 HITL 승인 경계가 명시되지 않았다.")

    metric_lines = [ln.strip() for ln in docs_text.splitlines() if re.search(r"(?:\d+(?:\.\d+)?\s*(?:ms|s|%|USD|\$|RPS|QPS))", ln) and not ln.strip().startswith("```")]
    untagged = [ln for ln in metric_lines if not re.search(r"(?:\(Proposed\)|\(추정\)|\(가정\)|BR-\d+|REQ-\d+|PRD-\d+|FR-\d+|NFR-\d+|CON-\d+|ASM-\d+)", ln, re.I)]
    if not metric_lines:
        add_check("1. 자율성 경계 및 성공 기준", "R-04", "SLA/비용 수치 근거 및 (Proposed) 태깅", "WARN", "측정 가능한 정량적 성공 기준이 확인되지 않는다.")
    elif not untagged:
        add_check("1. 자율성 경계 및 성공 기준", "R-04", "SLA/비용 수치 근거 및 (Proposed) 태깅", "PASS", f"정량 수치 {len(metric_lines)}건 모두 출처 ID 또는 (Proposed) 태깅 완료")
    else:
        add_check("1. 자율성 경계 및 성공 기준", "R-04", "SLA/비용 수치 근거 및 (Proposed) 태깅", "WARN", f"정량 수치 {len(metric_lines)}건 중 {len(untagged)}건에 출처 ID 또는 (Proposed) 태깅 누락")

    # 2. Agent Topology, Compute, Memory & Tools (R-05 ~ R-07)
    has_topology = bool(re.search(r"(?:Agent Engine|Cloud Run|GKE|ADK|Vertex AI)", docs_text, re.I))
    add_check("2. Agent 토폴로지, 컴퓨트 및 도구", "R-05", "컴퓨트 런타임 및 Agent 토폴로지 명시", "PASS" if has_topology else "WARN", "Google Cloud 런타임 및 에이전트 토폴로지 정의됨" if has_topology else "에이전트 호스팅 런타임 및 컴포넌트 배치가 불명확하다.")

    has_tools_mem = bool(re.search(r"(?:Tool|도구|Schema|Memory|세션|RAG|Vector Search|Knowledge Catalog)", docs_text, re.I))
    add_check("2. Agent 토폴로지, 컴퓨트 및 도구", "R-06", "도구 스키마 및 상태/메모리 경계", "PASS" if has_tools_mem else "WARN", "도구 호출 인터페이스 또는 상태/메모리 전략 명시됨" if has_tools_mem else "에이전트 도구 인터페이스 또는 메모리/세션 경계 설계가 부족하다.")

    has_diagram = "```mermaid" in docs_text and ("flowchart" in docs_text or "sequenceDiagram" in docs_text)
    add_check("2. Agent 토폴로지, 컴퓨트 및 도구", "R-07", "아키텍처 시각화(Mermaid 다이어그램)", "PASS" if has_diagram else "WARN", "Mermaid 아키텍처 또는 시퀀스 다이어그램 포함됨" if has_diagram else "설계 문서 내 Mermaid 다이어그램이 누락되었다.")

    # 3. SAIF-Aligned Security, Privacy & Compliance (R-08 ~ R-11)
    has_bi_pii = bool(re.search(r"(?:bidirectional|양방향|ingress.*egress)", docs_text, re.I)) and bool(re.search(r"(?:PII|마스킹|Sensitive Data Protection|비식별)", docs_text, re.I))
    add_check("3. SAIF 보안, 프라이버시 및 컴플라이언스", "R-08", "양방향(Ingress+Egress) PII 마스킹", "PASS" if has_bi_pii else "FAIL", "입출력 양방향 PII 비식별화 통제 확인" if has_bi_pii else "입출력 양방향 PII 마스킹 설계가 누락되었다.")

    has_adv = bool(re.search(r"(?:Model Armor|Adversarial|Off-corpus|HTTP 403|프롬프트\s*인젝션)", docs_text, re.I))
    add_check("3. SAIF 보안, 프라이버시 및 컴플라이언스", "R-09", "적대적 입력 및 범위 외 질의 차단", "PASS" if has_adv else "WARN", "Model Armor 또는 범위 외 입력 차단 게이트 명시됨" if has_adv else "프롬프트 인젝션 및 범위 외 차단 통제가 부족하다.")

    has_sec = bool(re.search(r"(?:CMEK|Cloud KMS)", docs_text, re.I)) and bool(re.search(r"(?:Secret Manager|VPC-SC|VPC Service Controls)", docs_text, re.I))
    add_check("3. SAIF 보안, 프라이버시 및 컴플라이언스", "R-10", "암호화(CMEK), 시크릿 및 네트워크 경계", "PASS" if has_sec else "WARN", "CMEK, Secret Manager 또는 VPC-SC 경계 통제 확인" if has_sec else "CMEK, Secret Manager, VPC-SC 중 일부 보안 통제가 누락되었다.")

    has_pii_leak = bool(re.search(r"AIza[0-9A-Za-z\-_]{35}|sk-[A-Za-z0-9]{20,}|/Users/|/home/|C:\\Users\\", docs_text))
    add_check("3. SAIF 보안, 프라이버시 및 컴플라이언스", "R-11", "설계서 내 PII 및 시크릿 미노출", "FAIL" if has_pii_leak else "PASS", "로컬 경로 또는 시크릿 토큰 패턴이 검출되었다." if has_pii_leak else "민감 시크릿 및 로컬 홈 경로 노출 없음")

    # 4. Reliability, Resiliency & State Integrity (R-12 ~ R-14)
    has_rel = bool(re.search(r"(?:RTO|RPO|Multi-region|멀티\s*리전|다중\s*존|failover)", docs_text, re.I))
    add_check("4. 신뢰성, 회복 탄력성 및 상태 무결성", "R-12", "다중 영역 가용성 및 RTO/RPO 기준", "PASS" if has_rel else "WARN", "다중 리전/존 및 RTO/RPO 복구 기준 명시" if has_rel else "RTO/RPO 또는 다중 영역 장애 조치 기준이 명시되지 않았다.")

    has_idemp = bool(re.search(r"(?:Idempotency|멱등성|잠금)", docs_text, re.I))
    add_check("4. 신뢰성, 회복 탄력성 및 상태 무결성", "R-13", "상태 변경 멱등성(Idempotency) 보장", "PASS" if has_idemp else "WARN", "재시도 및 중복 실행 방어용 멱등성 잠금 명시됨" if has_idemp else "비동기 재시도 시 중복 실행 방어용 멱등성 설계가 누락되었다.")

    has_fail_path = bool(re.search(r"(?:fallback|폴백|alt\b|예외|timeout|타임아웃|circuit|서킷|backoff|백오프)", docs_text, re.I))
    add_check("4. 신뢰성, 회복 탄력성 및 상태 무결성", "R-14", "타임아웃, 백오프 및 예외 폴백 경로", "PASS" if has_fail_path else "FAIL", "타임아웃, 백오프 또는 예외 분기 경로 정의됨" if has_fail_path else "장애 시 폴백, 백오프 또는 타임아웃 예외 처리 설계가 누락되었다.")

    # 5. Observability, Auditability & Evaluation Pipelines (R-15 ~ R-17)
    has_obs = bool(re.search(r"(?:OpenTelemetry|Cloud Trace|구조화\s*로깅|JSON logging|Cloud Logging)", docs_text, re.I)) and bool(re.search(r"(?:CI/CD|drift|회귀|Eval)", docs_text, re.I))
    add_check("5. 관측성, 감사 추적 및 평가 파이프라인", "R-15", "OpenTelemetry 관측성 및 Eval CI/CD 게이트", "PASS" if has_obs else "WARN", "트레이싱/구조화 로깅 및 평가 회귀 게이트 포함" if has_obs else "OpenTelemetry 관측성 또는 Eval 회귀 게이트가 부족하다.")

    has_worm = bool(re.search(r"(?:WORM|Bucket Lock|Access Approval|불변\s*감사)", docs_text, re.I))
    add_check("5. 관측성, 감사 추적 및 평가 파이프라인", "R-16", "불변 감사 로그 보존 (WORM / Bucket Lock)", "PASS" if has_worm else "WARN", "WORM 감사 로그 보존 정책 포함" if has_worm else "감사 로그 불변 보존(WORM / Bucket Lock) 명시가 없다.")

    has_labels = all(k in docs_text for k in ("managed-by", "scenario", "env", "created-by")) or bool(re.search(r"label\s*taxonomy|라벨링", docs_text, re.I))
    add_check("5. 관측성, 감사 추적 및 평가 파이프라인", "R-17", "FinOps 4대 표준 리소스 라벨링", "PASS" if has_labels else "FAIL", "4대 표준 라벨 또는 비용 추적 택소노미 명시됨" if has_labels else "4대 표준 리소스 라벨(managed-by, scenario, env, created-by) 명시가 누락되었다.")

    # 6. Optimizing Latency & Modeling Token Economics (R-18 ~ R-19)
    has_latency = bool(re.search(r"(?:latency|레이턴시|TTFT|p95)", docs_text, re.I))
    add_check("6. 지연 시간 최적화 및 토큰 경제성", "R-18", "종단간 지연(p95/TTFT) 및 스트리밍 목표", "PASS" if has_latency else "WARN", "E2E 또는 TTFT 레이턴시 목표 명시됨" if has_latency else "p95 또는 TTFT 지연 시간 목표가 명시되지 않았다.")

    has_cost = bool(re.search(r"(?:SELECT \*|scan|캐시|TTL|budget|예산|쿼터|token)", docs_text, re.I))
    add_check("6. 지연 시간 최적화 및 토큰 경제성", "R-19", "토큰/스캔 비용 상한 및 캐싱 전략", "PASS" if has_cost else "WARN", "토큰 상한, 캐시 TTL 또는 스캔 절감 전략 명시됨" if has_cost else "토큰 소모 상한, 캐싱 또는 스캔 비용 제어 설계가 부족하다.")

    # 7. ADR, 논리 모순 교차 검증 및 가독성 (R-20 ~ R-25)
    has_adr = bool(re.search(r"(?:Contradiction|모순|\bC\d+\b|Trade-off|트레이드오프|ADR|Decision Gate|\bDG-\d+\b)", docs_text, re.I))
    add_check("7. ADR, 모순 교차 검증 및 가독성", "R-20", "모순 해소, ADR 및 트레이드오프 근거화", "PASS" if has_adr else "WARN", "아키텍처 트레이드오프 또는 모순 해소 기록 포함" if has_adr else "대안 트레이드오프(ADR) 및 원시 자료 모순 해소 기록이 누락되었다.")

    has_phases = bool(re.search(r"(?:Phase\s*1|MVP|1단계)", docs_text, re.I)) and bool(re.search(r"(?:Phase\s*2|Scale|2단계)", docs_text, re.I))
    add_check("7. ADR, 모순 교차 검증 및 가독성", "R-21", "단계적 출시 범위 분리 (MVP vs Scale)", "PASS" if has_phases else "WARN", "MVP와 확장 단계 범위가 명시 분리됨" if has_phases else "Phase 1(MVP)과 Phase 2(확장) 범위 분리가 명시되지 않았다.")

    logic_contradictions = detect_internal_contradictions(docs_text)
    add_check(
        "7. ADR, 모순 교차 검증 및 가독성",
        "R-22",
        "명세 내부 논리 모순 교차 검출",
        "FAIL" if logic_contradictions else "PASS",
        " / ".join(logic_contradictions) if logic_contradictions else "Read-Only 경계, PII 로깅, SLA-타임아웃 간 내부 모순 없음",
    )

    long_cnt, weasel_cnt, heading_skips = analyze_readability(docs_text)
    add_check(
        "7. ADR, 모순 교차 검증 및 가독성",
        "R-23",
        "가독성: 장문 만연체 및 헤딩 계층 정합성",
        "WARN" if (long_cnt > 3 or heading_skips) else "PASS",
        f"180자 초과 장문 {long_cnt}건, 헤딩 건너뛰기 {len(heading_skips)}건" if (long_cnt > 3 or heading_skips) else "문장 호흡이 간결하고 헤딩 계층(H1->H2->H3)이 일관됨",
    )

    add_check(
        "7. ADR, 모순 교차 검증 및 가독성",
        "R-24",
        "명확성: 검증 불가 모호어(Weasel Words) 배제",
        "WARN" if weasel_cnt > 0 else "PASS",
        f"모호한 표현 {weasel_cnt}건 검출(측정 가능한 정량 기준으로 교체 필요)" if weasel_cnt > 0 else "검증 불가능한 모호한 형용, 부사 미사용",
    )

    upgrade_guides = detect_gcp_upgrade_recommendations(docs_text)
    add_check(
        "7. ADR, 모순 교차 검증 및 가독성",
        "R-25",
        "Google Cloud 최신 서비스, 모델 및 SDK 버전 준수",
        "FAIL" if upgrade_guides else "PASS",
        " / ".join(upgrade_guides) if upgrade_guides else "최신 Google Cloud 정규 명칭, AI 모델 및 SDK 기준 충족",
    )

    return results


def generate_markdown_report(
    project_id: str,
    source_desc: str,
    results: List[Dict[str, Any]],
    is_dry_run: bool,
) -> str:
    """루브릭 채점 결과를 Markdown 리포트로 생성한다."""
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total_score = sum(r["score"] for r in results)
    max_score = sum(r["max_score"] for r in results)
    fails = [r for r in results if r["status"] == "FAIL"]
    warns = [r for r in results if r["status"] == "WARN"]
    gate_verdict = "PASS (구현 착수 가능)" if not fails and total_score >= 80 else "HOLD (보완 후 재평가 권장)"

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
        "> 본 리포트는 Google LLC 참조용 샘플 평가기의 출력 결과다.",
        "",
        "# Google Cloud 아키텍처 명세 실전 루브릭 평가 리포트",
        "",
        f"- **평가 일시**: {now_str}",
        f"- **실행 모드**: `{'DRY-RUN (모의 명세 시뮬레이션)' if is_dry_run else 'LIVE (로컬 명세 감사)'}`",
        f"- **참고 프로젝트**: `{project_id}`",
        f"- **평가 대상**: {source_desc}",
        f"- **종합 점수**: **{total_score} / {max_score}점** (`FAIL` {len(fails)}건, `WARN` {len(warns)}건) -> **{gate_verdict}**",
        "",
        "---",
        "",
        "## 1. 7대 아키텍처 차원 및 모순, 가독성 채점 결과",
        "",
        "| 영역 | ID | 점검 항목 | 상태 | 배점 | 평가 상세 |",
        "| :--- | :---: | :--- | :---: | :---: | :--- |",
    ]

    for r in results:
        lines.append(
            f"| {r['suite']} | `{r['id']}` | {r['title']} | `{r['status']}` | {r['score']}/{r['max_score']} | {r['detail']} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 2. 우선 보완 처방 (Action Items)",
            "",
        ]
    )

    if not fails and not warns:
        lines.append("- 모든 실전 루브릭 항목을 충족하여 즉시 구현 단계로 이행할 수 있다.")
    else:
        for item in fails + warns:
            lines.append(f"- **`[{item['status']}] {item['id']} ({item['title']})`**: {item['detail']}")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. 사내 거버넌스 4대 필수 표준 라벨링 및 참고 문서",
            "",
            f"- **표준 라벨 규약**: `--labels={STANDARD_LABELS}`",
            "- Google Cloud Architecture Framework ( https://cloud.google.com/architecture/framework )",
            "- Google Cloud Security Best Practices ( https://cloud.google.com/security/best-practices )",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    """메인 실행 진입점."""
    base_dir = pathlib.Path(__file__).resolve().parent
    load_dotenv_file(base_dir / ".env")
    args = parse_args()

    if args.config:
        run_config_mode(base_dir)
        return

    project_id = resolve_project_id(args.project, args.dry_run)

    if args.dry_run:
        print("[모의 실행] 내장 모의 아키텍처 명세(결함 포함 표본)로 루브릭 평가를 시뮬레이션한다...", flush=True)
        docs_text, source_desc = get_mock_bundle()
    else:
        md_files = (
            collect_markdown_files(parse_path_list(args.path))
            if args.path
            else auto_detect_docs(pathlib.Path.cwd(), base_dir)
        )
        if not md_files:
            print(
                "[오류] 평가할 마크다운(*.md) 문서를 찾을 수 없다. --path 파일 또는 디렉터리 경로를 지정한다.",
                file=sys.stderr,
            )
            sys.exit(1)
        docs_text = "\n\n".join(p.read_text(encoding="utf-8") for p in md_files)
        label = "+".join(p.name for p in md_files[:5]) + (f"+외{len(md_files) - 5}건" if len(md_files) > 5 else "")
        source_desc = f"문서 {len(md_files)}건 ({label})"

    print("[1/2] 7대 아키텍처 차원 및 모순, 가독성 루브릭(25개 항목) 정적 감사 수행 중...", flush=True)
    results = evaluate_rubric(docs_text)

    print("[2/2] 평가 리포트(report.md) 생성 및 요약 출력 중...", flush=True)
    report_md = generate_markdown_report(project_id, source_desc, results, args.dry_run)
    report_path = base_dir / "report.md"
    report_path.write_text(report_md, encoding="utf-8")

    total_score = sum(r["score"] for r in results)
    fails = sum(1 for r in results if r["status"] == "FAIL")
    warns = sum(1 for r in results if r["status"] == "WARN")
    passes = len(results) - fails - warns
    print("=" * 72)
    print("Google Cloud 아키텍처 명세 실전 루브릭 평가 결과")
    print("=" * 72)
    print(f"- 참고 프로젝트: {project_id}")
    print(f"- 평가 대상: {source_desc}")
    print(f"- 종합 점수: {total_score} / 100점 (PASS {passes}건, WARN {warns}건, FAIL {fails}건)")
    print("-" * 72)
    print(f"[완료] 상세 평가 리포트가 저장되었다: {report_path.name}")


if __name__ == "__main__":
    main()
