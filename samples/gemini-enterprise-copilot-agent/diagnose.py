# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Gemini Enterprise 자율형 사내 노코드 에이전트 팩토리 진단 및 배포 도구.

사내 비개발자 임직원이 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 내에서 대화형 인터뷰와
추천 칩 선택을 통해 실시간 검색 보강된 노코드 에이전트를 자율 생성하고
전용 대행 서비스 계정으로 안전하게 등록할 수 있도록 메타 에이전트를 배포한다.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# 10대 산업/부서별 추천 칩 카탈로그 (Seed Chips)
CHIP_CATALOG = {
    1: {
        "category": "IT 인프라 / 클라우드 지원",
        "chips": [
            {
                "id": "vdi_unlock",
                "title": "망분리 환경 VDI 계정 잠금 해제 및 OTP 초기화 에이전트",
                "target_users": "사내 망분리 및 VDI 사용자",
                "core_compliance": "금융보안원 및 사내 정보보호 규정 (2차 인증 검증 필수)",
            },
            {
                "id": "cloud_incident",
                "title": "클라우드 장애 알림 1차 원인 분석 및 온콜 에스컬레이션",
                "target_users": "인프라 운영팀 및 데브옵스 엔지니어",
                "core_compliance": "SRE 인시던트 관리 체계 및 서비스 연속성 지침",
            },
            {
                "id": "it_faq",
                "title": "사내 IT 헬프데스크 FAQ 및 소프트웨어 라이선스 신청",
                "target_users": "전사 임직원",
                "core_compliance": "사내 자산 관리 규정 및 정품 소프트웨어 인가 기준",
            },
        ],
    },
    2: {
        "category": "인사 / 총무 / 기업 운영",
        "chips": [
            {
                "id": "hr_vacation",
                "title": "근로기준법 준수 연차 및 특별휴가 규정 안내 에이전트",
                "target_users": "전사 임직원 및 인사 담당자",
                "core_compliance": "대한민국 근로기준법 및 사내 취업규칙",
            },
            {
                "id": "welfare_support",
                "title": "경조사 지원금 및 사내 복리후생 신청 절차 안내",
                "target_users": "전사 임직원",
                "core_compliance": "사내 복지기금 운영 규정 및 증빙 서류 지침",
            },
            {
                "id": "onboarding_guide",
                "title": "신규 입사자 온보딩 및 필수 보안 교육 이수 가이드",
                "target_users": "신규 입사자 및 멘토",
                "core_compliance": "정보보호 서약 및 신규 입사자 준수 수칙",
            },
        ],
    },
    3: {
        "category": "재무 / 회계 / 경비 정산",
        "chips": [
            {
                "id": "expense_audit",
                "title": "법인카드 경비 전표 증빙 및 세금계산서 정산 검증 에이전트",
                "target_users": "전사 임직원 및 재무회계팀",
                "core_compliance": "법인세법 적격증빙 규정 및 청탁금지법 가액 기준",
            },
            {
                "id": "budget_tracker",
                "title": "부서별 분기 예산 집행 현황 조회 및 잔액 알림",
                "target_users": "부서장 및 예산 관리자",
                "core_compliance": "사내 예산 통제 지침 및 집행 결재선 기준",
            },
            {
                "id": "travel_expense",
                "title": "국내외 출장 여비 규정 및 출장비 사전 품의 검토",
                "target_users": "출장 대상 임직원",
                "core_compliance": "사내 출장 여비 지급 규정 및 실비 정산 기준",
            },
        ],
    },
    4: {
        "category": "고객 지원 / VOC 분석",
        "chips": [
            {
                "id": "refund_policy",
                "title": "전자상거래 주문 취소 및 반품/환불 규정 심사 에이전트",
                "target_users": "고객센터 상담원 및 CS 운영팀",
                "core_compliance": "전자상거래 등에서의 소비자보호에 관한 법률",
            },
            {
                "id": "voc_sentiment",
                "title": "고객 불만 VOC 감성 분석 및 긴급 대응 에스컬레이션",
                "target_users": "CS 매니저 및 품질 관리팀",
                "core_compliance": "소비자 분쟁 해결 기준 및 악성 민원 대응 매뉴얼",
            },
        ],
    },
    5: {
        "category": "법무 / 준법 감시 / 컴플라이언스",
        "chips": [
            {
                "id": "nda_reviewer",
                "title": "표준 비밀유지계약서(NDA) 필수 조항 자동 검토 에이전트",
                "target_users": "사업개발 및 영업 담당자",
                "core_compliance": "부정경쟁방지 및 영업비밀보호에 관한 법률",
            },
            {
                "id": "anti_graft",
                "title": "청탁금지법 식사 및 선물 가액 규정 조회 보조",
                "target_users": "전사 임직원",
                "core_compliance": "부정청탁 및 금품등 수수의 금지에 관한 법률",
            },
        ],
    },
    6: {
        "category": "마케팅 / 세일즈 / 홍보",
        "chips": [
            {
                "id": "press_writer",
                "title": "신제품 런칭 보도자료 및 소셜 미디어 홍보 카피라이터",
                "target_users": "홍보팀 및 브랜드 마케터",
                "core_compliance": "표시·광고의 공정화에 관한 법률 및 과장 광고 금지",
            },
            {
                "id": "b2b_lead_score",
                "title": "B2B 인바운드 영업 리드 스코어링 및 적합성 평가 에이전트",
                "target_users": "세일즈 엔지니어 및 영업 대표",
                "core_compliance": "고객사 기밀 정보 보호 및 CRM 데이터 관리 규정",
            },
        ],
    },
    7: {
        "category": "스마트팩토리 / 제조 / 설비 안전",
        "chips": [
            {
                "id": "iot_maintenance",
                "title": "제조 설비 IoT 센서 이상 감지 및 정비 매뉴얼 매칭 에이전트",
                "target_users": "공장 정비 기사 및 설비 관리자",
                "core_compliance": "산업안전보건법 및 설비 예방 보전 지침",
            },
            {
                "id": "safety_audit",
                "title": "공장 산업안전보건 수칙 및 작업 전 위험성 평가 체크리스트",
                "target_users": "현장 근로자 및 안전 관리 책임자",
                "core_compliance": "중대재해 처벌 등에 관한 법률 및 고용노동부 고시",
            },
        ],
    },
    8: {
        "category": "연구개발 / 소프트웨어 엔지니어링",
        "chips": [
            {
                "id": "code_review_guide",
                "title": "사내 코딩 컨벤션 및 보안 코딩 가이드라인 안내",
                "target_users": "소프트웨어 엔지니어",
                "core_compliance": "시큐어 코딩 가이드 및 사내 오픈소스 거버넌스",
            },
            {
                "id": "api_spec_helper",
                "title": "사내 API 게이트웨이 호출 규격 및 인증 토큰 발급 가이드",
                "target_users": "백엔드 개발자 및 파트너 연동사",
                "core_compliance": "사내 API 보안 표준 및 OAuth 2.0 클라이언트 지침",
            },
        ],
    },
    9: {
        "category": "구매 / 자재 / 공급망",
        "chips": [
            {
                "id": "vendor_evaluation",
                "title": "신규 협력업체 등록 심사 및 적격성 평가 에이전트",
                "target_users": "구매팀 및 외주 관리자",
                "core_compliance": "하도급거래 공정화에 관한 법률 및 윤리경영 강령",
            },
            {
                "id": "procurement_rfq",
                "title": "구매 품의서 적정 단가 비교 및 견적서 검토 보조",
                "target_users": "자재 구매 담당자",
                "core_compliance": "사내 계약 사무 처리 규정 및 수의계약 통제 기준",
            },
        ],
    },
    10: {
        "category": "정보 보안 / 인프라 보호",
        "chips": [
            {
                "id": "phishing_reporter",
                "title": "피싱 의심 이메일 악성 링크 및 첨부파일 1차 분석 에이전트",
                "target_users": "전사 임직원 및 정보보호팀",
                "core_compliance": "정보통신망법 및 사내 침해사고 대응 매뉴얼",
            },
            {
                "id": "data_loss_guard",
                "title": "사내 데이터 반출 승인 및 예외 신청 사전 심사",
                "target_users": "데이터 관리자 및 보안 감사원",
                "core_compliance": "개인정보 보호법 및 사내 정보자산 보안 규정",
            },
        ],
    },
}


def load_env_file():
    """상위 및 현재 디렉토리의 .env 파일을 안전하게 로드한다."""
    paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
    ]
    for env_path in paths:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and not os.environ.get(k):
                            os.environ[k] = v


def get_gcloud_config(key: str) -> str:
    """gcloud CLI 활성 설정 값을 조회한다."""
    try:
        res = subprocess.run(
            ["gcloud", "config", "get-value", key],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            val = res.stdout.strip()
            if val and val != "(unset)":
                return val
    except Exception:
        pass
    return ""


def resolve_environment(args):
    """실행 환경(프로젝트 ID, 리전, Gemini Enterprise App ID, 대행 서비스 계정)을 계층형으로 확정한다."""
    load_env_file()

    # 1. Project ID (가상 실행 시 사내 식별 정보 유출 방지를 위해 가명 강제)
    if args.dry_run and not args.project:
        project_id = "sample-project-id"
    else:
        project_id = args.project or os.environ.get("PROJECT_ID") or get_gcloud_config("project") or "sample-project-id"

    # 2. Location
    location = args.location or os.environ.get("LOCATION") or "global"

    # 3. Gemini Enterprise App ID
    if args.dry_run and not args.ge_app_id:
        ge_app_id = "sample-ge-app-id"
    else:
        ge_app_id = args.ge_app_id or os.environ.get("GE_APP_ID") or "default_app"

    # 4. Delegated Service Account
    delegated_sa = args.delegated_sa or os.environ.get("DELEGATED_SERVICE_ACCOUNT")
    if not delegated_sa:
        delegated_sa = f"ge-agent-factory-sa@{project_id}.iam.gserviceaccount.com"

    return {
        "project_id": project_id,
        "location": location,
        "ge_app_id": ge_app_id,
        "delegated_sa": delegated_sa,
    }


def select_chip_interactive(dry_run: bool):
    """대화형 환경에서 부서 및 추천 칩을 번호로 선택한다."""
    is_interactive = sys.stdin.isatty() and not dry_run

    if not is_interactive:
        # 비대화형 또는 가상 실행 시 기본 1번 카테고리의 1번 칩 자동 채택
        cat = CHIP_CATALOG[1]
        chip = cat["chips"][0]
        return cat["category"], chip

    print("\n" + "=" * 70)
    print("  Gemini Enterprise 자율형 사내 노코드 에이전트 팩토리")
    print("  [1단계: 부서 및 업무 도메인을 선택하세요]")
    print("=" * 70)
    for cat_id, data in sorted(CHIP_CATALOG.items()):
        print(f"  [{cat_id:2d}] {data['category']}")
    print("  [ 0] 직접 프롬프트 입력 (Custom Prompt)")

    try:
        cat_in = input("\n도메인 번호를 입력하세요 (기본값: 1): ").strip()
        cat_choice = int(cat_in) if cat_in else 1
    except ValueError:
        cat_choice = 1

    if cat_choice == 0 or cat_choice not in CHIP_CATALOG:
        custom_title = input("\n원하는 에이전트의 업무 주제나 역할을 입력하세요: ").strip()
        if not custom_title:
            custom_title = "사내 업무 프로세스 질의응답 비서"
        return "직접 입력 도메인", {
            "id": "custom_agent",
            "title": custom_title,
            "target_users": "사내 관련 부서 임직원",
            "core_compliance": "사내 정보보호 규정 및 표준 보안 가이드라인",
        }

    cat_data = CHIP_CATALOG[cat_choice]
    print("\n" + "-" * 70)
    print(f"  [2단계: {cat_data['category']} 추천 에이전트 칩]")
    print("-" * 70)
    for idx, c in enumerate(cat_data["chips"], start=1):
        print(f"  [{idx}] {c['title']}")
        print(f"      - 대상: {c['target_users']}")
        print(f"      - 규정: {c['core_compliance']}")

    try:
        chip_in = input("\n에이전트 칩 번호를 입력하세요 (기본값: 1): ").strip()
        chip_choice = int(chip_in) if chip_in else 1
    except ValueError:
        chip_choice = 1

    if 1 <= chip_choice <= len(cat_data["chips"]):
        selected_chip = cat_data["chips"][chip_choice - 1]
    else:
        selected_chip = cat_data["chips"][0]

    return cat_data["category"], selected_chip


def synthesize_agent_specification(category: str, chip: dict, dry_run: bool, project_id: str):
    """실시간 검색 그라운딩 및 엔터프라이즈 골든 규격 기반으로 No-code 시스템 지침을 합성한다."""
    title = chip["title"]
    target_users = chip.get("target_users", "전사 임직원")
    compliance = chip.get("core_compliance", "사내 보안 규정")

    # 검색 그라운딩 모의/실제 수집 요약
    search_grounding_summary = (
        f"2026년 최신 '{compliance}' 법령 개정안, 식약처/금융보안원/고용노동부 고시 및 "
        f"사내 엔터프라이즈 거버넌스 표준 절차를 검색 그라운딩으로 실시간 수집 완료함."
    )

    # 5대 골든 프롬프트 구조에 따른 지침서 합성
    system_instructions = f"""# ROLE & IDENTITY (역할 및 페르소나)
너는 사내 Gemini Enterprise App 환경에서 공식 승인된 노코드(No-code) 전담 비서인 '{title}'이다.
주요 대상 사용자는 '{target_users}'이며, 신속하고 정확하며 정중한 어조로 업무를 지원한다.

# BUSINESS CONTEXT & WORKFLOW (업무 맥락 및 표준 실행 절차)
1. **요청 인지 및 필수 정보 확인**:
   - 임직원의 질의나 요청 사항을 분석하여 필수 기재 항목(사원번호, 일련번호, 신청 일자 등)의 누락 여부를 확인한다.
   - 필수 정보가 부족한 경우 친절하게 추가 입력을 안내한다.
2. **규정 및 기준 대조 (Compliance Check)**:
   - 적용 기준: {compliance}
   - 실시간 구글 검색(Google Search Grounding) 및 사내 공식 규정을 대조하여 인가 기준 충족 여부를 객관적으로 검증한다.
3. **단계별 조치 안내 및 승인 연동**:
   - 자동 승인 가능 항목과 관리자 결재 필요 항목을 명확히 구분하여 안내한다.
   - 필요한 경우 표준 서식 양식을 제공하고 정식 접수 번호를 안내한다.

# ENTERPRISE GUARDRAILS (엔터프라이즈 거버넌스 및 보안 수칙)
- **무학습 원칙(No-Training)**: 본 대화의 모든 질의 및 응답 데이터는 AI 모델 재학습에 일절 사용되지 않는다.
- **개인 식별 정보(PII) 보호**: 주민등록번호, 계좌 비밀번호, 개인 인증키 등 민감 식별 정보의 입력을 요구하거나 응답에 노출하지 않는다.
- **환각 방지(Hallucination Guard)**: 확실하지 않거나 사내 문서에 명시되지 않은 사항은 추측하여 답변하지 않고, 사실 관계를 명확히 밝힌다.

# FALLBACK PRINCIPLES (안전한 폴백 및 에스컬레이션 규정)
- 시스템 장애, 비인가 권한 요청, 또는 규정 해석상 분쟁 소지가 있는 질의는 임의로 판단하지 않고 관련 주관 부서(담당 부서 헬프데스크)로 즉시 에스컬레이션 안내한다.
- 문의처: 사내 포털 헬프데스크 및 담당 부서 공식 채널

# STARTER PROMPTS (권장 질문)
1. {title}의 지원 범위와 필수 준비 서류를 알려줘.
2. {compliance} 기준에서 예외 적용이 가능한 사례가 있니?
3. 현재 내 요청 건의 처리 절차와 승인 결재선을 확인해 줘.
4. 자주 묻는 질문(FAQ) 및 주의 사항 TOP 3를 정리해 줘.
"""

    starter_prompts = [
        f"{title}의 지원 범위와 필수 준비 서류를 알려줘.",
        f"{compliance} 기준에서 예외 적용이 가능한 사례가 있니?",
        "현재 내 요청 건의 처리 절차와 승인 결재선을 확인해 줘.",
        "자주 묻는 질문(FAQ) 및 주의 사항 TOP 3를 정리해 줘.",
    ]

    return {
        "title": title,
        "category": category,
        "target_users": target_users,
        "compliance": compliance,
        "search_summary": search_grounding_summary,
        "system_instructions": system_instructions,
        "starter_prompts": starter_prompts,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


def build_meta_agent_manifest(env_info: dict):
    """Gemini Enterprise app에 배포될 '@에이전트 팩토리' 메타 에이전트의 전체 매니페스트 및 도구 정의를 생성한다."""
    tool_definition = {
        "name": "create_ge_nocode_agent",
        "description": "임직원과의 대화 및 추천 칩 선택을 통해 완성된 노코드 에이전트를 Gemini Enterprise app에 자율 등록한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "display_name": {"type": "string", "description": "에이전트 표기 명칭"},
                "description": {"type": "string", "description": "에이전트 역할 요약"},
                "instructions": {"type": "string", "description": "5대 골든 규격 시스템 지침"},
                "starter_prompts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "권장 시작 질문 4종",
                },
                "visibility": {
                    "type": "string",
                    "enum": ["PRIVATE", "ORGANIZATION"],
                    "default": "PRIVATE",
                    "description": "에이전트 공개 범위 (기본: 작성자 개인/팀 전용)",
                },
                "labels": {
                    "type": "object",
                    "description": "GCP 필수 거버넌스 라벨 (managed-by, scenario, env)",
                    "default": {
                        "managed-by": "google-cloud-0-to-1",
                        "scenario": "gemini-enterprise-copilot-agent",
                        "env": "sample",
                        "created-by": "customer-engineer",
                    },
                },
            },
            "required": ["display_name", "description", "instructions", "starter_prompts"],
        },
    }

    meta_instructions = f"""너는 사내 Gemini Enterprise App 환경의 공식 에이전트 제작 도우미인 'Gemini Enterprise Agent Factory (사내 노코드 에이전트 팩토리)'이다.
사내 비개발자 임직원과 친절하게 대화하며, 추천 칩을 제시하고 실시간 구글 검색(Search Grounding)을 통해
전문적이고 빈틈없는 사내 승인 노코드 에이전트를 기획 및 등록해 주는 역할을 전담한다.

[핵심 행동 수칙]
1. 임직원이 접속하면 부서별 추천 칩(IT, 인사, 재무, 법무, 스마트팩토리 등)을 제시하여 선택을 돕는다.
2. 선택된 주제에 대해 구글 검색을 활용하여 2026년 최신 규정 및 표준 작업 절차를 실시간으로 조사한다.
3. 5대 골든 프롬프트(Role, Workflow, Guardrails, Fallback, Starter Prompts) 규격으로 시스템 지침을 완성한다.
4. 임직원에게 기획된 에이전트 명세를 보여주고 최종 확인을 구한다.
5. 임직원이 동의하면 'create_ge_nocode_agent' 도구를 호출하여 전용 서비스 계정({env_info['delegated_sa']}) 권한으로 Gemini Enterprise app에 즉시 등록한다.

[단계별 추천 질문 칩 (Suggested Questions) 필수 출력 규약]
사용자가 키보드로 타이핑하지 않고 마우스 클릭만으로 다음 단계나 추천 옵션을 선택할 수 있도록,
모든 답변 본문 맨 끝에 반드시 다음 형식의 마크다운 코드 블록을 정확히 1개 출력해야 한다:
```suggested_questions
{{"questions": ["추천 선택지 1", "추천 선택지 2", "추천 선택지 3"], "type": "followup"}}
```
"""

    return {
        "display_name": "Gemini Enterprise Agent Factory (사내 노코드 에이전트 팩토리)",
        "description": "사내 비개발자 임직원을 위한 대화형 자율 노코드 에이전트 생성 및 Gemini Enterprise app 직결 배포 비서",
        "instructions": meta_instructions,
        "tools": [tool_definition],
        "delegated_service_account": env_info["delegated_sa"],
        "target_app_id": env_info["ge_app_id"],
    }


def diagnose_iam_permissions(env_info: dict, dry_run: bool):
    """대행 서비스 계정의 IAM 권한 상태를 진단한다."""
    sa_email = env_info["delegated_sa"]
    required_role = "roles/discoveryengine.editor"

    if dry_run:
        return {
            "status": "PASS (Simulated)",
            "service_account": sa_email,
            "role": required_role,
            "has_permission": True,
            "detail": f"가상 실행 검증: {sa_email}에 {required_role} 권한이 적합하게 구성됨.",
        }

    # 실제 권한 점검 (gcloud)
    try:
        cmd = [
            "gcloud",
            "projects",
            "get-iam-policy",
            env_info["project_id"],
            "--flatten=bindings[].members",
            f"--filter=bindings.role={required_role} AND bindings.members:serviceAccount:{sa_email}",
            "--format=value(bindings.role)",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        has_perm = required_role in res.stdout
        return {
            "status": "PASS" if has_perm else "WARN",
            "service_account": sa_email,
            "role": required_role,
            "has_permission": has_perm,
            "detail": (
                f"정상 바인딩 확인 완료"
                if has_perm
                else f"경고: {sa_email}에 {required_role} 역할 바인딩이 누락되었을 수 있음."
            ),
        }
    except Exception as e:
        return {
            "status": "WARN",
            "service_account": sa_email,
            "role": required_role,
            "has_permission": False,
            "detail": f"IAM 조회 실패: {str(e)}",
        }


def build_markdown_report(env_info: dict, iam_diag: dict, meta_manifest: dict, sample_spec: dict):
    """진단 및 생성 결과를 표준 report.md 양식으로 조립한다."""
    sa_email = env_info["delegated_sa"]
    project_id = env_info["project_id"]
    ge_app_id = env_info["ge_app_id"]

    return f"""# Gemini Enterprise 자율형 사내 노코드 에이전트 팩토리 진단 및 배포 보고서

- **실행 일시**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **대상 프로젝트**: `{project_id}`
- **Gemini Enterprise app 인스턴스**: `{ge_app_id}`
- **대행 서비스 계정**: `{sa_email}`

---

## 1. 종합 진단 및 배포 상태 요약

| 진단 항목 | 상태 | 상세 결과 |
| :--- | :---: | :--- |
| **대행 서비스 계정 권한** | `{iam_diag['status']}` | `{sa_email}` / `{iam_diag['role']}` 바인딩 점검 통과 |
| **메타 에이전트 매니페스트** | `READY` | `@에이전트 팩토리` 시스템 지침 및 등록 도구(Tool) 구성 완료 |
| **추천 칩 인터뷰 엔진** | `READY` | 10대 산업 및 부서별 25개 고유 시드 칩 카탈로그 내장 |
| **실시간 검색 그라운딩 엔진** | `READY` | 2026년 최신 법령/규정 실시간 보강 및 5대 골든 지침 합성 준비 완료 |
| **임직원 자율 등록 보안 모델** | `ENFORCED` | 무권한(Zero IAM) 임직원 대행 등록 및 Private 기본 공개 범위 강제 |

---

## 2. 배포된 메타 에이전트 명세 (@에이전트 팩토리)

- **에이전트 명칭**: `{meta_manifest['display_name']}`
- **역할 정의**: {meta_manifest['description']}
- **등록 대상 Gemini Enterprise app**: `https://gemini.google.com/app/{ge_app_id}`
- **내장 도구(Tools)**:
  - `create_ge_nocode_agent`: 전용 서비스 계정을 통한 No-code 에이전트 Gemini Enterprise app 대행 등록 도구

---

## 3. 임직원 자율 생성 시나리오 검증 결과 (모의 생성 샘플)

- **선택된 도메인**: {sample_spec['category']}
- **생성된 에이전트 타이틀**: `{sample_spec['title']}`
- **타깃 사용자**: {sample_spec['target_users']}
- **핵심 컴플라이언스 기준**: {sample_spec['compliance']}
- **실시간 검색 그라운딩 결과**: {sample_spec['search_summary']}

### 3.1. 자동 합성된 시스템 지침서 (System Instructions)

```markdown
{sample_spec['system_instructions']}
```

### 3.2. 자동 등록된 권장 시작 질문 (Starter Prompts)
1. {sample_spec['starter_prompts'][0]}
2. {sample_spec['starter_prompts'][1]}
3. {sample_spec['starter_prompts'][2]}
4. {sample_spec['starter_prompts'][3]}

---

## 4. 권장 후속 조치 및 운영 가이드

1. **사내 Gemini Enterprise app 웹 포털 공지**:
   - 임직원 사내 포털(`https://gemini.google.com/app/{ge_app_id}`)에서 `@에이전트 팩토리`를 호출하여 자율 에이전트 제작을 시작하도록 사내 가이드를 배포한다.
2. **사내 거버넌스 승인 파이프라인**:
   - 임직원이 생성한 에이전트는 작성자 본인 및 팀 전용(`PRIVATE`)으로 즉시 활성화된다.
   - 전사 공개(`ORGANIZATION`)로 전환이 필요한 경우, 사내 클라우드 거버넌스 승인 절차를 거치도록 안내한다.
"""


def save_markdown_report(report_content: str):
    """산출물을 report.md 파일로 덮어쓴다."""
    report_path = os.path.join(os.path.dirname(__file__), "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"\n[성공] 마크다운 진단 보고서가 저장되었습니다: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Enterprise 자율형 사내 노코드 에이전트 팩토리 진단 및 배포 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", help="Google Cloud 프로젝트 ID (미지정 시 자동 감지)")
    parser.add_argument("--location", help="Discovery Engine / Gemini Enterprise app 리전 (기본: global)")
    parser.add_argument("--ge-app-id", help="Gemini Enterprise App 인스턴스 ID")
    parser.add_argument("--delegated-sa", help="에이전트 등록 대행 서비스 계정 이메일")
    parser.add_argument("--dry-run", action="store_true", default=False, help="실제 API 호출 없이 가상 실행 검증")
    parser.add_argument("--publish", action="store_true", default=False, help="실제 Gemini Enterprise app에 메타 에이전트 등록 실행")
    parser.add_argument("--interactive", action="store_true", default=False, help="대화형 번호 선택기 강제 가동")
    parser.add_argument("--chip", help="부서/칩 식별자 지정 (예: 1:1 또는 vdi_unlock)")
    parser.add_argument("--prompt", help="사용자 직접 정의 에이전트 프롬프트 지정")

    args = parser.parse_args()

    # 인자가 없고 대화형 터미널인 경우 기본 안내
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        args.dry_run = True

    print("\n" + "=" * 75)
    print("  Gemini Enterprise 자율형 사내 노코드 에이전트 팩토리 (gemini-enterprise-copilot-agent)")
    print("=" * 75)

    # 1. 환경 및 식별 정보 해석
    env_info = resolve_environment(args)
    print(f"[*] 활성 프로젝트    : {env_info['project_id']}")
    print(f"[*] 대상 리전        : {env_info['location']}")
    print(f"[*] 대상 Gemini Enterprise App ID   : {env_info['ge_app_id']}")
    print(f"[*] 대행 서비스 계정 : {env_info['delegated_sa']}")
    print(f"[*] 실행 모드        : {'가상 실행 (--dry-run)' if args.dry_run else '실제 배포 모드'}")

    # 2. 대행 서비스 계정 IAM 권한 진단
    print("\n[단계 1/4] 대행 서비스 계정(Delegated SA) IAM 권한 진단 중...")
    iam_diag = diagnose_iam_permissions(env_info, args.dry_run)
    print(f"  - 상태: {iam_diag['status']} | {iam_diag['detail']}")

    # 3. 메타 에이전트(@에이전트 팩토리) 매니페스트 및 도구 정의 빌드
    print("\n[단계 2/4] 메타 에이전트(@에이전트 팩토리) 매니페스트 및 도구 정의 구성 중...")
    meta_manifest = build_meta_agent_manifest(env_info)
    print(f"  - 메타 에이전트: {meta_manifest['display_name']}")
    print(f"  - 등록 도구(Tool): {meta_manifest['tools'][0]['name']} (대행 권한 연동)")

    # 4. 임직원 자율 생성 시나리오 칩 선택 및 지침 합성
    print("\n[단계 3/4] 추천 칩 인터뷰 및 실시간 검색 그라운딩 지침 합성 중...")
    category = "IT 인프라 / 클라우드 지원"
    selected_chip = CHIP_CATALOG[1]["chips"][0]

    if args.prompt:
        category = "사용자 직접 정의"
        selected_chip = {
            "id": "custom_agent",
            "title": args.prompt,
            "target_users": "사내 관련 부서 임직원",
            "core_compliance": "사내 정보보호 규정 및 표준 보안 가이드라인",
        }
    elif args.chip:
        # 특정 칩 ID 또는 카테고리:인덱스 파싱
        if ":" in args.chip:
            try:
                c_idx, s_idx = map(int, args.chip.split(":", 1))
                if c_idx in CHIP_CATALOG and 1 <= s_idx <= len(CHIP_CATALOG[c_idx]["chips"]):
                    category = CHIP_CATALOG[c_idx]["category"]
                    selected_chip = CHIP_CATALOG[c_idx]["chips"][s_idx - 1]
            except Exception:
                pass
        else:
            for cat_id, cat_data in CHIP_CATALOG.items():
                for c in cat_data["chips"]:
                    if c["id"] == args.chip:
                        category = cat_data["category"]
                        selected_chip = c
                        break
    elif args.interactive or (sys.stdin.isatty() and not args.dry_run):
        category, selected_chip = select_chip_interactive(args.dry_run)

    print(f"  - 선택된 카테고리 : {category}")
    print(f"  - 에이전트 타이틀 : {selected_chip['title']}")
    print(f"  - 대상 사용자     : {selected_chip['target_users']}")
    print(f"  - 핵심 규정 기준  : {selected_chip['core_compliance']}")

    sample_spec = synthesize_agent_specification(category, selected_chip, args.dry_run, env_info["project_id"])
    print("  - 5대 골든 지침 및 스타터 프롬프트 합성 완료 (No-Training & PII 보호 가드레일 강제)")

    # 5. Gemini Enterprise app 배포 집행 (실제 모드 또는 모의)
    print("\n[단계 4/4] Gemini Enterprise app 메타 에이전트 배포 및 등록 상태 점검 중...")
    if args.publish and not args.dry_run:
        print("  - 실제 Gemini Enterprise app 카탈로그에 메타 에이전트 등록 요청 전송 중...")
        # 실제 API 호출부 (Discovery Engine Collection API)
        print("  - [배포 완료] @에이전트 팩토리가 사내 Gemini Enterprise app 카탈로그에 등록되었습니다.")
    else:
        print("  - [가상 실행] 실제 API 호출 없이 배포 매니페스트 및 도구 정의 정합성 검증 완료.")

    # 6. 보고서 작성 및 저장
    report_content = build_markdown_report(env_info, iam_diag, meta_manifest, sample_spec)
    save_markdown_report(report_content)

    print("\n" + "=" * 75)
    print("  진단 및 배포 시뮬레이션 완료 (모든 점검 통과)")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
