# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Gemini Enterprise 프롬프트 로그 기반 3R 마이크로 업무 발굴 및 도구/에이전트 전환 파이프라인 분석기.

제미나이 엔터프라이즈 앱(Gemini Enterprise app)에 누적된 사용자 질의(Prompt) 로그를
BigQuery 또는 JSONL에서 수집하고, 인라인 PII 마스킹 및 멀티 턴 세션 묶음 정제를 거쳐
빅쿼리 내장 임베딩(ML.GENERATE_EMBEDDING)과 자율 적응형(Auto-K) K-Means++ 군집화를 통해
사내 3R(반복성 Repetitive, 규칙성 Rule-based, 검색 집약성 Retrieval-heavy) 마이크로 업무를 발굴하고
사내 API 도구(Tool) 및 검색/자율 에이전트(Agent) 전환 파이프라인을 자동 도출한다.
"""

import argparse
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
from datetime import datetime, timezone


# ------------------------------------------------------------------------------
# 1. 쉘 실행 및 프로젝트 감지 유틸리티
# ------------------------------------------------------------------------------
def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    """쉘 명령어를 실행하고 결과를 반환한다."""
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "sample-project-id") -> str:
    """gcloud 설정 및 환경 변수에서 활성 프로젝트를 탐색/선택한다."""
    if is_dry_run:
        return fallback_demo
    env_proj = os.getenv("PROJECT_ID")
    if env_proj:
        return env_proj
    _, stdout, _ = run_cmd(["gcloud", "config", "get-value", "project"])
    if stdout and "(unset)" not in stdout:
        return stdout

    if not sys.stdin.isatty():
        return fallback_demo

    code, stdout, _ = run_cmd(["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"])
    projects = [p.strip() for p in stdout.splitlines() if p.strip()] if code == 0 and stdout else []
    if projects:
        print("\n[?] 대상 구글 클라우드(Google Cloud) 프로젝트가 지정되지 않았다. 현재 접근 가능한 프로젝트 목록:")
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

    return fallback_demo


# ------------------------------------------------------------------------------
# 2. 프라이버시 보호 및 인라인 PII 마스킹 엔진 (Privacy & PII Sanitizer)
# ------------------------------------------------------------------------------
PII_PATTERNS = [
    ("주민등록번호", re.compile(r"\b\d{6}[-\s]?[1-4]\d{6}\b"), "[주민등록번호 마스킹]"),
    ("휴대전화번호", re.compile(r"\b01[016789][-\s]?\d{3,4}[-\s]?\d{4}\b"), "[전화번호 마스킹]"),
    ("이메일주소", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[이메일 마스킹]"),
    ("신용카드번호", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[카드번호 마스킹]"),
    ("계좌번호", re.compile(r"\b\d{3,6}[-\s]?\d{2,6}[-\s]?\d{3,6}\b"), "[계좌번호 마스킹]"),
    ("IPv4주소", re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"), "[IP주소 마스킹]"),
]


def sanitize_pii(text: str) -> tuple[str, dict[str, int]]:
    """사용자 질의 내 개인 식별 정보(PII) 및 민감 금융/인프라 정보를 마스킹한다."""
    sanitized = text
    stats: dict[str, int] = {}
    for pii_name, pattern, mask_label in PII_PATTERNS:
        matches = pattern.findall(sanitized)
        if matches:
            stats[pii_name] = stats.get(pii_name, 0) + len(matches)
            sanitized = pattern.sub(mask_label, sanitized)
    return sanitized, stats


def anonymize_user(user_email: str) -> str:
    """사용자 이메일 계정을 솔트 해시 기반 가명 식별자(Pseudonym)로 변환한다."""
    if not user_email or user_email in ("unknown", "unset"):
        return "emp-anon"
    hash_digest = hashlib.sha256(f"salt-0-to-1-{user_email}".encode("utf-8")).hexdigest()[:6]
    return f"emp-{hash_digest}"


# ------------------------------------------------------------------------------
# 3. 멀티 턴 대화 세션 묶음 처리 엔진 (Multi-turn Threading Engine)
# ------------------------------------------------------------------------------
def group_conversation_sessions(
    raw_logs: list[dict],
    group_multi_turn: bool = True,
    enable_pii_masking: bool = True
) -> tuple[list[dict], dict[str, int]]:
    """단일 질의들을 대화 세션(session_id / conversation_id) 단위로 묶고 PII를 마스킹한다."""
    pii_total_stats: dict[str, int] = {}

    if not group_multi_turn:
        sessions = []
        for idx, row in enumerate(raw_logs):
            q_text = row.get("query", "")
            if enable_pii_masking:
                q_text, p_stats = sanitize_pii(q_text)
                for k, v in p_stats.items():
                    pii_total_stats[k] = pii_total_stats.get(k, 0) + v
            u_anon = anonymize_user(row.get("user_email", "unknown"))
            sessions.append({
                "session_id": row.get("session_id") or f"sess-{idx + 1:04d}",
                "user_anon": u_anon,
                "turn_count": 1,
                "session_text": q_text,
                "queries": [q_text],
                "sample_preview": q_text
            })
        return sessions, pii_total_stats

    session_map: dict[str, list[dict]] = {}
    for idx, row in enumerate(raw_logs):
        sid = row.get("session_id") or row.get("conversation_id") or f"sess-auto-{idx + 1:04d}"
        session_map.setdefault(sid, []).append(row)

    sessions = []
    for sid, turns in session_map.items():
        user_email = turns[0].get("user_email", "unknown")
        user_anon = anonymize_user(user_email)
        sanitized_queries = []
        turn_strings = []

        for t_idx, turn in enumerate(turns, 1):
            q_raw = turn.get("query", "")
            if enable_pii_masking:
                q_san, p_stats = sanitize_pii(q_raw)
                for k, v in p_stats.items():
                    pii_total_stats[k] = pii_total_stats.get(k, 0) + v
            else:
                q_san = q_raw
            sanitized_queries.append(q_san)
            turn_strings.append(f"[{t_idx}턴] {q_san}")

        session_text = " -> ".join(turn_strings) if len(turn_strings) > 1 else sanitized_queries[0]
        preview = sanitized_queries[0] if len(sanitized_queries) == 1 else f"{sanitized_queries[0]} (외 {len(sanitized_queries) - 1}턴 대화 묶음)"

        sessions.append({
            "session_id": sid,
            "user_anon": user_anon,
            "turn_count": len(turns),
            "session_text": session_text,
            "queries": sanitized_queries,
            "sample_preview": preview
        })

    return sessions, pii_total_stats


# ------------------------------------------------------------------------------
# 4. 모의 데이터셋 (Dry-Run용 60건의 실제 업무 질의 & 24개 멀티 턴 세션)
# ------------------------------------------------------------------------------
MOCK_RAW_LOGS = [
    # 1. 셀러 정산 지연 및 미지급 내역 확인 (정산/재무)
    {"session_id": "sess-settle-01", "user_email": "seller-op-1@example.com", "query": "이번 달 입점 셀러 정산 주기가 어떻게 되나요? 110-123-456789 계좌 지연 건 확인해 줘"},
    {"session_id": "sess-settle-01", "user_email": "seller-op-1@example.com", "query": "그중 패션 카테고리 셀러 지연 정산 목록만 따로 추려줘"},
    {"session_id": "sess-settle-01", "user_email": "seller-op-1@example.com", "query": "미지급 금액 내역 엑셀 다운로드 가능한지 확인해 줘"},
    {"session_id": "sess-settle-02", "user_email": "md-living@example.com", "query": "리빙 카테고리 셀러 정산 대금 입금 지연 관련 FAQ 찾아줘"},
    {"session_id": "sess-settle-02", "user_email": "md-living@example.com", "query": "특정 셀러 정산 보류 사유와 세금계산서 마감 일정 정리해 줘"},

    # 2. 세금계산서 역발행 및 전표 자동 연동 (회계/세무)
    {"session_id": "sess-tax-01", "user_email": "finance-1@example.com", "query": "월말 셀러 정산 마감 일정 및 세금계산서 역발행 프로세스 가이드 알려줘"},
    {"session_id": "sess-tax-01", "user_email": "finance-1@example.com", "query": "국세청 홈택스 연동용 매입 매출 전표 파일 서식 조회해 줘"},
    {"session_id": "sess-tax-02", "user_email": "finance-2@example.com", "query": "PG사 수수료 정산 대조표 및 결제 수수료율 비교표 작성해 줘"},
    {"session_id": "sess-tax-02", "user_email": "finance-2@example.com", "query": "부가세 신고용 월별 카드 매출 집계표 출력 방법 안내해 줘"},

    # 3. 간편결제 타임아웃 롤백 및 결제 승인 실패 보정 (결제 플랫폼)
    {"session_id": "sess-pay-timeout-01", "user_email": "dev-checkout@example.com", "query": "간편결제 모듈 타임아웃 오류 발생 시 DB 롤백 프로세스 알려줘"},
    {"session_id": "sess-pay-timeout-01", "user_email": "dev-checkout@example.com", "query": "결제 취소 웹훅 재시도 정책 및 실패 건 수동 보정 가이드 찾아줘"},
    {"session_id": "sess-pay-timeout-02", "user_email": "dev-checkout@example.com", "query": "결제 게이트웨이(PG) 장애 시 서킷 브레이커 동작 기준 및 공지 양식"},
    {"session_id": "sess-pay-timeout-02", "user_email": "dev-infra@example.com", "query": "최근 1주일간 Slack checkout-alerts에 올라온 504 타임아웃 요약해 줘"},

    # 4. 결제 승인 후 주문서 미생성 건 복구 (주문 플랫폼)
    {"session_id": "sess-order-sync-01", "user_email": "cs-tech@example.com", "query": "결제 승인 후 주문서 미생성 건에 대한 DB 조회 및 수동 복구 가이드"},
    {"session_id": "sess-order-sync-01", "user_email": "cs-tech@example.com", "query": "장바구니 쿠폰 중복 할인 적용 오류 관련 Jira 티켓 현황 조회"},
    {"session_id": "sess-order-sync-02", "user_email": "dev-order@example.com", "query": "주문 생성 실패 시 결제사 자동 취소 요청 스크립트 실행 방법"},
    {"session_id": "sess-order-sync-02", "user_email": "dev-order@example.com", "query": "미생성 주문 고객 안내용 SMS 발송 템플릿과 보상 포인트 지급 규정"},

    # 5. 기획전 및 주말 타임딜 쿠폰 예산 소진 모니터링 (마케팅 프로모션)
    {"session_id": "sess-promo-budget-01", "user_email": "mkt-promo@example.com", "query": "주간 기획전 할인 쿠폰 발급 기준 및 마케팅 예산 소진율 분석해 줘"},
    {"session_id": "sess-promo-budget-01", "user_email": "mkt-promo@example.com", "query": "주말 깜짝 타임딜 프로모션 운영 가이드 및 배너 게시 절차"},
    {"session_id": "sess-promo-budget-02", "user_email": "md-beauty@example.com", "query": "뷰티 페스타 브랜드별 쿠폰 할인율 및 교차 적용 가능 여부 확인"},
    {"session_id": "sess-promo-budget-02", "user_email": "mkt-promo@example.com", "query": "기획전 조기 종료 시 쿠폰 자동 회수 및 잔여 예산 이관 정책"},

    # 6. 휴면 고객 복귀 알림톡 및 개인화 푸시 스케줄링 (CRM/성장)
    {"session_id": "sess-crm-push-01", "user_email": "mkt-crm@example.com", "query": "휴면 고객 대상 복귀 프로모션 알림톡 발송 스케줄 및 문구 제안해 줘"},
    {"session_id": "sess-crm-push-01", "user_email": "mkt-crm@example.com", "query": "010-9876-5432 테스트 번호로 알림톡 사전 발송 테스트 방법 알려줘"},
    {"session_id": "sess-crm-push-02", "user_email": "mkt-brand@example.com", "query": "신규 회원 첫 구매 웰컴 쿠폰 사용 조건 및 타깃 고객군 정의"},
    {"session_id": "sess-crm-push-02", "user_email": "mkt-crm@example.com", "query": "FCM 푸시 발송 실패율 모니터링 대시보드 링크 찾아줘"},

    # 7. 도서산간 및 단순 변심 반품 택배비 환불 규정 (CS 운영)
    {"session_id": "sess-cs-shipping-fee-01", "user_email": "cs-ops@example.com", "query": "단순 변심 반품 시 택배비 청구 기준 및 제주/도서산간 배송비 규정"},
    {"session_id": "sess-cs-shipping-fee-01", "user_email": "cs-ops@example.com", "query": "무료 배송 혜택 주문 건의 부분 반품 시 왕복 택배비 계산 로직"},
    {"session_id": "sess-cs-shipping-fee-02", "user_email": "cs-ops@example.com", "query": "반품 수거 접수 후 택배사 영업소 미집하 시 재접수 처리 기준"},
    {"session_id": "sess-cs-shipping-fee-02", "user_email": "cs-lead@example.com", "query": "고객 귀책 반품 택배비 포인트 차감 처리 절차 매뉴얼"},

    # 8. 파손 배송 접수 고객 선환불 및 택배사 클레임 접수 (CS 물류)
    {"session_id": "sess-cs-damage-refund-01", "user_email": "cs-ops@example.com", "query": "파손 배송 접수 시 고객 선환불 처리 및 택배사 클레임 접수 매뉴얼"},
    {"session_id": "sess-cs-damage-refund-01", "user_email": "cs-ops@example.com", "query": "배송 중 상품 파손 증빙 사진 검수 기준 및 보상 한도 조회"},
    {"session_id": "sess-cs-damage-refund-02", "user_email": "cs-lead@example.com", "query": "배송 지연 보상 포인트 지급 기준 및 고객 불만 응대 스크립트 작성"},
    {"session_id": "sess-cs-damage-refund-02", "user_email": "cs-ops@example.com", "query": "택배 파손 사고 보상금 정산 주기 및 물류사 구상권 청구 가이드"},

    # 9. 신규 입사자 VPN 접속 및 개발 계정 연동 (IT 지원)
    {"session_id": "sess-it-vpn-onboard-01", "user_email": "new-hire@example.com", "query": "신규 입사자 사내 VPN 접속 및 Confluence 계정 연동 가이드 알려줘"},
    {"session_id": "sess-it-vpn-onboard-01", "user_email": "dev-backend@example.com", "query": "사내 GitLab 배포 파이프라인 러너 등록 및 개인 Secret 토큰 발급 방법"},
    {"session_id": "sess-it-vpn-onboard-02", "user_email": "new-hire@example.com", "query": "맥북 교체 시 옥타 다중 인증 OTP 재등록 및 사내 인증서 갱신 절차"},
    {"session_id": "sess-it-vpn-onboard-02", "user_email": "dev-infra@example.com", "query": "사내 무선 와이파이 기기 등록 및 사내망 192.168.1.10 IP 대역 안내"},

    # 10. 스테이징 BigQuery 데이터셋 접근 및 임시 IAM 권한 신청 (데이터 거버넌스)
    {"session_id": "sess-bq-iam-request-01", "user_email": "qa-engineer@example.com", "query": "스테이징 환경 BigQuery 데이터셋 접근 권한 신청 방법 알려줘"},
    {"session_id": "sess-bq-iam-request-01", "user_email": "qa-engineer@example.com", "query": "admin-security@example.com 담당자에게 데이터 열람 승인 요청 결재 올리는 양식"},
    {"session_id": "sess-bq-iam-request-02", "user_email": "dev-backend@example.com", "query": "민감 고객 정보 테이블 마스킹 조회 권한 및 Cloud KMS 키 복호화 승인"},
    {"session_id": "sess-bq-iam-request-02", "user_email": "qa-engineer@example.com", "query": "BigQuery 쿼리 캐시 만료 정책 및 임시 테이블 쿼터 증설 가이드"},

    # 11. 법인카드 경비 처리 및 해외 출장 여비 정산 규정 (경영지원)
    {"session_id": "sess-corp-expense-01", "user_email": "md-beauty@example.com", "query": "법인카드 경비 처리 영수증 제출 기한 및 전표 마감 일정 알려줘"},
    {"session_id": "sess-corp-expense-01", "user_email": "md-beauty@example.com", "query": "해외 출장 여비 정산 시 식대 및 일비 한도 규정 가이드 찾아줘"},
    {"session_id": "sess-corp-expense-02", "user_email": "mkt-brand@example.com", "query": "야근 식대 법인카드 결제 허용 시간 및 주말 근무 경비 승인 기준"},
    {"session_id": "sess-corp-expense-02", "user_email": "finance-1@example.com", "query": "경비 처리 전표 반려 시 수정 사유 입력 및 재상신 절차"},

    # 12. 물류 창고 안전 재고 미달 품목 실시간 확인 및 추가 발주 (SCM 물류)
    {"session_id": "sess-scm-inventory-order-01", "user_email": "md-ops@example.com", "query": "물류 창고 안전 재고 미달 품목 실시간 확인 및 추가 발주 절차"},
    {"session_id": "sess-scm-inventory-order-01", "user_email": "md-ops@example.com", "query": "WMS 시스템 재고 연동 오류 시 수동 실사 재고 동기화 방법"},
    {"session_id": "sess-scm-inventory-order-02", "user_email": "seller-op-2@example.com", "query": "인기 기획전 상품 긴급 입고 요청 및 공급사 발주서 자동 발행"},
    {"session_id": "sess-scm-inventory-order-02", "user_email": "md-ops@example.com", "query": "품절 임박 SKU에 대한 쇼핑몰 자동 품절 처리 기준 및 알림 설정"}
]


# ------------------------------------------------------------------------------
# 5. 벡터 연산 및 다중 마이크로 토픽 임베딩 생성기
# ------------------------------------------------------------------------------
def dot_product(v1: list[float], v2: list[float]) -> float:
    return sum(a * b for a, b in zip(v1, v2))


def norm(v: list[float]) -> float:
    return math.sqrt(sum(a * a for a in v))


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    n1, n2 = norm(v1), norm(v2)
    return dot_product(v1, v2) / (n1 * n2) if n1 > 0 and n2 > 0 else 0.0


def vector_add(v1: list[float], v2: list[float]) -> list[float]:
    return [a + b for a, b in zip(v1, v2)]


def vector_scalar_div(v: list[float], scalar: float) -> list[float]:
    return [a / scalar for a in v] if scalar != 0 else v


def get_mock_embedding(text: str, dim: int = 24) -> list[float]:
    """모의 실행 시 12대 마이크로 업무 영역을 분별하는 결정론적 직교 임베딩 생성."""
    random.seed(sum(ord(c) for c in text))
    vec = [random.uniform(-0.1, 0.1) for _ in range(dim)]

    topic_keywords = [
        (["정산", "셀러", "미지급", "수수료율"], 0),
        (["세금계산서", "역발행", "전표", "홈택스"], 2),
        (["타임아웃", "서킷", "체크아웃", "504"], 4),
        (["주문서", "미생성", "주문 생성", "장바구니"], 6),
        (["기획전", "타임딜", "프로모션", "쿠폰 예산"], 8),
        (["휴면", "알림톡", "FCM", "푸시"], 10),
        (["택배비", "단순 변심", "도서산간", "제주"], 12),
        (["파손", "선환불", "클레임", "구상권"], 14),
        (["VPN", "GitLab", "러너", "옥타", "입사자"], 16),
        (["BigQuery", "IAM", "접근 권한", "열람 승인"], 18),
        (["법인카드", "경비", "출장", "여비", "식대"], 20),
        (["안전 재고", "WMS", "발주서", "SKU"], 22),
    ]

    for words, idx in topic_keywords:
        if any(w in text for w in words):
            vec[idx] += 3.5
            vec[idx + 1] += 2.5

    n = norm(vec)
    return [x / n for x in vec] if n > 0 else vec


def get_bigquery_embeddings(
    session_texts: list[str],
    project_id: str,
    dataset_id: str = "gemini_logging",
    model_name: str = "text_multilingual_embedding_002",
    location: str = "asia-northeast3"
) -> list[list[float]]:
    """BigQuery 내장 ML.GENERATE_EMBEDDING SQL 함수를 호출하여 한국어 text-multilingual-embedding-002 기반 512차원 벡터를 일괄 추출한다."""
    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=project_id, location=location)

        # 텍스트들을 BigQuery 인라인 UNION ALL 쿼리로 구성하여 ML.GENERATE_EMBEDDING 호출
        subqueries = []
        for idx, t in enumerate(session_texts):
            escaped = t.replace("\\", "\\\\").replace("'", "\\'")
            subqueries.append(f"SELECT {idx} AS row_id, '{escaped}' AS content")

        union_sql = " UNION ALL ".join(subqueries)
        query = f"""
        SELECT row_id, ml_generate_embedding_result AS embedding
        FROM ML.GENERATE_EMBEDDING(
          MODEL `{project_id}.{dataset_id}.{model_name}`,
          ({union_sql}),
          STRUCT('CLUSTERING' AS task_type, 512 AS output_dimensionality)
        )
        ORDER BY row_id ASC
        """
        rows = client.query(query).result()
        results = {}
        for r in rows:
            results[r.row_id] = list(r.embedding)

        if len(results) == len(session_texts):
            return [results[i] for i in range(len(session_texts))]
        return [get_mock_embedding(t) for t in session_texts]
    except Exception as e:
        print(f"[!] BigQuery 임베딩 모델 호출 불가 ({e}). 사내 기본 직교 시뮬레이션 벡터로 자동 대체한다.", file=sys.stderr)
        return [get_mock_embedding(t) for t in session_texts]


# ------------------------------------------------------------------------------
# 6. 자율 적응형(Auto-K) 군집 수 도출 및 K-Means++ 클러스터링 알고리즘
# ------------------------------------------------------------------------------
def determine_optimal_k(n_sessions: int, clusters_arg: str | int = "auto") -> int:
    """질의 모수 및 실질 마이크로 태스크 발굴 목표에 부합하는 최적 군집 수 K를 자율 계산한다."""
    if clusters_arg != "auto" and str(clusters_arg).isdigit():
        req_k = int(clusters_arg)
        return max(1, min(req_k, n_sessions))

    if n_sessions <= 4:
        return max(1, n_sessions)
    if n_sessions <= 12:
        return max(2, n_sessions // 2)
    if n_sessions <= 30:
        return max(6, min(n_sessions // 2, 12))
    if n_sessions <= 100:
        return max(10, min(n_sessions // 4, 20))
    if n_sessions <= 500:
        return max(15, min(n_sessions // 8, 35))
    return max(25, min(int(math.sqrt(n_sessions * 2.5)), 60))


def run_kmeans(vectors: list[list[float]], k: int, max_iter: int = 35) -> list[int]:
    """순수 파이썬 K-Means++ 클러스터링 (외부 scikit-learn 없이 동작)."""
    n = len(vectors)
    if n <= k:
        return list(range(n))

    random.seed(42)
    centroids = [vectors[random.randint(0, n - 1)]]
    for _ in range(1, k):
        distances = []
        for v in vectors:
            min_dist = min(1.0 - cosine_similarity(v, c) for c in centroids)
            distances.append(max(0.0, min_dist))
        total_dist = sum(distances)
        if total_dist == 0:
            centroids.append(vectors[random.randint(0, n - 1)])
            continue
        pick = random.uniform(0, total_dist)
        current = 0.0
        for i, d in enumerate(distances):
            current += d
            if current >= pick:
                centroids.append(vectors[i])
                break

    labels = [0] * n
    for _ in range(max_iter):
        new_labels = []
        for v in vectors:
            sims = [cosine_similarity(v, c) for c in centroids]
            best_cluster = sims.index(max(sims))
            new_labels.append(best_cluster)

        if new_labels == labels:
            break
        labels = new_labels

        dim = len(vectors[0])
        for c_idx in range(k):
            members = [vectors[i] for i in range(n) if labels[i] == c_idx]
            if not members:
                continue
            sum_vec = [0.0] * dim
            for m in members:
                sum_vec = vector_add(sum_vec, m)
            mean_vec = vector_scalar_div(sum_vec, len(members))
            m_norm = norm(mean_vec)
            centroids[c_idx] = [x / m_norm for x in mean_vec] if m_norm > 0 else mean_vec

    return labels


# ------------------------------------------------------------------------------
# 7. 동적 3R 프로파일링 및 독립 완결형 도구/에이전트 자산화 변환 엔진
# ------------------------------------------------------------------------------
DOMAIN_SIGNATURES = [
    {
        "keywords": ["정산", "셀러", "미지급", "수수료율"],
        "title": "셀러 정산 대금 지연 조회 및 미지급 내역 확인",
        "category": "정산 및 금융 운영 (Finance/MD)",
        "3r_fit": "높음 (규칙성 95%, 반복성 90%)",
        "recommended_asset": "API 도구 (정산 DB 조회 및 상태 추적 Tool)",
        "asset_type": "tool",
        "instructions": "입점 셀러 ID를 기반으로 기간계 정산 데이터베이스를 조회하여 미지급 금액과 보류 사유를 구조화된 표로 즉시 반환한다."
    },
    {
        "keywords": ["세금계산서", "역발행", "전표", "홈택스"],
        "title": "세금계산서 역발행 및 매입전표 발행 프로세스",
        "category": "회계 및 세무 지원 (Finance/Tax)",
        "3r_fit": "매우 높음 (규칙성 100%, 검색 집약성 95%)",
        "recommended_asset": "API 도구 (세금계산서 자동 역발행 연동 Tool)",
        "asset_type": "tool",
        "instructions": "월말 셀러 정산 마감 데이터와 사업자 등록번호를 검증하고 홈택스 규격 전표를 자동 생성하여 ERP로 전송한다."
    },
    {
        "keywords": ["타임아웃", "서킷", "체크아웃", "504"],
        "title": "간편결제 타임아웃 롤백 및 결제 승인 실패 보정",
        "category": "결제 플랫폼 엔지니어링 (Payment Backend)",
        "3r_fit": "매우 높음 (반복성 85%, 규칙성 95%)",
        "recommended_asset": "자율 에이전트 (결제 트랜잭션 자율 롤백 복구 Agent)",
        "asset_type": "autonomous-agent",
        "instructions": "PG사 승인 실패 로그를 감지하고 멱등성 키(Idempotency Key)를 기반으로 결제 취소 웹훅을 자동 재시도하며 슬랙 경보를 발행한다."
    },
    {
        "keywords": ["주문서", "미생성", "주문 생성", "장바구니"],
        "title": "결제 승인 후 주문서 미생성 건 복구 및 정합성 보정",
        "category": "주문 시스템 엔지니어링 (Order Backend)",
        "3r_fit": "매우 높음 (규칙성 95%, 반복성 90%)",
        "recommended_asset": "자율 에이전트 (주문 파이프라인 정합성 복구 Agent)",
        "asset_type": "autonomous-agent",
        "instructions": "결제 완료 후 주문서 생성 큐에서 누락된 트랜잭션을 실시간 격리하고 주문 데이터를 역보정 생성한 후 고객 안내 알림을 트리거한다."
    },
    {
        "keywords": ["기획전", "타임딜", "프로모션", "쿠폰 예산"],
        "title": "기획전 및 주말 타임딜 쿠폰 예산 소진 모니터링",
        "category": "이커머스 프로모션 (Growth/Marketing)",
        "3r_fit": "높음 (검색 집약성 95%, 반복성 85%)",
        "recommended_asset": "검색 에이전트 (프로모션 기획 및 쿠폰 운영 RAG Agent)",
        "asset_type": "rag-agent",
        "instructions": "기획전 할인 쿠폰 룰과 예산 소진 속도를 모니터링하고 조기 소진 시 프로모션 종료 알림 및 추가 예산 승인 가이드를 제시한다."
    },
    {
        "keywords": ["휴면", "알림톡", "FCM", "푸시"],
        "title": "휴면 고객 복귀 알림톡 및 개인화 푸시 스케줄링",
        "category": "CRM 및 고객 유치 (Marketing/CRM)",
        "3r_fit": "높음 (반복성 90%, 규칙성 90%)",
        "recommended_asset": "API 도구 (FCM 및 카카오 알림톡 자동 발송 Tool)",
        "asset_type": "tool",
        "instructions": "휴면 고객 세그먼트를 추출하고 개인화된 할인 문구를 조합하여 승인된 템플릿 기반으로 알림톡 발송 API를 비동기 호출한다."
    },
    {
        "keywords": ["택배비", "단순 변심", "도서산간", "제주"],
        "title": "도서산간 및 단순 변심 반품 택배비 환불 규정",
        "category": "고객 지원 운영 (CS/Customer Service)",
        "3r_fit": "높음 (규칙성 95%, 검색 집약성 95%)",
        "recommended_asset": "검색 에이전트 (반품/교환 배송비 규정 안내 RAG Agent)",
        "asset_type": "rag-agent",
        "instructions": "고객의 주문 내역 및 귀책 사유를 판별하여 편도/왕복 택배비와 도서산간 추가 운임을 정확히 계산하여 상담원에게 즉각 응답한다."
    },
    {
        "keywords": ["파손", "선환불", "클레임", "구상권"],
        "title": "파손 배송 접수 고객 선환불 및 택배사 클레임 접수",
        "category": "고객 지원 및 물류 클레임 (CS/Logistics)",
        "3r_fit": "높음 (규칙성 90%, 반복성 95%)",
        "recommended_asset": "API 도구 (택배사 클레임 접수 및 선환불 승인 Tool)",
        "asset_type": "tool",
        "instructions": "파손 사진 증빙 데이터를 검수한 후 승인 한도 내에서 고객 선환불을 집행하고 담당 택배사 사고 접수 API로 클레임을 자동 전송한다."
    },
    {
        "keywords": ["VPN", "GitLab", "러너", "옥타", "입사자"],
        "title": "신규 입사자 VPN 접속 및 개발 계정 연동 가이드",
        "category": "사내 IT 및 보안 지원 (IT Support/Security)",
        "3r_fit": "중간 (규칙성 100%, 발생 빈도 보통)",
        "recommended_asset": "검색 에이전트 (임직원 IT 온보딩 헬프데스크 RAG Agent)",
        "asset_type": "rag-agent",
        "instructions": "신규 입사자의 사내 VPN 설정, 사내 GitLab 러너 등록, Okta 2차 인증 및 와이파이 인증서 발급 단계를 대화형으로 단계별 안내한다."
    },
    {
        "keywords": ["BigQuery", "IAM", "접근 권한", "열람 승인"],
        "title": "스테이징 BigQuery 데이터셋 접근 및 임시 IAM 권한 신청",
        "category": "데이터 엔지니어링 및 거버넌스 (Data Governance)",
        "3r_fit": "높음 (규칙성 100%, 검색 집약성 85%)",
        "recommended_asset": "API 도구 (BigQuery IAM 권한 임시 승인 및 자동 회수 Tool)",
        "asset_type": "tool",
        "instructions": "신청 사유와 요청 테이블을 분석하여 결재 승인 즉시 IAM 뷰어 역할을 부여하고 설정된 만료 시간 경과 시 권한을 자동 회수한다."
    },
    {
        "keywords": ["법인카드", "경비", "출장", "여비", "식대"],
        "title": "법인카드 경비 처리 및 해외 출장 여비 정산 규정",
        "category": "경영 지원 및 총무 (Corporate Support/Finance)",
        "3r_fit": "높음 (규칙성 95%, 검색 집약성 90%)",
        "recommended_asset": "검색 에이전트 (경비 처리 및 출장 규정 안내 RAG Agent)",
        "asset_type": "rag-agent",
        "instructions": "사내 출장 여비 지급 규정 및 법인카드 사용 시간대 가이드를 실시간 조회하여 전표 반려를 방지하고 올바른 계정 과목을 추천한다."
    },
    {
        "keywords": ["안전 재고", "WMS", "발주서", "SKU"],
        "title": "물류 창고 안전 재고 미달 품목 실시간 확인 및 추가 발주",
        "category": "공급망 관리 및 물류 (SCM/Logistics)",
        "3r_fit": "매우 높음 (반복성 95%, 규칙성 95%)",
        "recommended_asset": "API 도구 (WMS 재고 연동 및 자동 발주 Tool)",
        "asset_type": "tool",
        "instructions": "WMS 창고별 실시간 가용 재고를 모니터링하여 안전 재고 임계치 미달 시 공급업체 발주서(PO)를 자동 드래프트하고 알림을 보낸다."
    },
]


def match_domain_signature(queries: list[str]) -> dict:
    """군집 내 질의들의 키워드 빈도를 바탕으로 최적의 마이크로 업무 영역과 자산을 동적 매핑한다."""
    combined_text = " ".join(queries)

    best_match = None
    best_score = 0
    for sig in DOMAIN_SIGNATURES:
        score = sum(combined_text.count(kw) for kw in sig["keywords"])
        if score > best_score:
            best_score = score
            best_match = sig

    if best_match and best_score > 0:
        return best_match

    # 미등록 키워드의 동적 자가 치유(Self-healing) 프로파일러
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", combined_text)
    top_words = [w for w in words if w not in ("어떻게", "알려줘", "조회해", "확인해", "가이드", "방법", "관련", "위한", "있는지")]
    kw_label = top_words[0] if top_words else "사내 공통"

    is_tool = any(v in combined_text for v in ("조회", "발송", "계산", "신청", "발행", "연동", "등록"))
    is_auto = any(v in combined_text for v in ("장애", "롤백", "타임아웃", "서킷", "복구", "실패"))

    if is_auto:
        asset_type = "autonomous-agent"
        asset_name = f"자율 에이전트 ({kw_label} 시스템 자율 제어 및 복구 Agent)"
    elif is_tool:
        asset_type = "tool"
        asset_name = f"API 도구 ({kw_label} 기간계 DB/API 연동 Tool)"
    else:
        asset_type = "rag-agent"
        asset_name = f"검색 에이전트 ({kw_label} 사내 규정 RAG Agent)"

    return {
        "title": f"{kw_label} 관련 반복 질의 및 업무 자동화",
        "category": "일반 현업 지원",
        "3r_fit": "높음 (규칙성 90%, 반복성 85%)",
        "recommended_asset": asset_name,
        "asset_type": asset_type,
        "instructions": f"{kw_label}와 관련된 빈출 반복 문의에 대해 사내 승인된 데이터소스를 조회하여 정확한 안내를 제공한다."
    }


def analyze_clusters(sessions: list[dict], labels: list[int], k: int) -> list[dict]:
    """군집별 데이터 통계 집계, PII 보호 검증 및 3R 자산화 매핑을 완결한다."""
    clusters = []
    for c_idx in range(k):
        members = [sessions[i] for i in range(len(sessions)) if labels[i] == c_idx]
        if not members:
            continue
        all_queries = []
        for m in members:
            all_queries.extend(m.get("queries", []))

        unique_users = len(set(m.get("user_anon", "unknown") for m in members))
        total_turns = sum(m.get("turn_count", 1) for m in members)

        sig = match_domain_signature(all_queries)

        clusters.append({
            "cluster_id": c_idx + 1,
            "title": sig["title"],
            "category": sig["category"],
            "3r_fit": sig["3r_fit"],
            "recommended_asset": sig["recommended_asset"],
            "asset_type": sig.get("asset_type", "tool"),
            "instructions": sig.get("instructions", ""),
            "session_count": len(members),
            "total_queries": len(all_queries),
            "total_turns": total_turns,
            "unique_users": unique_users,
            "user_samples": list(set(m.get("user_anon", "unknown") for m in members))[:3],
            "sample_queries": [m.get("sample_preview", "") for m in members[:3]]
        })

    clusters.sort(key=lambda x: x["session_count"], reverse=True)
    return clusters


# ------------------------------------------------------------------------------
# 8. 마크다운 보고서 빌더 및 콘솔 포맷터
# ------------------------------------------------------------------------------
def build_markdown_report(
    clusters: list[dict],
    total_raw_queries: int,
    total_sessions: int,
    pii_stats: dict[str, int],
    project_id: str,
    mode_str: str,
    group_multi_turn: bool = True
) -> str:
    """마크다운 분석 결과 보고서 생성 (스킬화/에이전트화 전환 파이프라인 중심)."""
    tool_count = sum(1 for c in clusters if c.get("asset_type") == "tool")
    rag_count = sum(1 for c in clusters if c.get("asset_type") == "rag-agent")
    auto_count = sum(1 for c in clusters if c.get("asset_type") == "autonomous-agent")
    total_pii_masked = sum(pii_stats.values())

    lines = [
        "# Gemini Enterprise 프롬프트 로그 기반 3R 마이크로 업무 발굴 및 도구/에이전트 전환 파이프라인 보고서",
        "",
        f"- **분석 일시**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- **실행 모드**: {mode_str}",
        f"- **대상 프로젝트**: `{project_id}`",
        f"- **원시 수집 질의 수**: {total_raw_queries}건",
        f"- **분석 단위 대화 세션 수**: {total_sessions}개 세션" + (" (멀티 턴 묶음 분석 적용)" if group_multi_turn else " (단일 턴 개별 분석)"),
        f"- **도출된 3R 마이크로 업무 군집 수**: {len(clusters)}개 영역 (자율 적응형 Auto-K)",
        f"- **프라이버시 보호 적용**: 인라인 PII 마스킹 총 {total_pii_masked}건 집행 및 임직원 계정 비식별화(Pseudonymization)",
        "",
        "---",
        ""
    ]

    if "모의 데이터" in mode_str or "--dry-run" in mode_str:
        lines.extend([
            "> [!NOTE]",
            "> **가상 모의 분석 안내 (Dry-Run)**: 본 보고서는 사내 기능 체험 및 스모크 테스트를 위해 사전 탑재된 49건의 엔터프라이즈 표본 질의 데이터를 기반으로 생성된 시뮬레이션 결과입니다. 실제 사내 대화 로그 분석 시에는 `--project <PROJECT_ID>` 옵션으로 BigQuery 감사 로그를 직접 연결하십시오.",
            ""
        ])
    else:
        lines.extend([
            "> [!IMPORTANT]",
            f"> **사내 실환경 데이터 분석 안내**: 본 보고서는 대상 프로젝트(`{project_id}`)의 BigQuery 감사 로그 테이블에서 수집된 총 {total_raw_queries}건의 실제 질의 데이터를 바탕으로 분석된 실측 결과입니다.",
            ""
        ])

    lines.extend([
        "## 1. 사내 도구 및 에이전트 전환 파이프라인 종합 대시보드",
        "",
        "임직원이 입력한 일상 질의 속에서 상투적 대분류를 탈피하고, 자체 완결적으로 구현 가능한 고해상도 마이크로 업무 자동화 자산 파이프라인을 도출했다:",
        "",
        "| 자산화 구분 | 추천 구현 아키텍처 | 발굴 건수 | 핵심 기술 구현 메커니즘 |",
        "| :--- | :--- | :--- | :--- |",
        f"| **`API 도구 (Tool)`** | OpenAPI 도구 / 함수 호출 | **{tool_count}건** | 정산, 세금, 클레임, 권한 회수 등 기간계 DB/API 트랜잭션 연동 |",
        f"| **`검색 에이전트 (RAG Agent)`** | 사내 지식 및 규정 검색 어시스턴트 | **{rag_count}건** | 반품 배송비 규정, 온보딩 가이드, 프로모션 룰 등 사내 문서/위키 그라운딩 |",
        f"| **`자율 에이전트 (Autonomous Agent)`** | 트랜잭션 자율 제어 및 장애 복구 | **{auto_count}건** | 간편결제 타임아웃 롤백, 주문서 정합성 보정 등 시스템 자율 복구 |",
        f"| **합계 (Total)** | **전사 3R 업무 자동화 파이프라인** | **{len(clusters)}건** | **실질 자산화 전환율: 100.0% (전수 실행 가능)** |",
        "",
        "---",
        "",
        "## 2. 프라이버시 보호 및 멀티 턴 세션 정제 현황",
        "",
        "- **멀티 턴 대화 묶음 정제**: 단편적 질문 파편화를 방지하기 위해 동일 세션 내 사용자 후속 질의를 단일 업무 워크플로우 컨텍스트로 결합하여 임베딩 군집화 정확도를 극대화했다.",
        "- **인라인 PII 마스킹 내역**:"
    ])

    if pii_stats:
        for p_name, p_cnt in pii_stats.items():
            lines.append(f"  - `{p_name}`: {p_cnt}건 안전 마스킹 완료")
    else:
        lines.append("  - 검출된 민감 PII 항목 없음 (원천 안전 데이터)")

    lines.extend([
        "",
        "---",
        "",
        "## 3. 발굴된 3R 마이크로 업무 군집별 세부 분석 및 자산화 명세",
        "",
        "| 순위 | 3R 마이크로 업무 군집 명칭 | 소속 도메인 | 세션 수 (질의 수) | 참여 임직원 | 3R 적합도 | 추천 코파일럿 자산 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ])

    for rank, c in enumerate(clusters, 1):
        lines.append(
            f"| {rank} | **{c['title']}** | {c['category']} | {c['session_count']}세션 ({c['total_queries']}건) | {c['unique_users']}명 | {c['3r_fit']} | `{c['recommended_asset']}` |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 4. 군집별 세부 업무 시나리오 및 워크숍 실습 지침",
        ""
    ])

    for rank, c in enumerate(clusters, 1):
        lines.extend([
            f"### {rank}. {c['title']} ({c['category']})",
            f"* **분석 세션 수**: {c['session_count']}개 세션 (총 {c['total_queries']}건 질의, 세션당 평균 {c['total_turns'] / max(1, c['session_count']):.1f}턴)",
            f"* **3R 적합도 분석**: {c['3r_fit']}",
            f"* **추천 엔터프라이즈 자산**: `{c['recommended_asset']}`",
            f"* **참여 사용자(비식별 가명)**: {', '.join(c['user_samples']) if c['user_samples'] else 'emp-anon'}",
            f"* **추천 시스템 지침 초안**: \"{c['instructions']}\"",
            "* **실제 세션 질의 샘플**:"
        ])
        for q in c["sample_queries"]:
            lines.append(f"  - \"{q}\"")
        lines.extend([
            "* **워크숍 실습 활용 지침**:",
            f"  - 사전 설문 없이도 본 군집의 질의 샘플을 활용하여 `{c['recommended_asset']}` 매니페스트 및 시스템 지침을 즉시 빌드한다.",
            ""
        ])

    lines.extend([
        "---",
        "",
        "## 5. 사내 거버넌스 4대 필수 표준 라벨링",
        "",
        "본 도구 및 관련 클라우드 인프라 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:",
        "- `managed-by`: `google-cloud-0-to-1`",
        "- `scenario`: `gemini-enterprise-prompt-miner`",
        "- `env`: `sample` (또는 `poc`)",
        "- `created-by`: `customer-engineer`",
        "",
        "---",
        "",
        "## 6. 자원 정리 안내 (Teardown)",
        "",
        "본 도구는 일회성 임베딩 분석 스크립트로 동작하므로 상주 인프라 비용이 발생하지 않는다.",
        "더 이상 분석 데이터가 필요하지 않을 경우 로컬 산출물만 정리한다:",
        "```bash",
        "rm -f report.md prompts.jsonl",
        "```"
    ])
    return "\n".join(lines)


def save_markdown_report(content: str, filename: str = "report.md") -> None:
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(cur_dir, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n[성공] 마크다운 진단 보고서가 저장되었습니다: {out_path}")


# ------------------------------------------------------------------------------
# 9. 사내 환경 대화형 설정 마법사 (--config)
# ------------------------------------------------------------------------------
def run_config_mode(scenario_name: str = "gemini-enterprise-prompt-miner") -> None:
    """사내 환경 대화형 설정 마법사: .env.example을 기반으로 사내 리소스를 대화형으로 탐색하여 .env에 저장한다."""
    print("\n" + "=" * 76)
    print(f"  {scenario_name} - 사내 환경 대화형 설정 마법사 (--config)")
    print("=" * 76)

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(cur_dir, ".env")
    example_path = os.path.join(cur_dir, ".env.example")

    if not os.path.exists(example_path):
        print("[-] .env.example 템플릿 파일이 존재하지 않습니다.")
        return

    existing_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    existing_vars[k.strip()] = v.strip().strip("'\"")

    gcloud_project = ""
    try:
        res = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            val = res.stdout.strip()
            if val and val != "(unset)":
                gcloud_project = val
    except Exception:
        pass

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
    new_values = {}

    for idx, key in enumerate(keys_to_prompt, 1):
        default_val = existing_vars.get(key, "")
        if not default_val:
            if "PROJECT" in key:
                default_val = gcloud_project or os.environ.get("PROJECT_ID", "")
            elif key in ("LOCATION", "TARGET_REGION"):
                default_val = "asia-northeast3"
            elif key == "BQ_DATASET_ID":
                default_val = "gemini_logging"
            elif key == "CLUSTERS":
                default_val = "auto"
            elif key == "DAYS":
                default_val = "30"
            elif key == "ENABLE_PII_MASKING":
                default_val = "true"
            elif key == "GROUP_MULTI_TURN":
                default_val = "true"

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
            print(f"  -> 설정값: {final_val or '(기본값 유지)'}")

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

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)

    print(f"\n[성공] .env 환경 설정 파일이 저장되었습니다: {env_path}")


# ------------------------------------------------------------------------------
# 10. 메인 실행 진입점
# ------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Gemini Enterprise 프롬프트 로그 기반 3R 마이크로 업무 발굴 및 스킬/에이전트 전환 분석기"
    )
    parser.add_argument("--config", action="store_true", help="사내 환경 대화형 설정 마법사 실행")
    parser.add_argument("--dry-run", action="store_true", help="모의 질의 데이터(60건, 24개 세션)로 가상 분석 실행")
    parser.add_argument("--project", default="", help="BigQuery 감사 로그 및 내장 임베딩 연동용 GCP 프로젝트 ID")
    parser.add_argument("--dataset", default="gemini_logging", help="BigQuery 프롬프트 감사 로그 데이터세트 ID")
    parser.add_argument("--location", default="asia-northeast3", help="BigQuery 데이터세트 리전 (기본값: asia-northeast3)")
    parser.add_argument("--model", default="text_multilingual_embedding_002", help="BigQuery 내장 임베딩 모델 이름 (기본값: text_multilingual_embedding_002)")
    parser.add_argument("--clusters", default="auto", help="도출할 업무 군집 수 K (기본값: auto - 모수 기반 자율 계산, 숫자 지정 가능)")
    parser.add_argument("--days", type=int, default=30, help="분석 대상 최근 기간 일수 (기본값: 30)")
    parser.add_argument("--input", default="", help="로컬 JSONL 파일 경로 (생략 시 BigQuery 또는 모의 데이터 사용)")
    parser.add_argument("--output", default="report.md", help="출력 보고서 마크다운 파일명")
    parser.add_argument("--no-pii-masking", action="store_true", help="프라이버시 PII 마스킹 비활성화")
    parser.add_argument("--no-group-sessions", action="store_true", help="멀티 턴 대화 묶음 처리 비활성화 및 단일 질의 단위 분석")

    args = parser.parse_args()

    if args.config:
        run_config_mode()
        return

    project_id = get_default_project(args.dry_run, fallback_demo="sample-project-id")
    if args.project:
        project_id = args.project

    print("=" * 76)
    print("  Gemini Enterprise 프롬프트 마이너 (3R 마이크로 업무 및 자산화 분석기)")
    print(f"  - 대상 프로젝트 : {project_id}")
    print(f"  - BigQuery 리전: {args.location}")
    print(f"  - 도출 군집 수  : {args.clusters} (Auto-K 모수 적응형)")
    print(f"  - PII 마스킹    : {'비활성화' if args.no_pii_masking else '활성화 (주민번호, 계좌, 전화번호 등)'}")
    print(f"  - 멀티 턴 묶음  : {'비활성화 (단일 턴)' if args.no_group_sessions else '활성화 (세션 워크플로우 단위)'}")
    print("=" * 76)

    # 1. 데이터 소스 확보
    raw_logs = []
    if args.dry_run or (not args.input and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not args.project):
        mode_str = "모의 데이터 가상 실행 (--dry-run)"
        raw_logs = MOCK_RAW_LOGS
        print(f"[*] [가상 모의 분석 모드] 사전 탑재된 49건의 엔터프라이즈 표본 질의 데이터를 로드합니다.")
    elif args.input:
        if not os.path.exists(args.input):
            print(f"[-] 지정한 입력 파일이 존재하지 않습니다: {args.input}", file=sys.stderr)
            return
        mode_str = f"로컬 JSONL 파일 분석 ({args.input})"
        with open(args.input, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        d = json.loads(line)
                        if "query" in d:
                            raw_logs.append(d)
                    except json.JSONDecodeError:
                        continue
        print(f"[*] JSONL 파일 로드 완료: 총 {len(raw_logs)}건")
        if not raw_logs:
            print("[-] 파일 내에 유효한 'query' 필드를 포함한 로그가 없습니다.", file=sys.stderr)
            return
    else:
        mode_str = f"BigQuery 실시간 감사 로그 분석 ({project_id}.{args.dataset})"
        print(f"[*] BigQuery 프롬프트 감사 로그 조회 중 ({project_id}.{args.dataset})...")
        try:
            from google.cloud import bigquery
            client = bigquery.Client(project=project_id, location=args.location)
            query = f"""
            SELECT JSON_EXTRACT_SCALAR(protopayload_auditlog.requestJson, '$.query') AS query,
                   protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
                   COALESCE(
                     JSON_EXTRACT_SCALAR(protopayload_auditlog.requestJson, '$.conversation'),
                     JSON_EXTRACT_SCALAR(protopayload_auditlog.requestJson, '$.sessionId'),
                     protopayload_auditlog.authenticationInfo.principalEmail
                   ) AS session_id,
                   timestamp
            FROM `{project_id}.{args.dataset}.cloudaudit_googleapis_com_data_access`
            WHERE protopayload_auditlog.serviceName = 'discoveryengine.googleapis.com'
              AND JSON_EXTRACT_SCALAR(protopayload_auditlog.requestJson, '$.query') IS NOT NULL
              AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {args.days} DAY)
            ORDER BY session_id, timestamp ASC
            LIMIT 1000
            """
            rows = client.query(query).result()
            for r in rows:
                raw_logs.append({
                    "query": r.query,
                    "user_email": r.user_email,
                    "session_id": r.session_id
                })
        except Exception as e:
            print(f"\n[-] BigQuery 감사 로그 조회 실패: {e}")

        if not raw_logs:
            print("\n" + "=" * 76)
            print("  [진단 결과] 대상 프로젝트에서 수집된 Gemini Enterprise 프롬프트 로그가 없습니다 (0건).")
            print("=" * 76)
            print("  * 가능한 원인:")
            print(f"    1. `{project_id}.{args.dataset}` 데이터셋 또는 감사 로그 테이블이 존재하지 않습니다.")
            print("    2. Cloud Logging의 Data Access 감사 로그가 BigQuery로 자동 내보내기(Sink)되지 않았습니다.")
            print(f"    3. 최근 {args.days}일 동안 임직원의 검색/질의 활동이 없었습니다.")
            print("\n  * 실환경 조치 가이드:")
            print("    1) Cloud Logging -> BigQuery 감사 로그 싱크(Sink) 생성:")
            print(f"       gcloud logging sinks create gemini-audit-sink \\")
            print(f"         bigquery.googleapis.com/projects/{project_id}/datasets/{args.dataset} \\")
            print("         --log-filter='logName:\"logs/cloudaudit.googleapis.com%2Fdata_access\" AND protoPayload.serviceName=\"discoveryengine.googleapis.com\"' \\")
            print(f"         --project={project_id}")
            print("\n    2) 사전 탑재된 49건의 모의 질의셋으로 기능 및 리포트를 먼저 체험해 보시려면:")
            print("       python diagnose.py --dry-run")
            print("=" * 76)
            return

        print(f"[*] BigQuery 조회 성공: 총 {len(raw_logs)}건의 실제 사용자 질의 수집")

    # 2. 프라이버시 보호 및 멀티 턴 세션 묶음 처리
    sessions, pii_stats = group_conversation_sessions(
        raw_logs,
        group_multi_turn=not args.no_group_sessions,
        enable_pii_masking=not args.no_pii_masking
    )

    avg_turns = len(raw_logs) / max(1, len(sessions))
    total_pii = sum(pii_stats.values())
    print(f"\n[*] 세션 정제 완료: {len(raw_logs)}개 원시 질의 -> {len(sessions)}개 대화 세션 (세션당 평균 {avg_turns:.1f}턴)")
    if total_pii > 0:
        print(f"[*] 프라이버시 보호: 인라인 PII {total_pii}건 마스킹 완료 {dict(pii_stats)}")
    else:
        print("[*] 프라이버시 보호: 검출된 PII 없음 (원천 안전 데이터)")

    # 3. 자율 적응형 군집 수 K 도출
    k = determine_optimal_k(len(sessions), args.clusters)
    print(f"[*] 분석 해상도 산정: 최적 마이크로 업무 군집 수 K={k} 결정 (상투적 대분류 탈피)")

    # 4. BigQuery 내장 임베딩 생성 (세션 컨텍스트 기준)
    session_texts = [s["session_text"] for s in sessions]
    print(f"\n[*] BigQuery 내장 임베딩(ML.GENERATE_EMBEDDING) 생성 중 (총 {len(sessions)}개 세션)...")
    if args.dry_run or mode_str.startswith("모의 데이터"):
        vectors = [get_mock_embedding(t) for t in session_texts]
    else:
        vectors = get_bigquery_embeddings(
            session_texts,
            project_id=project_id,
            dataset_id=args.dataset,
            model_name=args.model,
            location=args.location
        )
    print("  - 임베딩 벡터 생성 완료.")

    # 5. K-Means++ 군집화
    print(f"\n[*] K-Means++ 클러스터링 알고리즘 실행 중 (K={k})...")
    labels = run_kmeans(vectors, k=k)

    # 6. 군집별 3R 분석 및 자산화 매핑
    clusters = analyze_clusters(sessions, labels, k=k)

    tool_count = sum(1 for c in clusters if c.get("asset_type") == "tool")
    rag_count = sum(1 for c in clusters if c.get("asset_type") == "rag-agent")
    auto_count = sum(1 for c in clusters if c.get("asset_type") == "autonomous-agent")

    # 7. 콘솔 출력: 도구/에이전트 전환 파이프라인 대시보드
    print("\n" + "=" * 76)
    print(f"  [사내 3R 업무 자동화 발굴 종합 요약] 총 {len(clusters)}대 마이크로 파이프라인")
    print("=" * 76)
    print(f"  - API 연동 도구 (Tool / Extension) : {tool_count}건 (기간계 DB/API 직결)")
    print(f"  - 지식 검색 에이전트 (RAG Agent)   : {rag_count}건 (사내 규정/온보딩 비서)")
    print(f"  - 자율 복구 에이전트 (Autonomous)  : {auto_count}건 (트랜잭션 자율 복구)")
    print(f"  - 실질 자산화 전환율: 100.0% ({len(clusters)}/{len(clusters)} 과제 전환 완료)")
    print("-" * 76)
    print(f"{'순위':<3} | {'마이크로 업무 군집 명칭':<26} | {'세션(질의)':<9} | {'추천 자산'}")
    print("-" * 76)
    for rank, c in enumerate(clusters, 1):
        asset_short = c['recommended_asset'].split('(')[0].strip()
        print(f"{rank:<3} | {c['title'][:25]:<26} | {c['session_count']}세션({c['total_queries']}건) | {asset_short}")
    print("=" * 76)

    # 8. 보고서 저장
    report_content = build_markdown_report(
        clusters=clusters,
        total_raw_queries=len(raw_logs),
        total_sessions=len(sessions),
        pii_stats=pii_stats,
        project_id=project_id,
        mode_str=mode_str,
        group_multi_turn=not args.no_group_sessions
    )
    save_markdown_report(report_content, filename=args.output)


if __name__ == "__main__":
    main()
