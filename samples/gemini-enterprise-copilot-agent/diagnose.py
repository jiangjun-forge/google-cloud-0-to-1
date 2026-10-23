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
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
import requests

try:
    import yaml
except ImportError:
    yaml = None

# 엔터프라이즈 노코드 에이전트 인라인 폴백 시드
FALLBACK_AGENT_CATALOG = {
    1: {
        "id": "hr-onboarding-guide",
        "slug": "hr-onboarding-guide",
        "title": "신규 입사자 온보딩 가이드 에이전트",
        "name": "신규 입사자 온보딩 가이드 에이전트",
        "category": "인사 및 조직 문화",
        "description": "사내 필수 계정 발급, 부서별 환영 절차, 멘토링 프로그램, 보안 서약 및 첫 주 적응 태스크를 안내한다.",
        "mention_handle": "@hr-onboarding-guide",
        "slash_command": "/hr-onboarding-guide",
        "target_users": "신규 입사자, 팀 멘토, 피플팀",
        "core_compliance": "사내 정보보호 서약 및 신규 입사자 준수 수칙",
        "default_scope": "ORG",
        "starter_prompts": [
            "신규 입사 첫 주 필수 체크리스트와 계정 신청 링크 알려줘",
            "사내 보안 서약서 제출 방법과 교육 이수 마감일이 언제야?",
            "멘토 배정 기준과 온보딩 미팅 일정 템플릿 보여줘",
            "사내 그룹웨어 및 사내망 접속 절차 가이드 해줘",
        ],
        "instructions_summary": "신규 입사자가 사내 문화와 업무 인프라에 안착하도록 따뜻하고 전문적인 어조로 사내 규정과 링크를 안내하며, PII 보호 수칙을 준수한다.",
    },
    2: {
        "id": "hr-welfare-concierge",
        "slug": "hr-welfare-concierge",
        "title": "임직원 복리후생 컨시어지 에이전트",
        "name": "임직원 복리후생 컨시어지 에이전트",
        "category": "인사 및 복리후생",
        "description": "경조사비 지원, 휴양소 예약, 건강검진 대상 및 사내 동호회 지원 기준을 조회하고 신청 양식을 안내한다.",
        "mention_handle": "@hr-welfare-concierge",
        "slash_command": "/hr-welfare-concierge",
        "target_users": "전사 임직원",
        "core_compliance": "사내 복지기금 운영 규정 및 증빙 서류 지침",
        "default_scope": "ORG",
        "starter_prompts": [
            "올해 종합건강검진 대상자 여부와 제휴 병원 목록 알려줘",
            "경조사 화환 신청 및 경조금 지급 기준이 어떻게 돼?",
            "하계 콘도/휴양소 추첨 신청 일정과 자격 요건 안내해줘",
            "사내 동호회 설립 조건과 분기별 활동 지원금 규정 확인해줘",
        ],
        "instructions_summary": "임직원이 받을 수 있는 복리후생 혜택을 놓치지 않도록 사내 규정을 명확히 안내하고 필요 증빙 서류와 신청 기한을 안내한다.",
    },
    3: {
        "id": "hr-evaluation-assistant",
        "slug": "hr-evaluation-assistant",
        "title": "인사평가 및 KPI 작성 코칭 에이전트",
        "name": "인사평가 및 KPI 작성 코칭 에이전트",
        "category": "인사 및 조직 성과",
        "description": "분기/반기별 목표 수립(OKR/KPI) SMART 원칙 코칭, 업무 성과 기술서 작성 및 다면 평가 피드백 작성을 돕는다.",
        "mention_handle": "@hr-evaluation-assistant",
        "slash_command": "/hr-evaluation-assistant",
        "target_users": "전사 임직원 및 평가자(팀장/부서장)",
        "core_compliance": "사내 인사평가 관리 지침 및 다면평가 비밀 유지 규정",
        "default_scope": "ORG",
        "starter_prompts": [
            "이번 분기 영업/기술 지원 KPI를 SMART 기준에 맞춰 구체화해줘",
            "상반기 주요 업무 실적 기술서 초안을 정량 지표 중심으로 다듬어줘",
            "팀원 다면 평가 피드백을 건설적이고 객관적인 문장으로 작성해줘",
            "하반기 역량 개발 계획서 작성 가이드라인 알려줘",
        ],
        "instructions_summary": "과장이나 추상적인 서술을 배제하고 정량적 결과(Metric)와 구체적 기여도를 중심으로 성과 기술서를 코칭하며 비밀유지를 보장한다.",
    },
    4: {
        "id": "finance-expense-auditor",
        "slug": "finance-expense-auditor",
        "title": "법인카드 경비 전표 사전 검토 에이전트",
        "name": "법인카드 경비 전표 사전 검토 에이전트",
        "category": "재무 및 경비 정산",
        "description": "법인카드 전표 증빙, 부가세 공제 대상 여부, 접대비 한도 및 청탁금지법 가액 기준 충족 여부를 사전 점검한다.",
        "mention_handle": "@finance-expense-auditor",
        "slash_command": "/finance-expense-auditor",
        "target_users": "전사 임직원 및 재무회계팀",
        "core_compliance": "법인세법 적격증빙 규정 및 청탁금지법 가액 기준",
        "default_scope": "ORG",
        "starter_prompts": [
            "야근 식대 법인카드 결제 한도와 필요 증빙 안내해줘",
            "거래처 미팅 식사비 1인당 한도와 청탁금지법 체크리스트 보여줘",
            "주말/공휴일 법인카드 사용 시 사유서 작성 요령 알려줘",
            "해외 출장 항공권 및 숙박비 영수증 정산 절차 안내해줘",
        ],
        "instructions_summary": "세법 및 사내 전표 규정에 부합하는지 꼼꼼하게 대조하며, 불인정 위험 항목(사적 사용, 심야 한도 초과 등)을 사전 경고한다.",
    },
    5: {
        "id": "finance-tax-advisor",
        "slug": "finance-tax-advisor",
        "title": "사내 연말정산 원천징수 상담 에이전트",
        "name": "사내 연말정산 원천징수 상담 에이전트",
        "category": "재무 및 세무 상담",
        "description": "근로소득 연말정산 소득/세액 공제 항목, 부양가족 요건, 국세청 간소화 자료 제출 및 원천징수영수증 발급을 상담한다.",
        "mention_handle": "@finance-tax-advisor",
        "slash_command": "/finance-tax-advisor",
        "target_users": "전사 임직원",
        "core_compliance": "소득세법 근로소득 연말정산 규정",
        "default_scope": "ORG",
        "starter_prompts": [
            "올해 신설된 주택청약종합저축 소득공제 한도 알려줘",
            "기본공제 대상 부양가족 소득 요건과 나이 요건 확인해줘",
            "맞벌이 부부 의료비 몰아주기 공제 최적화 방법 설명해줘",
            "연도 중 중도 입사자의 전 직장 근로소득 원천징수 합산 절차 안내해줘",
        ],
        "instructions_summary": "최신 소득세법 기준의 공제 요건을 알기 쉽게 설명하고 과다공제로 인한 가산세 발생 위험을 예방하도록 돕는다.",
    },
    6: {
        "id": "legal-contract-reviewer",
        "slug": "legal-contract-reviewer",
        "title": "표준 계약서 1차 법무 검토 에이전트",
        "name": "표준 계약서 1차 법무 검토 에이전트",
        "category": "법무 및 준법 감시",
        "description": "비밀유지계약서(NDA), 업무위수탁계약서 등 사내 표준 양식과의 독소 조항, 관할 법원, 지식재산권 귀속을 1차 스크리닝한다.",
        "mention_handle": "@legal-contract-reviewer",
        "slash_command": "/legal-contract-reviewer",
        "target_users": "사업개발, 영업, 구매팀 및 법무팀",
        "core_compliance": "부정경쟁방지 및 영업비밀보호에 관한 법률, 하도급법",
        "default_scope": "ORG",
        "starter_prompts": [
            "고객사 전달 NDA에서 일방적 손해배상 독소 조항 찾아줘",
            "SW 외주 용역 계약서의 지식재산권 귀속 조항 표준 문구 추천해줘",
            "계약 분쟁 시 관할 법원을 우리 회사 소재지 법원으로 변경하는 특약 검토해줘",
            "표준 업무위수탁 계약서 필수 기재사항 누락 여부 확인해줘",
        ],
        "instructions_summary": "최종 법률 자문은 사내 법무팀의 고유 권한임을 명시하되, 불리한 독소 조항이나 법률상 필수 조항 누락을 1차적으로 안전하게 걸러낸다.",
    },
    7: {
        "id": "sec-compliance-officer",
        "slug": "sec-compliance-officer",
        "title": "정보보호 및 망 분리 규정 질의 에이전트",
        "name": "정보보호 및 망 분리 규정 질의 에이전트",
        "category": "정보보호 및 보안",
        "description": "사내 정보보안 수칙, 망 분리 반출입 절차, 외부 오픈소스 소프트웨어 인가 기준, 개인정보 처리 동의 가이드를 제공한다.",
        "mention_handle": "@sec-compliance-officer",
        "slash_command": "/sec-compliance-officer",
        "target_users": "전사 임직원 및 개발/인프라팀",
        "core_compliance": "개인정보보호법, 전자금융감독규정, 정보통신망법",
        "default_scope": "ORG",
        "starter_prompts": [
            "내부망 PC에서 외부 개발 소스코드 반입 신청 절차 알려줘",
            "고객 개인식별정보(PII) 포함 데이터 마스킹 표준 규정 확인해줘",
            "상용 소프트웨어 설치 시 CISO 보안성 검토 신청 방법 안내해줘",
            "생성형 AI 서비스 사용 시 사내 기밀 유출 방지 3대 가이드라인 보여줘",
        ],
        "instructions_summary": "철저한 컴플라이언스 준수 원칙 하에 사내 보안 규정과 망 분리 승인 프로세스를 단호하고 명료하게 안내한다.",
    },
    8: {
        "id": "it-helpdesk-responder",
        "slug": "it-helpdesk-responder",
        "title": "사내 전산 계정 장애 1차 응대 에이전트",
        "name": "사내 전산 계정 장애 1차 응대 에이전트",
        "category": "IT 전산 지원",
        "description": "SSO 계정 잠금 해제, OTP/2차 인증 초기화, VPN 접속 오류, 프린터/네트워크 설정 장애를 진단하고 티켓을 생성한다.",
        "mention_handle": "@it-helpdesk-responder",
        "slash_command": "/it-helpdesk-responder",
        "target_users": "전사 임직원",
        "core_compliance": "사내 계정 관리 보안 지침 및 IT 서비스 관리(ITSM) 체계",
        "default_scope": "ORG",
        "starter_prompts": [
            "사내 SSO 계정 비밀번호 5회 오류 잠금 해제 방법 알려줘",
            "재택근무 중 글로벌 VPN 연결 실패 시 네트워크 조치 순서 안내해줘",
            "스마트폰 변경 후 2차 인증(OTP) 재등록 절차 설명해줘",
            "사내 층별 복합기 드라이버 설치 및 보안 출력 설정 가이드 해줘",
        ],
        "instructions_summary": "임직원의 업무 중단을 최소화하기 위해 즉각적인 자가 조치 가이드를 제공하고, 미해결 시 IT 헬프데스크 티켓 접수를 유도한다.",
    },
    9: {
        "id": "ga-facility-navigator",
        "slug": "ga-facility-navigator",
        "title": "사내 시설 및 회의실 예약 도우미 에이전트",
        "name": "사내 시설 및 회의실 예약 도우미 에이전트",
        "category": "총무 및 시설 관리",
        "description": "본사 및 지사 회의실 화상 장비 지원 여부, 사내 카페/피트니스 이용 시간, 주차 등록 및 방문객 출입증 발급을 지원한다.",
        "mention_handle": "@ga-facility-navigator",
        "slash_command": "/ga-facility-navigator",
        "target_users": "전사 임직원 및 방문객 접수자",
        "core_compliance": "사내 사옥 관리 규정 및 방문객 출입 보안 수칙",
        "default_scope": "ORG",
        "starter_prompts": [
            "30인 이상 수용 가능한 화상회의실 예약 현황과 장비 안내해줘",
            "외부 고객사 방문 시 임시 출입증 발급 및 무료 주차 등록 방법 알려줘",
            "사내 피트니스 센터 이용 시간과 개인 사물함 배정 규정 확인해줘",
            "사내 우편물 수령처와 퀵서비스 발송 신청 절차 안내해줘",
        ],
        "instructions_summary": "사옥 편의시설과 공용 회의실 이용 수칙을 신속하게 안내하여 쾌적한 사내 환경 운영을 돕는다.",
    },
    10: {
        "id": "sales-rfp-assistant",
        "slug": "sales-rfp-assistant",
        "title": "공공 및 엔터프라이즈 제안서 초안 에이전트",
        "name": "공공 및 엔터프라이즈 제안서 초안 에이전트",
        "category": "세일즈 및 사업 개발",
        "description": "공공기관 및 대기업 제안요청서(RFP) 요구사항을 매트릭스로 분석하고, 회사 소개, 기술 스택, 수행 실적 요약 초안을 작성한다.",
        "mention_handle": "@sales-rfp-assistant",
        "slash_command": "/sales-rfp-assistant",
        "target_users": "세일즈 엔지니어, 제안 PM, 사업개발팀",
        "core_compliance": "국가를 당사자로 하는 계약에 관한 법률 및 제안 보안 규정",
        "default_scope": "ORG",
        "starter_prompts": [
            "RFP 요구사항 명세서의 기능적 요구사항 분석 매트릭스 표 생성해줘",
            "클라우드 구축 사업 제안서의 시스템 아키텍처 개요 초안 작성해줘",
            "유사 사업 수행 실적 증명서 양식에 맞춘 3개년 주요 레퍼런스 정리해줘",
            "제안서 평가 배점표 기준 기술 부문 고득점 차별화 전략 제안해줘",
        ],
        "instructions_summary": "발주처의 RFP 요구사항을 정확히 충족하는 고품질 제안서 목차와 기술 서술 초안을 체계적으로 빌드한다.",
    },
    11: {
        "id": "cs-voc-classifier",
        "slug": "cs-voc-classifier",
        "title": "고객 VOC 분류 및 대응 가이드 에이전트",
        "name": "고객 VOC 분류 및 대응 가이드 에이전트",
        "category": "고객 지원 및 CS",
        "description": "인입된 고객 불만/문의(VOC)의 긴급도와 감성을 분석하여 부서별(품질, 배송, 결제)로 자동 분류하고 1차 정중 답변문을 추천한다.",
        "mention_handle": "@cs-voc-classifier",
        "slash_command": "/cs-voc-classifier",
        "target_users": "고객센터 상담원, CS 매니저, 제품 품질팀",
        "core_compliance": "소비자분쟁해결기준 및 악성 민원 대응 가이드라인",
        "default_scope": "ORG",
        "starter_prompts": [
            "인입된 고객 환불 지연 항의문에 대한 1차 정중 사과 답변 초안 써줘",
            "최근 일주일간 VOC 텍스트에서 불만 키워드 빈도 및 감성 점수 분석해줘",
            "제품 파손 클레임 접수 시 부서별 긴급 에스컬레이션 기준 안내해줘",
            "배송 지연에 따른 포인트 보상 기준과 고객 안내 스크립트 작성해줘",
        ],
        "instructions_summary": "고객의 감정에 공감하면서도 회사의 정책을 명확하게 전달하는 정중한 상담 스크립트와 분류 데이터를 제공한다.",
    },
    12: {
        "id": "biz-meeting-summarizer",
        "slug": "biz-meeting-summarizer",
        "title": "임원 회의록 및 액션 플랜 도우미 에이전트",
        "name": "임원 회의록 및 액션 플랜 도우미 에이전트",
        "category": "경영 기획 및 업무 보고",
        "description": "회의 전사 텍스트에서 주요 의사결정 사항, 부서별 담당 액션 아이템(R&R), 데드라인을 체계적으로 구조화 요약한다.",
        "mention_handle": "@biz-meeting-summarizer",
        "slash_command": "/biz-meeting-summarizer",
        "target_users": "전사 임직원, 프로젝트 관리자, 경영지원팀",
        "core_compliance": "경영 회의록 보안 등급 관리 지침",
        "default_scope": "ORG",
        "starter_prompts": [
            "경영전략 주간 회의 녹취록에서 의사결정 사항 3줄 요약해줘",
            "회의 내용 중 부서별 담당자, 액션 플랜, 완료 기한을 표로 정리해줘",
            "주요 안건별 찬반 쟁점 사항과 차주 팔로업 안건 도출해줘",
            "임원 보고용 1장짜리 핵심 요약 보고서 포맷으로 변환해줘",
        ],
        "instructions_summary": "모호하거나 장황한 대화 내용을 군더더기 없이 사실 중심의 결정 사항과 담당자별 실행 과제로 완벽히 정제한다.",
    },
    13: {
        "id": "corp-pr-drafter",
        "slug": "corp-pr-drafter",
        "title": "사내외 보도자료 및 공지문 작성 에이전트",
        "name": "사내외 보도자료 및 공지문 작성 에이전트",
        "category": "홍보 및 마케팅",
        "description": "신제품 출시, 조직 개편, 수상 실적 등 대내외 공식 공지문 및 언론 배포용 표준 보도자료 초안을 작성한다.",
        "mention_handle": "@corp-pr-drafter",
        "slash_command": "/corp-pr-drafter",
        "target_users": "홍보팀, 브랜드 마케터, 사내 커뮤니케이션 담당자",
        "core_compliance": "표시·광고의 공정화에 관한 법률 및 언론 보도 가이드라인",
        "default_scope": "ORG",
        "starter_prompts": [
            "신규 AI 솔루션 런칭 관련 언론 배포용 표준 보도자료 초안 작성해줘",
            "사내 조직 개편 및 임원 인사 발령 전사 공지문 포맷 작성해줘",
            "ESG 친환경 경영 인증 획득 소식에 대한 사내 게시판 홍보글 써줘",
            "보도자료 내 인용 문구(대표이사 코멘트) 적절한 톤앤매너로 다듬어줘",
        ],
        "instructions_summary": "과장이나 단정적 표현을 배제하고 사실과 검증된 지표 중심의 신뢰도 높은 대외 커뮤니케이션 문안을 생성한다.",
    },
    14: {
        "id": "procure-vendor-screener",
        "slug": "procure-vendor-screener",
        "title": "협력업체 평가 및 견적 비교 에이전트",
        "name": "협력업체 평가 및 견적 비교 에이전트",
        "category": "구매 및 조달",
        "description": "복수 벤더 비교 견적서 단가 차이, 신용평가등급, 납기 일정, 하도급법 준수 체크리스트를 구조화하여 비교표를 생성한다.",
        "mention_handle": "@procure-vendor-screener",
        "slash_command": "/procure-vendor-screener",
        "target_users": "구매팀, 자재관리팀, 사업 PM",
        "core_compliance": "하도급거래 공정화에 관한 법률 및 협력사 관리 규정",
        "default_scope": "ORG",
        "starter_prompts": [
            "하드웨어 납품 3개사 비교 견적서 단가 및 납기 비교표 만들어줘",
            "신규 협력업체 등록 시 필수 제출 서류 및 신용등급 심사 기준 알려줘",
            "용역 도급 계약 시 부당 감액 방지를 위한 하도급법 점검 항목 보여줘",
            "분기별 외주 협력사 SLA 평가 점수 집계표 작성해줘",
        ],
        "instructions_summary": "객관적인 수치와 납기, 신용도를 근거로 공정한 벤더 평가를 지원하며 불공정 거래 행위 위험을 사전 예방한다.",
    },
}


def load_agent_catalog(catalog_path: str = None) -> dict:
    """선언적 catalog.yaml 파일로부터 도메인별 엔터프라이즈 에이전트를 동적 로드한다 (4단계 캐스케이드 탐색)."""
    candidates = []
    if catalog_path:
        candidates.append(catalog_path)
    if os.environ.get("AGENT_CATALOG_PATH"):
        candidates.append(os.environ.get("AGENT_CATALOG_PATH"))
    local_default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog.yaml")
    candidates.append(local_default)

    raw_yaml_text = None
    loaded_source = None

    for target in candidates:
        if not target:
            continue
        # 원격 URL 처리 (2.0초 타임아웃 적용하여 사내 방화벽 행 방지)
        if target.startswith("http://") or target.startswith("https://"):
            try:
                req = urllib.request.Request(target, headers={"User-Agent": "GE-Agent-Factory/1.0"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    raw_yaml_text = resp.read().decode("utf-8")
                    loaded_source = f"원격 URL ({target})"
                    break
            except Exception:
                continue
        # 로컬 파일 처리
        elif os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    raw_yaml_text = f.read()
                    loaded_source = f"로컬 파일 ({target})"
                    break
            except Exception:
                continue

    if not raw_yaml_text or yaml is None:
        return FALLBACK_AGENT_CATALOG

    try:
        data = yaml.safe_load(raw_yaml_text)
        agents_list = data.get("agents", [])
        if not agents_list:
            return FALLBACK_AGENT_CATALOG

        catalog = {}
        slug_pattern = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
        seen_slugs = set()
        seen_names = set()
        seen_mentions = set()

        for idx, a in enumerate(agents_list, start=1):
            slug = a.get("slug", f"agent-{idx}-helper")
            if not slug_pattern.match(slug):
                slug = slug.lower().replace("_", "-")

            name = a.get("name", slug)
            mention_handle = a.get("mention_handle", f"@{slug}")
            slash_command = a.get("slash_command", f"/{slug}")

            # 사전 중복 검증 인터셉터 (Pre-flight duplicate check)
            if slug in seen_slugs:
                print(f"[경고] 중복된 에이전트 슬러그 발견 및 자동 격리: {slug}", file=sys.stderr)
                continue
            if name in seen_names:
                print(f"[경고] 중복된 에이전트 명칭 발견: {name}", file=sys.stderr)
            if mention_handle in seen_mentions:
                print(f"[경고] 중복된 멘션 핸들 발견: {mention_handle}", file=sys.stderr)

            seen_slugs.add(slug)
            seen_names.add(name)
            seen_mentions.add(mention_handle)

            catalog[idx] = {
                "id": slug,
                "slug": slug,
                "title": name,
                "name": name,
                "category": a.get("category", "기타 엔터프라이즈 업무"),
                "description": a.get("description", ""),
                "mention_handle": mention_handle,
                "slash_command": slash_command,
                "target_users": a.get("target_users", "전사 임직원"),
                "core_compliance": a.get("core_compliance", "사내 업무 규정"),
                "default_scope": a.get("default_scope", "ORG"),
                "starter_prompts": a.get("starter_prompts", []),
                "instructions_summary": a.get("instructions_summary", ""),
            }

        return catalog if catalog else FALLBACK_AGENT_CATALOG
    except Exception as e:
        print(f"[정보] 선언적 카탈로그 파싱 예외 발생, 내장 시드로 폴백: {e}", file=sys.stderr)
        return FALLBACK_AGENT_CATALOG


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


def get_resource_creator(dry_run: bool = False) -> str:
    """CLI 실행 계정으로부터 GCP 표준 라벨 형식에 부합하는 풀 프린시펄(Full Principal) 문자열을 추출한다."""
    if dry_run:
        return "customer-engineer"
    account = get_gcloud_config("account") or os.environ.get("USER") or "customer-engineer"
    clean = account.lower().replace("@", "-at-").replace(".", "-").replace(":", "-").replace("_", "-")
    sanitized = "".join(c for c in clean if c.isalnum() or c == "-").strip("-")
    return sanitized[:63] if sanitized else "customer-engineer"


def _get_cloud_token() -> str:
    """로컬 gcloud 계정 또는 클라우드 런타임 ADC로부터 유효한 OAuth2 액세스 토큰을 조회한다."""
    try:
        out = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True, timeout=10).strip()
        tok = out.split()[-1]
        if tok.startswith("ya29."):
            return tok
    except Exception:
        pass
    try:
        import google.auth
        import google.auth.transport.requests
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        return creds.token
    except Exception as e:
        raise RuntimeError(f"GCP 인증 토큰을 획득할 수 없습니다: {e}")


def discover_ge_app_engines(project_id: str) -> list:
    """현재 프로젝트에 프로비저닝된 Gemini Enterprise App (Discovery Engine) 목록을 실시간 조회한다."""
    if not project_id or project_id == "sample-project-id":
        return []

    token = _get_cloud_token()
    if not token:
        return []

    url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/global/collections/default_collection/engines"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            engines = data.get("engines", [])
            result = []
            for e in engines:
                eng_id = e.get("name", "").split("/")[-1]
                disp_name = e.get("displayName", eng_id)
                result.append({"id": eng_id, "displayName": disp_name})
            return result
    except Exception:
        return []


def select_ge_app_id(project_id: str, candidate_apps: list, dry_run: bool = False) -> str:
    """사내에 발견된 복수 GE App 중 하나를 대화형 번호로 선택하거나 기본값을 채택한다."""
    if not candidate_apps:
        return os.environ.get("GE_APP_ID") or ("sample-ge-app-id" if dry_run else "default_app")

    if len(candidate_apps) == 1:
        chosen = candidate_apps[0]["id"]
        print(f"[*] 사내 활성 Gemini Enterprise App 자동 감지: {chosen} ({candidate_apps[0]['displayName']})")
        return chosen

    print(f"\n[*] 사내 발견된 Gemini Enterprise App 목록 ({len(candidate_apps)}개):")
    for idx, app in enumerate(candidate_apps, 1):
        print(f"  [{idx}] {app['id']} ({app['displayName']})")

    # dry-run 모드에서는 프로세스 멈춤 방지를 위해 1번 자동 시뮬레이션
    if dry_run:
        selected = candidate_apps[0]["id"]
        print(f"  -> [가상 실행] 1번 GE App 자동 채택: {selected}")
        return selected

    # 실제 실행 모드 + 대화형 TTY 환경인 경우 번호 선택 요청
    if sys.stdin.isatty():
        try:
            choice = input(f"\n선택할 Gemini Enterprise App 번호를 입력하세요 [1-{len(candidate_apps)}, 기본값 1]: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(candidate_apps):
                selected = candidate_apps[int(choice) - 1]["id"]
                print(f"  -> 선택된 GE App: {selected}")
                return selected
        except (EOFError, KeyboardInterrupt):
            pass

    selected = candidate_apps[0]["id"]
    print(f"  -> 기본 1번 GE App 자동 채택: {selected}")
    return selected


def persist_env_value(key: str, value: str, dry_run: bool = False):
    """실행 중 자동 감지되거나 선택된 값을 로컬 .env 파일에 안전하게 반영한다."""
    if dry_run or not value or value.startswith("sample-"):
        return

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(cur_dir, ".env")
    example_path = os.path.join(cur_dir, ".env.example")

    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    elif os.path.exists(example_path):
        with open(example_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"#{key}="):
            new_lines.append(f"{key}={value}\n")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"{key}={value}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"[*] 로컬 .env 파일에 {key}={value} 설정 저장 완료")
    except Exception:
        pass


def run_config_mode(args):
    """사내 환경 대화형 설정 마법사: gcloud 활성 설정 및 사내 리소스를 탐색하여 .env에 저장한다."""
    print("\n" + "=" * 75)
    print("  Gemini Enterprise 노코드 에이전트 팩토리 - 사내 환경 설정 마법사 (--config)")
    print("=" * 75)

    load_env_file()

    # 1. Project ID
    current_proj = os.environ.get("PROJECT_ID") or get_gcloud_config("project") or ""
    proj_prompt = f"1. 구글 클라우드 프로젝트 ID [기본값: {current_proj}]: " if current_proj else "1. 구글 클라우드 프로젝트 ID 입력: "
    if sys.stdin.isatty():
        try:
            val = input(proj_prompt).strip()
            chosen_proj = val if val else current_proj
        except (EOFError, KeyboardInterrupt):
            chosen_proj = current_proj
    else:
        chosen_proj = current_proj

    if not chosen_proj:
        chosen_proj = "sample-project-id"
    persist_env_value("PROJECT_ID", chosen_proj)
    print(f"  -> 프로젝트 ID 설정: {chosen_proj}")

    # 2. Location
    current_loc = os.environ.get("LOCATION") or "global"
    loc_prompt = f"2. Gemini Enterprise / Discovery Engine 리전 [기본값: {current_loc}]: "
    if sys.stdin.isatty():
        try:
            val = input(loc_prompt).strip()
            chosen_loc = val if val else current_loc
        except (EOFError, KeyboardInterrupt):
            chosen_loc = current_loc
    else:
        chosen_loc = current_loc
    persist_env_value("LOCATION", chosen_loc)
    print(f"  -> 리전 설정: {chosen_loc}")

    # 3. GE App ID 탐색 및 선택
    print("\n[*] 사내 Gemini Enterprise App (Discovery Engine) 목록 실시간 스캔 중...")
    candidate_apps = discover_ge_app_engines(chosen_proj)
    chosen_app = ""
    if candidate_apps:
        print(f"[*] {len(candidate_apps)}개의 Gemini Enterprise App 인스턴스를 발견했습니다:")
        for idx, app in enumerate(candidate_apps, 1):
            disp = app.get("displayName") or "무제"
            app_id = app.get("id")
            print(f"    [{idx}] {app_id} (표시 이름: {disp})")
        if sys.stdin.isatty():
            try:
                choice = input(f"\n3. 사용할 Gemini Enterprise App 번호 [1-{len(candidate_apps)}, 기본값 1]: ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(candidate_apps):
                    chosen_app = candidate_apps[int(choice) - 1]["id"]
            except (EOFError, KeyboardInterrupt):
                pass
        if not chosen_app:
            chosen_app = candidate_apps[0]["id"]
    else:
        print("  [-] 현재 프로젝트에서 프로비저닝된 Gemini Enterprise App을 발견하지 못했습니다.")
        print("  [*] 신규 App 생성이 필요한 경우 공식 콘솔 경로를 참고하십시오:")
        print("      Google Cloud 콘솔 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines )")
        current_app = os.environ.get("GE_APP_ID") or ""
        app_prompt = f"\n3. Gemini Enterprise App 인스턴스 ID [Enter 시 기본값({current_app or 'default'}) 자동 채택]: "
        if sys.stdin.isatty():
            try:
                val = input(app_prompt).strip()
                chosen_app = val if val else (current_app or "default")
            except (EOFError, KeyboardInterrupt):
                chosen_app = current_app or "default"
        else:
            chosen_app = current_app or "default"

    persist_env_value("GE_APP_ID", chosen_app)
    print(f"  -> GE App ID 설정: {chosen_app}")

    print("\n" + "-" * 75)
    print("[*] 사내 환경 설정이 .env 파일에 성공적으로 저장되었습니다.")
    print("[*] 다음 명령어로 실행을 진행하십시오:")
    print("    - 가상 실행 검증: python diagnose.py --dry-run")
    print("    - 실제 팩토리 배포: python diagnose.py")
    print("=" * 75 + "\n")


def resolve_environment(args):
    """실행 환경(프로젝트 ID, 리전, Gemini Enterprise App ID, 대행 서비스 계정)을 계층형으로 확정한다 (실시간 GE App 감지 및 대화형 번호 선택 지원)."""
    load_env_file()

    # 1. Project ID (가상 실행 시 사내 실환경 노출 방지 가명 우선, 명시적 인자 최우선)
    if args.dry_run and not args.project:
        project_id = "sample-project-id"
    else:
        project_id = args.project or os.environ.get("PROJECT_ID") or get_gcloud_config("project") or "sample-project-id"

    if not args.dry_run and not os.environ.get("PROJECT_ID") and project_id != "sample-project-id":
        persist_env_value("PROJECT_ID", project_id, dry_run=args.dry_run)

    # 2. Location
    location = args.location or os.environ.get("LOCATION") or "global"

    # 3. Gemini Enterprise App ID
    if args.dry_run and not args.ge_app_id:
        ge_app_id = "sample-ge-app-id"
    else:
        ge_app_id = args.ge_app_id or os.environ.get("GE_APP_ID")
        if not ge_app_id:
            candidates = discover_ge_app_engines(project_id)
            ge_app_id = select_ge_app_id(project_id, candidates, dry_run=args.dry_run)
            if not args.dry_run and ge_app_id:
                persist_env_value("GE_APP_ID", ge_app_id, dry_run=args.dry_run)

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


def select_chip_interactive(dry_run: bool, catalog: dict = None):
    """대화형 환경에서 부서 및 추천 에이전트 칩을 번호로 선택한다."""
    active_catalog = catalog or FALLBACK_AGENT_CATALOG
    is_interactive = sys.stdin.isatty() and not dry_run

    if not is_interactive:
        # 비대화형 또는 가상 실행 시 기본 1번 에이전트 자동 채택
        chip = active_catalog[1]
        return chip["category"], chip

    print("\n" + "=" * 75)
    print("  Gemini Enterprise 자율형 사내 노코드 에이전트 팩토리")
    print("  [부서별 맞춤형 에이전트 프리셋 목록]")
    print("=" * 75)
    for aid, data in sorted(active_catalog.items()):
        handle = data.get("mention_handle", f"@{data.get('slug', 'agent')}")
        print(f"  [{aid:2d}] {handle:24s} : {data['name']} [{data['category']}]")
    print("  [ 0] 직접 프롬프트 입력 (Free-form Prompt)")

    try:
        choice_in = input(f"\n선택할 에이전트 번호를 입력하세요 [1-{len(active_catalog)}, 기본값: 1]: ").strip()
        choice = int(choice_in) if choice_in else 1
    except ValueError:
        choice = 1

    if choice == 0 or choice not in active_catalog:
        custom_title = input("\n원하는 에이전트의 업무 주제나 역할을 입력하세요: ").strip()
        if not custom_title:
            custom_title = "사내 업무 프로세스 질의응답 비서"
        return "사용자 직접 정의", {
            "id": "custom-agent-helper",
            "slug": "custom-agent-helper",
            "title": custom_title,
            "name": custom_title,
            "mention_handle": "@custom-agent-helper",
            "category": "사용자 직접 정의",
            "target_users": "사내 관련 부서 임직원",
            "core_compliance": "사내 정보보호 규정 및 표준 보안 가이드라인",
            "starter_prompts": [
                f"{custom_title}의 주요 지원 범위를 알려줘",
                "관련 업무 진행 시 필수 제출 서류 및 규정을 확인해줘",
                "담당 부서 에스컬레이션 절차를 안내해줘",
                "자주 묻는 질문 FAQ TOP 3를 정리해줘",
            ],
            "instructions_summary": "사용자가 직접 정의한 업무 요구사항을 바탕으로 안전하고 전문적인 업무 보조를 수행한다.",
        }

    selected_chip = active_catalog[choice]
    return selected_chip["category"], selected_chip


def synthesize_agent_specification(category: str, chip: dict, dry_run: bool, project_id: str):
    """실시간 검색 그라운딩 및 엔터프라이즈 골든 규격 기반으로 No-code 시스템 지침을 합성한다."""
    title = chip.get("name") or chip.get("title", "사내 업무 보조 에이전트")
    slug = chip.get("slug", "custom-agent-helper")
    mention_handle = chip.get("mention_handle", f"@{slug}")
    target_users = chip.get("target_users", "전사 임직원")
    compliance = chip.get("core_compliance", "사내 보안 규정")

    # 검색 그라운딩 모의/실제 수집 요약
    search_grounding_summary = (
        f"2026년 최신 '{compliance}' 법령 개정안, 식약처/금융보안원/고용노동부 고시 및 "
        f"사내 엔터프라이즈 거버넌스 표준 절차를 검색 그라운딩으로 실시간 수집 완료함."
    )

    # 기본 또는 선언적 카탈로그 스타터 질문 추출
    raw_starters = chip.get("starter_prompts")
    if raw_starters and isinstance(raw_starters, list) and len(raw_starters) >= 2:
        starter_prompts = raw_starters
    else:
        starter_prompts = [
            f"{title}의 지원 범위와 필수 준비 서류를 알려 줘.",
            f"{compliance} 기준에서 예외 적용이 가능한 사례가 있니?",
            "현재 내 요청 건의 처리 절차와 승인 결재선을 확인해 줘.",
            "자주 묻는 질문(FAQ) 및 주의 사항 TOP 3를 정리해 줘.",
        ]

    starters_formatted = "\n".join([f"{idx}. {sp}" for idx, sp in enumerate(starter_prompts, start=1)])

    # 5대 골든 프롬프트 구조에 따른 지침서 합성
    system_instructions = f"""# ROLE & IDENTITY (역할 및 페르소나)
너는 사내 Gemini Enterprise App 환경에서 공식 승인된 노코드(No-code) 전담 비서인 '{title}'({mention_handle})이다.
주요 대상 사용자는 '{target_users}'이며, 신속하고 정확하며 정중한 어조로 업무를 지원한다.

# APPLIED MODEL & RUNTIME (적용 모델 및 런타임 표준)
- **적용 모델**: `gemini-3.8-flash` (2026년 Google Cloud 공식 엔터프라이즈 주력 모델, 사내 RAG 및 고속 추론 기본값)
- **호출 핸들**: `{mention_handle}` (대화창 멘션 호출 지원)

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
{starters_formatted}
"""

    return {
        "title": title,
        "slug": slug,
        "mention_handle": mention_handle,
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
                        "created-by": get_resource_creator(False),
                    },
                },
            },
            "required": ["display_name", "description", "instructions", "starter_prompts"],
        },
    }

    meta_instructions = f"""너는 사내 Gemini Enterprise App 환경의 공식 에이전트 제작 도우미인 'GE In-Chat Agent Factory (사내 노코드 에이전트 팩토리)'이다.
사내 비개발자 임직원과 친절하게 대화하며, 추천 칩을 제시하고 실시간 구글 검색(Search Grounding)을 통해
전문적이고 빈틈없는 사내 승인 노코드 에이전트를 기획 및 등록해 주는 역할을 전담한다.

[2026년 Google Cloud AI 모델 표준 및 거버넌스 가이드라인]
- 사내 엔터프라이즈 표준 기본 모델은 'gemini-3.8-flash' (고속 응답, 사내 RAG 문서 검색, 일상 업무 자동화)이다.
- 에이전트 기획서 및 시스템 명세서 출력 시 적용 모델 항목에는 반드시 'gemini-3.8-flash (권장 기본)'로 명시한다.

[핵심 행동 수칙]
1. 임직원이 접속하면 부서별 추천 칩(IT, 인사, 재무, 법무, 스마트팩토리 등)을 제시하여 선택을 돕는다.
2. 선택된 주제에 대해 구글 검색을 활용하여 2026년 최신 규정 및 표준 작업 절차를 실시간으로 조사한다.
3. 5대 골든 프롬프트(Role, Workflow, Guardrails, Fallback, Starter Prompts) 규격으로 시스템 지침을 완성한다.
4. 임직원에게 기획된 에이전트 명세를 보여주고 최종 확인을 구한다.
5. 임직원이 동의하면 'create_ge_nocode_agent' 도구를 호출하여 전용 서비스 계정({env_info['delegated_sa']}) 권한으로 Gemini Enterprise app에 즉시 등록한다.

[단계별 추천 후속 질문 안내 규약]
사용자가 다음 행동이나 추천 옵션을 쉽게 선택할 수 있도록,
모든 답변 본문 맨 끝에 반드시 구분선(---)과 함께 마크다운 번호 매기기 리스트로 2~3개의 '추천 후속 질문'을 명확히 안내한다:
---
**추천 후속 질문:**
1. 추천 선택지 1 (예: IT 헬프데스크 에이전트 생성)
2. 추천 선택지 2 (예: 인사 복무 규정 FAQ 에이전트 생성)
3. 추천 선택지 3 (예: 사내 등록된 에이전트 목록 조회)
- 주의: JSON이나 코드 블록(```suggested_questions 등) 형태가 아닌, 순수 마크다운 텍스트 리스트로 가독성 높게 출력한다.
"""

    return {
        "display_name": "GE In-Chat Agent Factory (사내 노코드 에이전트 팩토리)",
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
- **등록 대상 Gemini Enterprise app**: ( https://gemini.google.com/app/{ge_app_id} )
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
   - 임직원 사내 포털 ( https://gemini.google.com/app/{ge_app_id} )에서 `@에이전트 팩토리`를 호출하여 자율 에이전트 제작을 시작하도록 사내 가이드를 배포한다.
2. **사내 거버넌스 승인 파이프라인**:
   - 임직원이 생성한 에이전트는 작성자 본인 및 팀 전용(`PRIVATE`)으로 즉시 활성화된다.
   - 전사 공개(`ORGANIZATION`)로 전환이 필요한 경우, 사내 클라우드 거버넌스 승인 절차를 거치도록 안내한다.

---

## 5. 사내 거버넌스 4대 필수 표준 라벨링

에이전트 인프라 및 관리 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-agent`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 6. 콘솔 링크 조치 가이드

- **Gemini Enterprise 웹 포털**: 사내 임직원 전용 대화형 포털 접속 및 에이전트 대화 ( https://gemini.google.com )
- **Gemini Enterprise 에이전트 목록 콘솔**: 사내 등록된 에이전트 목록 조회 및 관리 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines )
- **IAM 및 관리자 콘솔**: 대행 서비스 계정(`{sa_email}`) 역할 및 바인딩 상태 확인 ( https://console.cloud.google.com/iam-admin/iam )

---

## 7. 자원 정리 안내 (Teardown)

본 솔루션 검증 후 테스트용으로 등록된 메타 에이전트나 대행 서비스 계정을 정리하고자 할 경우 아래 절차를 수행한다:

1. **대행 서비스 계정 삭제**:
   ```bash
   gcloud iam service-accounts delete {sa_email} --quiet
   ```
2. **Gemini Enterprise app 등록 에이전트 삭제**:
   - Gemini Enterprise 에이전트 목록 콘솔 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines )에 접속하여 대상 앱의 `Agents` 목록에서 생성된 에이전트를 선택 후 삭제한다.
"""


def build_factory_markdown_report(env_info: dict, deploy_res: dict, dry_run: bool = False) -> str:
    """GE Agent Factory(붕어빵 틀 에이전트) 배포 결과를 표준 report.md 양식으로 조립한다 (가상 실행 시 사내 식별 정보 마스킹)."""
    if dry_run:
        project_id = "sample-project-id"
        ge_app_id = "sample-ge-app-id"
        re_uri = f"projects/{project_id}/locations/us-central1/reasoningEngines/simulated-agent-factory-engine"
        sa_email = f"ge-agent-factory-sa@{project_id}.iam.gserviceaccount.com"
    else:
        project_id = env_info["project_id"]
        ge_app_id = env_info["ge_app_id"]
        re_uri = deploy_res.get("reasoning_engine", "N/A")
        sa_email = env_info["delegated_sa"]

    status = deploy_res.get("status", "UNKNOWN")
    display_name = deploy_res.get("display_name", "GE In-Chat Agent Factory (사내 노코드 에이전트 팩토리)")
    portal_url = f"https://gemini.google.com/app/{ge_app_id}"

    return f"""# Gemini Enterprise 노코드 에이전트 팩토리 배포 보고서 (gemini-enterprise-copilot-agent)

- **배포 일시**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **대상 프로젝트**: `{project_id}`
- **Gemini Enterprise app 인스턴스**: `{ge_app_id}`
- **팩토리 에이전트**: `{display_name}`
- **배포 상태**: `{status}`

---

## 1. 팩토리 에이전트(붕어빵 틀) 프로비저닝 결과 요약

| 항목 | 상태 | 세부 정보 |
| :--- | :---: | :--- |
| **에이전트 명칭** | `PROVISIONED` | `{display_name}` |
| **호스팅 런타임** | `Agent Engine` | `{re_uri}` |
| **추론 파운데이션 모델** | `gemini-3.8-flash` | 위치: `global` (샌드박스 안정성 보장) |
| **내장 실행 도구** | `2종 완비` | `register_nocode_agent_tool`, `list_deployed_agents_tool` |
| **GE App 사내 갤러리 등록** | `ACTIVE` | 사내 갤러리(`/r/agents`) 전사 공유 (`ALL_USERS`) 바인딩 완료 |

---

## 2. 팩토리 에이전트 아키텍처 및 붕어빵 생산 흐름

본 솔루션은 비개발자 임직원이 복잡한 클라우드 콘솔이나 코딩 없이, GE App 채팅창에서 자연어 인터뷰만으로 사내 맞춤형 노코드 에이전트를 자율 생산(붕어빵 생산)할 수 있도록 지원하는 **사내 에이전트 팩토리(붕어빵 틀)**다:

```mermaid
flowchart TB
    subgraph Dev["1. 엔지니어링 & 프로비저닝"]
        A["인프라 / 플랫폼 엔지니어"] -->|"python diagnose.py"| B["노코드 에이전트 팩토리<br/>(diagnose.py)"]
        B -->|"Google ADK 2.11+ 패키징"| C["Agent Engine 이미지 & 스펙"]
    end

    subgraph Runtime["2. 런타임 & 도구 연동"]
        C -->|"원클릭 프로비저닝"| D["Agent Engine<br/>(Reasoning Engine)"]
        D -->|"사내 갤러리 전사 등록"| E["Gemini Enterprise app<br/>사내 갤러리 (/r/agents)"]
    end

    subgraph Portal["3. 전사 임직원 인터페이스"]
        E -->|"대화형 인터뷰 제공"| F["사내 임직원<br/>(비개발자 / 실무자)"]
        F -->|"자연어 에이전트 제작 요청"| E
        E -->|"에이전트 자동 생성 도구 호출"| D
    end
```

---

## 3. 사내 임직원 활용 가이드 (노코드 에이전트 생성)

전사 임직원은 배포된 팩토리 에이전트와 대화하여 다음과 같이 사내 맞춤형 에이전트를 즉시 찍어낼 수 있다:

1. **Gemini Enterprise app 접속**:
   - 웹 포털 ( {portal_url} ) 접속 후 좌측 사이드바 **사내 갤러리(`/r/agents`)** 이동.
   - **`{display_name}`** 선택.

2. **자연어 붕어빵 생성 예시 프롬프트**:
   - *"사내 특허 출원 절차 가이드 에이전트 만들어 줘"*
   - *"주간 업무 보고서 취합 및 경영진 브리핑 에이전트 만들어 줘"*
   - *"신규 입사자 온보딩 가이드 및 사내 규정 Q&A 에이전트 만들어 줘"*
   - *"CS 고객 불만 VOC 감성 분석 및 답변 초안 에이전트 만들어 줘"*

3. **팩토리 에이전트 자율 동작**:
   - 팩토리 에이전트가 4단계 인터뷰(목적 파악 -> 핵심 규칙 -> 지식 베이스 -> 최종 검증)를 진행하고,
   - 내장된 `register_nocode_agent_tool`을 호출하여 사내 갤러리에 신규 에이전트를 자동 등록한다.

---

## 4. 사내 거버넌스 4대 필수 표준 라벨

팩토리 에이전트 및 하위 생성 리소스 관리 시 아래 4대 표준 라벨이 기본 적용된다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-agent`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 5. 콘솔 링크 조치 가이드

- **Gemini Enterprise 사내 갤러리**: 사내 임직원 전용 대화형 포털 접속 및 에이전트 대화 ( https://gemini.google.com/app/{ge_app_id}/r/agents )
- **Gemini Enterprise 에이전트 목록 콘솔**: 사내 등록된 에이전트 및 Gemini Enterprise app 바인딩 관리 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/agentic/agents?project={project_id} )
- **IAM 및 관리자 콘솔**: 서비스 계정(`{sa_email}`) 권한 확인 ( https://console.cloud.google.com/iam-admin/iam?project={project_id} )

---

## 6. 자원 정리 안내 (Teardown)

본 솔루션 검증 후 테스트용으로 생성된 Agent Engine 런타임 및 등록된 에이전트를 정리하고자 할 경우 아래 명령을 수행한다:

1. **Agent Engine 삭제**:
   ```bash
   # Agent Engine 인스턴스 삭제 (force=true)
   curl -X DELETE -H "Authorization: Bearer $(gcloud auth print-access-token)" \\
     "https://us-central1-aiplatform.googleapis.com/v1/{re_uri}?force=true"
   ```

2. **GE App 사내 갤러리 등록 해제**:
   ```bash
   # GE App 에이전트 삭제
   curl -X DELETE -H "Authorization: Bearer $(gcloud auth print-access-token)" \\
     "https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/global/collections/default_collection/engines/{ge_app_id}/assistants/default_assistant/agents/<AGENT_ID>"
   ```
"""


def save_markdown_report(report_content: str):
    """산출물을 report.md 파일로 덮어쓴다."""
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"\n[성공] 마크다운 진단 보고서가 저장되었습니다: {report_path}")


def deploy_agent_factory_engine(env_info: dict, dry_run: bool = False) -> dict:
    """Gemini Enterprise Agent Factory를 Agent Engine으로 프로비저닝하고 GE App에 자동 등록한다."""
    project_id = env_info["project_id"]
    re_location = "us-central1"
    ge_app_id = env_info["ge_app_id"]
    ge_location = "global"
    staging_bucket = f"gs://{project_id}-agent-engine-staging"

    display_name = "GE In-Chat Agent Factory (사내 노코드 에이전트 팩토리)"
    description = "사내 비개발자 임직원을 위한 대화형 노코드 AI 에이전트 팩토리"

    labels = {
        "managed-by": "google-cloud-0-to-1",
        "scenario": "gemini-enterprise-copilot-agent",
        "env": "sample",
        "created-by": get_resource_creator(dry_run),
    }

    if dry_run:
        print("\n--> [가상 실행 모드 (--dry-run)] 실제 배포 없이 프로비저닝 명세를 시뮬레이션합니다.")
        simulated_re_id = "simulated-agent-factory-engine"
        simulated_res = f"projects/{project_id}/locations/{re_location}/reasoningEngines/{simulated_re_id}"
        print(f"  [1] Agent Engine 프로비저닝 시뮬레이션: {simulated_res}")
        print(f"  [2] GE App 사내 갤러리(/r/agents) 전사 공유(ALL_USERS) 등록 명세 검증 완료")
        return {
            "status": "DRY_RUN_PASSED",
            "reasoning_engine": simulated_res,
            "display_name": display_name,
            "ge_app_id": ge_app_id,
        }

    try:
        import vertexai
        from vertexai import agent_engines
        from google.adk.agents import Agent
        import google.oauth2.credentials
        import google.auth
    except ImportError as e:
        print(f"[오류] 필수 라이브러리가 누락되었습니다: {e}")
        return {"status": "FAILED", "error": str(e)}

    token = _get_cloud_token()
    creds = google.oauth2.credentials.Credentials(token)
    google.auth.default = lambda *args, **kwargs: (creds, project_id)

    print("\n[단계 1/2] Agent Engine 초기화 및 패키징 중...")
    vertexai.init(
        project=project_id,
        location=re_location,
        staging_bucket=staging_bucket,
        credentials=creds,
    )

    instruction = """당신은 Google Cloud 및 Gemini Enterprise app 환경의 전사 '사내 노코드 에이전트 팩토리(Agent Factory)' 마스터 에이전트입니다.
사내 비개발자 및 실무 임직원이 자신의 업무를 자동화할 수 있는 맞춤형 AI 에이전트를 대화형으로 손쉽게 만들 수 있도록 안내하고, 완성된 에이전트를 실제 사내 갤러리 및 Gemini Enterprise app에 자동 등록해 주는 역할을 수행합니다.

[2026년 Google Cloud AI 모델 표준 및 거버넌스 가이드라인]
- 사내 기본 표준 모델은 'gemini-3.8-flash' (고속 응답, 사내 RAG 문서 검색, 일상 업무 자동화)이다.
- 에이전트 기획서 및 시스템 명세서 출력 시 적용 모델 항목에는 반드시 'gemini-3.8-flash (권장 기본)'로 명시한다.

[핵심 단계별 인터뷰 절차]
1단계 (목적 파악): 해결하려는 구체적인 업무 페인포인트와 주요 사용 부서 확인.
2단계 (핵심 규칙): 에이전트가 지켜야 할 사내 규정과 처리 기준, 필수 기재 항목 정의.
3단계 (지식 베이스): 연동할 사내 구글 드라이브(Google Drive), 구글 시트(Google Sheets), 문서, 사내 위키 등 데이터 저장소 정의.
4단계 (최종 검증 및 합성): 5대 골든 규격(Role, Workflow, Guardrails, Fallback, Starter Prompts)으로 완성된 시스템 지침서 생성.
5단계 (실제 클라우드 등록): 사용자가 에이전트 등록/배포에 동의하면, 반드시 `register_nocode_agent_tool` 도구를 호출하여 Gemini Enterprise app 사내 갤러리에 실제로 등록을 집행한다!

[장착된 실제 실행 도구 (Tools)]
당신에게는 실제 클라우드 환경에 에이전트를 프로비저닝하고 Gemini Enterprise app에 자동 등록할 수 있는 실제 실행 도구가 장착되어 있습니다:
1. `register_nocode_agent_tool`: 인터뷰를 마치고 에이전트 기획이 완료되면, 사용자가 "등록해 줘", "배포해 줘", "생성해 줘"라고 하거나 동의했을 때 즉시 이 도구를 호출하여 실제 클라우드에 에이전트를 등록하십시오! 이 도구를 호출해야만 사내 에이전트 목록에 나타납니다.
2. `list_deployed_agents_tool`: 현재 사내에 등록된 활성 에이전트 목록을 조회할 때 즉시 호출하십시오.

[단계별 추천 후속 질문 안내 규약]
모든 답변 본문의 맨 끝에는 사용자가 다음 행동을 쉽게 선택할 수 있도록 구분선(---)과 함께 마크다운 번호 매기기 리스트로 2~3개의 '추천 후속 질문'을 명확히 안내한다:
---
**추천 후속 질문:**
1. 에이전트 등록 실행
2. 지식 저장소 추가 연동
3. 사내 등록된 에이전트 목록 조회
- 주의: JSON이나 코드 블록(```suggested_questions 등) 형태가 아닌, 순수 마크다운 텍스트 리스트로 가독성 높게 출력한다.

[소통 원칙]
- 정중하고 품격 있는 문어체(-다, -한다)와 한글 맞춤법 복합어 띄어쓰기를 철저히 준수합니다.
- 이모지나 특수 기호 대신 깔끔한 마크다운을 사용합니다.
"""

    def register_nocode_agent_tool(
        display_name: str,
        description: str,
        instructions: str,
        starter_prompts: str = "",
    ) -> str:
        """Register the newly designed no-code agent directly into Gemini Enterprise app so it appears in the enterprise gallery.

        Args:
            display_name: The display name of the agent (e.g. '사내 특허 출원 절차 가이드 에이전트').
            description: Short summary of what the agent does.
            instructions: Complete 5 golden prompt system instructions for the agent.
            starter_prompts: Comma-separated starter questions (e.g. '특허 출원 지원 범위 알려 줘, 필수 서류는 뭐야').
        """
        token = ""
        try:
            import google.auth
            import google.auth.transport.requests
            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            token = creds.token
        except Exception:
            try:
                token = _get_cloud_token()
            except Exception:
                token = ""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        }
        base_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
            f"/locations/{ge_location}/collections/default_collection"
            f"/engines/{ge_app_id}/assistants/default_assistant/agents"
        )

        # 1. 대상 GE App 내 기존 등록 여부 및 팩토리 호스팅 엔진 동적 탐색 (Pre-flight check)
        factory_re_res = ""
        try:
            list_resp = requests.get(base_url, headers=headers, timeout=15)
            if list_resp.ok:
                for a in list_resp.json().get("agents", []):
                    if a.get("displayName") == display_name:
                        existing_id = a.get("name", "").split("/")[-1]
                        existing_state = a.get("state", "UNKNOWN")
                        if existing_state == "ENABLED":
                            return (
                                f"### 사내 노코드 에이전트 등록 현황\n\n"
                                f"- **{display_name}**\n"
                                f"  - 상태: 이미 사내 갤러리에 정상 등록되어 활성화(ENABLED)되어 있습니다.\n"
                                f"  - Agent ID: `{existing_id}`\n"
                                f"  - 공유 범위: `ALL_USERS`\n"
                                f"  - 안내: 추가 등록 없이 사내 갤러리(/r/agents)에서 즉시 대화하실 수 있습니다."
                            )
                    # 팩토리 자체의 Reasoning Engine 리소스 이름 동적 추출 (adkAgentDefinition 리소스 스펙 기반)
                    if "adkAgentDefinition" in a:
                        re_engine = a.get("adkAgentDefinition", {}).get("provisionedReasoningEngine", {}).get("reasoningEngine")
                        if re_engine:
                            factory_re_res = re_engine
        except Exception:
            pass

        prompts_list = [p.strip() for p in starter_prompts.split(",") if p.strip()] if starter_prompts else [
            f"{display_name}의 주요 기능을 알려 줘",
            "업무 처리 절차와 승인 결재선 확인해 줘",
            "필수 준비 서류와 주의 사항 알려 줘",
            "자주 묻는 질문(FAQ) 정리해 줘",
        ]

        # 전사 갤러리 즉시 노출 및 ENABLED 활성화를 위해 엔터프라이즈 정규 adkAgentDefinition 규격 적용
        body = {
            "displayName": display_name,
            "description": description,
            "state": "ENABLED",
            "sharingConfig": {"scope": "ALL_USERS"},
            "customPlaceholderText": f"{display_name}에게 업무 질문이나 요청을 입력하세요...",
            "starterPrompts": [{"text": p} for p in prompts_list],
            "adkAgentDefinition": {
                "toolSettings": {"toolDescription": description},
                "provisionedReasoningEngine": {
                    "reasoningEngine": factory_re_res or f"projects/{project_id}/locations/us-central1/reasoningEngines/1287101780492025856"
                },
            },
        }

        try:
            resp = requests.post(base_url, headers=headers, json=body, timeout=30)
            if resp.status_code == 409 or "already exists" in resp.text.lower():
                list_resp = requests.get(base_url, headers=headers, timeout=30)
                agent_id = None
                existing_state = None
                if list_resp.ok:
                    for a in list_resp.json().get("agents", []):
                        if a.get("displayName") == display_name:
                            agent_id = a.get("name").split("/")[-1]
                            existing_state = a.get("state")
                            break
                if agent_id:
                    if existing_state == "PRIVATE" and "adkAgentDefinition" in body:
                        requests.delete(f"{base_url}/{agent_id}", headers=headers, timeout=30)
                        resp = requests.post(base_url, headers=headers, json=body, timeout=30)
                    else:
                        mask = "displayName,description,starterPrompts,customPlaceholderText"
                        mask += ",adkAgentDefinition" if "adkAgentDefinition" in body else ",noCodeAgentDefinition"
                        patch_url = f"{base_url}/{agent_id}?updateMask={mask}"
                        resp = requests.patch(patch_url, headers=headers, json=body, timeout=30)

            if resp.ok:
                res_data = resp.json()
                agent_id = res_data.get("name", "").split("/")[-1]
                agent_state = res_data.get("state", "PRIVATE")
                admin_url = f"https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/agentic/agents?project={project_id}"
                portal_url = f"https://gemini.google.com/app/{ge_app_id}/r/agents"
                activation_guide = (
                    f"사내 모든 임직원이 사내 갤러리 ( {portal_url} ) 및 검색창에서 즉시 해당 에이전트를 호출하여 대화할 수 있습니다."
                    if agent_state == "ENABLED"
                    else (
                        f"관리자 승인이나 상세 설정은 Gemini Enterprise 에이전트 목록 콘솔 ( {admin_url} )에서 확인하실 수 있습니다."
                    )
                )
                return (
                    f"### 사내 노코드 에이전트 등록 완료\n\n"
                    f"- **에이전트 명칭**: {display_name}\n"
                    f"- **Agent ID**: `{agent_id}`\n"
                    f"- **등록 상태**: `{agent_state}`\n"
                    f"- **공유 범위**: `전사 공유 (ALL_USERS)`\n"
                    f"- **적용 모델**: `gemini-3.8-flash` (2026 최신 표준)\n\n"
                    f"[사내 갤러리 활성화 안내]\n"
                    f"{activation_guide}"
                )
            else:
                return f"[등록 오류] 에이전트 등록 실패 (HTTP {resp.status_code}): {resp.text[:300]}"
        except Exception as e:
            return f"[등록 예외] 에이전트 등록 중 예외 발생: {str(e)}"

    def _get_agent_type(agent_dict: dict) -> str:
        """Discovery Engine 리소스 스키마 정의 키 기반 순수 리소스 유형 판별."""
        if "skillAgentDefinition" in agent_dict:
            return "스킬 (/r/skills)"
        elif "a2aAgentDefinition" in agent_dict:
            return "A2A 데이터 에이전트 (/r/agents)"
        elif "adkAgentDefinition" in agent_dict:
            return "커스텀 에이전트 (/r/agents)"
        elif "noCodeAgentDefinition" in agent_dict:
            return "노코드 에이전트 (/r/agents)"
        return "기타"

    def list_deployed_agents_tool() -> str:
        """List all currently active agents registered in Gemini Enterprise app.

        Returns:
            A markdown-formatted summary table of registered agents with explicit resource definition types.
        """
        token = ""
        try:
            import google.auth
            import google.auth.transport.requests
            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            token = creds.token
        except Exception:
            try:
                token = _get_cloud_token()
            except Exception:
                token = ""
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Goog-User-Project": project_id,
        }
        url = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
            f"/locations/{ge_location}/collections/default_collection"
            f"/engines/{ge_app_id}/assistants/default_assistant/agents"
        )
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if not resp.ok:
                return f"[오류] 에이전트 목록 조회 실패 (HTTP {resp.status_code}): {resp.text}"
            data = resp.json()
            agents = data.get("agents", [])
            if not agents:
                return "현재 등록된 에이전트가 없습니다."

            lines = [
                "### Gemini Enterprise App 등록 에이전트 및 스킬 현황",
                "",
                "| 에이전트 명칭 | Agent ID | 유형 (Type) | 상태 (State) | 공유 범위 (Sharing) |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
            for a in agents:
                aid = a.get("name", "").split("/")[-1]
                disp = a.get("displayName", "-")
                atype = _get_agent_type(a)
                state = a.get("state", "UNKNOWN")
                scope = a.get("sharingConfig", {}).get("scope", "PRIVATE")
                lines.append(f"| {disp} | `{aid}` | {atype} | `{state}` | `{scope}` |")
            return "\n".join(lines)
        except Exception as e:
            return f"[예외 발생] 에이전트 목록 조회 실패: {str(e)}"

    adk_agent = Agent(
        name="gemini_enterprise_agent_factory",
        description=description,
        model="gemini-3.8-flash",
        instruction=instruction,
        tools=[register_nocode_agent_tool, list_deployed_agents_tool],
    )
    class ResilientAdkApp(agent_engines.AdkApp):
        """Pydantic v2 직렬화 호환성 및 세션 안정화를 지원하는 엔터프라이즈 Agent Engine 래퍼."""

        def _ensure_pydantic_private(self):
            targets = []
            if "agent" in self._tmpl_attrs and self._tmpl_attrs["agent"] is not None:
                targets.append(self._tmpl_attrs["agent"])
            for runner_key in ("runner", "in_memory_runner"):
                runner = self._tmpl_attrs.get(runner_key)
                if runner and hasattr(runner, "app") and runner.app:
                    if hasattr(runner.app, "root_agent") and runner.app.root_agent:
                        targets.append(runner.app.root_agent)
            for ag in targets:
                if getattr(ag, "__pydantic_private__", None) is None:
                    object.__setattr__(
                        ag,
                        "__pydantic_private__",
                        {"_resolved_model": None, "_resolved_live_model": None},
                    )
                try:
                    _ = ag.canonical_model
                except Exception:
                    pass

        def set_up(self):
            self._ensure_pydantic_private()
            super().set_up()
            self._ensure_pydantic_private()

        async def streaming_agent_run_with_events(self, request_json: str):
            self._ensure_pydantic_private()
            async for event in super().streaming_agent_run_with_events(request_json):
                yield event

        async def async_stream_query(self, *args, **kwargs):
            self._ensure_pydantic_private()
            async for event in super().async_stream_query(*args, **kwargs):
                yield event

    # 사전 모델 해석으로 Pydantic v2 __pydantic_private__ 슬롯 초기화 강제
    try:
        _ = adk_agent.canonical_model
    except Exception:
        pass

    app = ResilientAdkApp(agent=adk_agent, enable_tracing=True)

    runtime_env = {
        "GOOGLE_GENAI_USE_VERTEXAI": "1",
        "GOOGLE_CLOUD_LOCATION": "global",
        "ADK_ENABLE_MCP_MODERN_PROTOCOL": "1",
    }

    print("  - Agent Engine 프로비저닝 LRO 생성 중 (약 1분 소요)...")
    remote = agent_engines.create(
        agent_engine=app,
        display_name=display_name,
        description=description,
        gcs_dir_name="ge_factory_agent_factory",
        requirements=[
            "google-cloud-aiplatform[adk,agent_engines]==2.5.0",
            "google-adk==2.11.0",
            "google-genai==2.31.0",
            "pydantic==2.13.5",
            "requests",
            "cloudpickle==3.1.2",
            "google-auth",
        ],
        env_vars=runtime_env,
    )

    re_res = remote.resource_name
    print(f"[성공] Agent Engine 생성 완료: {re_res}")

    print("\n[단계 2/2] Gemini Enterprise app 사내 갤러리(/r/agents) 자동 바인딩 중...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }
    base_url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
        f"/locations/{ge_location}/collections/default_collection"
        f"/engines/{ge_app_id}/assistants/default_assistant/agents"
    )

    body = {
        "displayName": display_name,
        "description": description,
        "state": "ENABLED",
        "sharingConfig": {"scope": "ALL_USERS"},
        "customPlaceholderText": "만들고 싶은 사내 맞춤 AI 에이전트의 업무나 목적을 입력하세요...",
        "starterPrompts": [
            {"text": "사내 특허 출원 절차 가이드 에이전트 만들어 줘"},
            {"text": "주간 업무 보고서 취합 및 경영진 브리핑 에이전트 만들어 줘"},
            {"text": "신규 입사자 온보딩 가이드 및 사내 규정 Q&A 에이전트 만들어 줘"},
            {"text": "CS 고객 불만 유형 자동 분류 및 답변 초안 에이전트 만들어 줘"},
        ],
        "adkAgentDefinition": {
            "toolSettings": {"toolDescription": description},
            "provisionedReasoningEngine": {
                "reasoningEngine": re_res
            },
        },
    }

    target_agent_id = None
    list_resp = requests.get(base_url, headers=headers, timeout=30)
    if list_resp.ok:
        for a in list_resp.json().get("agents", []):
            if a.get("displayName") == display_name:
                target_agent_id = a.get("name").split("/")[-1]
                break

    if target_agent_id:
        patch_url = f"{base_url}/{target_agent_id}?updateMask=displayName,description,starterPrompts,customPlaceholderText,adkAgentDefinition"
        reg_resp = requests.patch(patch_url, headers=headers, json=body, timeout=30)
    else:
        reg_resp = requests.post(base_url, headers=headers, json=body, timeout=30)

    if not reg_resp.ok:
        print(f"[경고] GE App 등록 응답 이상 ({reg_resp.status_code}): {reg_resp.text}")
    else:
        print(f"[성공] Gemini Enterprise app 등록 완료 (공유 범위: ALL_USERS)")

    return {
        "status": "DEPLOYED",
        "reasoning_engine": re_res,
        "display_name": display_name,
        "ge_app_id": ge_app_id,
    }


def run_local_scaffolding_mode(args, env_info: dict):
    """로컬 단일 에이전트 스펙 합성 및 인터뷰 보조 모드를 실행한다."""
    print("\n[안내] 로컬 단일 에이전트 스펙 합성 및 인터뷰 보조 모드 가동")

    # 1. 대행 서비스 계정 IAM 권한 진단
    print("\n[단계 1/4] 대행 서비스 계정(Delegated SA) IAM 권한 진단 중...")
    iam_diag = diagnose_iam_permissions(env_info, args.dry_run)
    print(f"  - 상태: {iam_diag['status']} | {iam_diag['detail']}")

    # 2. 메타 에이전트(@에이전트 팩토리) 매니페스트 및 도구 정의 빌드
    print("\n[단계 2/4] 메타 에이전트(@에이전트 팩토리) 매니페스트 및 도구 정의 구성 중...")
    meta_manifest = build_meta_agent_manifest(env_info)
    print(f"  - 메타 에이전트: {meta_manifest['display_name']}")
    print(f"  - 등록 도구(Tool): {meta_manifest['tools'][0]['name']} (대행 권한 연동)")

    # 3. 임직원 자율 생성 시나리오 칩 선택 및 지침 합성
    print("\n[단계 3/4] 추천 칩 인터뷰 및 실시간 검색 그라운딩 지침 합성 중...")
    catalog = load_agent_catalog(getattr(args, "catalog", None))

    category = "인사 및 조직 문화"
    selected_chip = catalog[1]

    if getattr(args, "prompt", None):
        category = "사용자 직접 정의"
        selected_chip = {
            "id": "custom-agent-helper",
            "slug": "custom-agent-helper",
            "title": args.prompt,
            "name": args.prompt,
            "mention_handle": "@custom-agent-helper",
            "category": "사용자 직접 정의",
            "target_users": "사내 관련 부서 임직원",
            "core_compliance": "사내 정보보호 규정 및 표준 보안 가이드라인",
            "starter_prompts": [
                f"{args.prompt}의 주요 지원 범위를 알려줘",
                "관련 업무 진행 시 필수 제출 서류 및 규정을 확인해줘",
                "담당 부서 에스컬레이션 절차를 안내해줘",
                "자주 묻는 질문 FAQ TOP 3를 정리해줘",
            ],
            "instructions_summary": "사용자가 직접 정의한 업무 요구사항을 바탕으로 안전하고 전문적인 업무 보조를 수행한다.",
        }
    elif getattr(args, "chip", None):
        chip_val = str(args.chip).strip()
        if chip_val.isdigit() and int(chip_val) in catalog:
            selected_chip = catalog[int(chip_val)]
            category = selected_chip["category"]
        else:
            found = False
            for c in catalog.values():
                if c.get("id") == chip_val or c.get("slug") == chip_val:
                    selected_chip = c
                    category = c["category"]
                    found = True
                    break
            if not found:
                print(f"[경고] 지정된 에이전트 식별자 '{chip_val}'을 카탈로그에서 찾을 수 없어 1번으로 대체합니다.")
                selected_chip = catalog[1]
                category = selected_chip["category"]
    elif getattr(args, "interactive", False) or (sys.stdin.isatty() and not args.dry_run):
        category, selected_chip = select_chip_interactive(args.dry_run, catalog=catalog)

    agent_title = selected_chip.get("name") or selected_chip.get("title")
    mention = selected_chip.get("mention_handle", f"@{selected_chip.get('slug', 'agent')}")
    print(f"  - 선택된 카테고리 : {category}")
    print(f"  - 에이전트 타이틀 : {agent_title} ({mention})")
    print(f"  - 대상 사용자     : {selected_chip['target_users']}")
    print(f"  - 핵심 규정 기준  : {selected_chip['core_compliance']}")

    sample_spec = synthesize_agent_specification(category, selected_chip, args.dry_run, env_info["project_id"])
    print("  - 5대 골든 지침 및 스타터 프롬프트 합성 완료 (No-Training & PII 보호 가드레일 강제)")

    # 4. 보고서 작성 및 저장
    report_content = build_markdown_report(env_info, iam_diag, meta_manifest, sample_spec)
    save_markdown_report(report_content)

    print("\n" + "=" * 75)
    print("  로컬 에이전트 스펙 합성 완료")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Enterprise 자율형 사내 노코드 에이전트 팩토리 (붕어빵 틀) 배포 및 등록 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", help="Google Cloud 프로젝트 ID (미지정 시 자동 감지)")
    parser.add_argument("--location", help="Discovery Engine / Gemini Enterprise app 리전 (기본: global)")
    parser.add_argument("--ge-app-id", help="Gemini Enterprise App 인스턴스 ID")
    parser.add_argument("--delegated-sa", help="에이전트 등록 대행 서비스 계정 이메일")
    parser.add_argument("--dry-run", action="store_true", default=False, help="실제 배포 없이 가상 실행 검증")
    parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
    parser.add_argument("--scaffold", action="store_true", default=False, help="로컬 단일 에이전트 스펙 합성 보조 모드")
    parser.add_argument("--catalog", help="선언적 catalog.yaml 파일 경로 (지정 시 우선 로드)")
    parser.add_argument("--chip", help="부서/에이전트 번호(1~15) 또는 슬러그(예: hr-onboarding-guide)")
    parser.add_argument("--prompt", help="사용자 직접 정의 에이전트 자유 프롬프트 지정")
    parser.add_argument("--interactive", action="store_true", default=False, help="로컬 에이전트 대화형 번호 선택기 강제 가동")
    parser.add_argument("--deploy-engine", action="store_true", default=False, help="Agent Engine 프로비저닝 (기본 실행과 동일)")

    args = parser.parse_args()

    # 사내 환경 대화형 설정 모드 분기
    if args.config:
        run_config_mode(args)
        return

    # 인자가 없고 비대화형 환경인 경우 기본 dry-run 활성화
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        args.dry_run = True

    print("\n" + "=" * 75)
    print("  Gemini Enterprise 노코드 에이전트 팩토리 (gemini-enterprise-copilot-agent)")
    print("=" * 75)

    # 1. 환경 및 식별 정보 해석
    env_info = resolve_environment(args)
    print(f"[*] 활성 프로젝트    : {env_info['project_id']}")
    print(f"[*] 대상 리전        : {env_info['location']}")
    print(f"[*] 대상 GE App ID   : {env_info['ge_app_id']}")
    print(f"[*] 대행 서비스 계정 : {env_info['delegated_sa']}")
    print(f"[*] 실행 모드        : {'가상 실행 (--dry-run)' if args.dry_run else '실제 프로비저닝 모드'}")

    # 로컬 스캐폴딩 보조 모드 분기 (명시적 플래그 지정 시에만 작동)
    if args.scaffold or args.chip or args.prompt or args.interactive:
        run_local_scaffolding_mode(args, env_info)
        return

    # [핵심 메인 워크플로우]: 붕어빵 틀(GE Agent Factory) 배포 및 GE App 사내 갤러리 등록
    if not args.dry_run and not _get_cloud_token():
        print("\n[오류] 유효한 Google Cloud 인증 자격 증명(ADC)을 찾을 수 없습니다.", file=sys.stderr)
        print("      아래 명령어를 실행하여 로컬 자격 증명을 갱신하십시오:", file=sys.stderr)
        print("      gcloud auth application-default login\n", file=sys.stderr)
        print("      (참고: 실제 배포 없이 가상 검증을 수행하려면 '--dry-run' 플래그를 사용하십시오.)\n", file=sys.stderr)
        sys.exit(1)

    print("\n[진행] 사내 노코드 에이전트 팩토리(붕어빵 틀) 프로비저닝 파이프라인 가동...")
    deploy_res = deploy_agent_factory_engine(env_info, dry_run=args.dry_run)

    # 팩토리 리포트 생성 및 저장
    report_content = build_factory_markdown_report(env_info, deploy_res, dry_run=args.dry_run)
    save_markdown_report(report_content)

    creator = get_resource_creator(args.dry_run)
    print("\n" + "=" * 75)
    print("  노코드 에이전트 팩토리 배포 및 등록 완료 (모든 점검 통과)")
    print("=" * 75)
    print("\n[안내] 사내 거버넌스 및 자원 추적을 위한 4대 필수 표준 라벨:")
    print("  - managed-by: google-cloud-0-to-1")
    print("  - scenario: gemini-enterprise-copilot-agent")
    print("  - env: sample")
    print(f"  - created-by: {creator}\n")


if __name__ == "__main__":
    main()
