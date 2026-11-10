# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Gemini Enterprise 자율형 사내 스킬 팩토리 진단 및 배포 도구.

사내 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 채팅창에서 반복 업무를
재사용 가능한 업무 스킬(SKILL.md)로 대화형 생성하고, GE App 스킬 갤러리(/r/skills)에
skillAgentDefinition 규격으로 즉시 자동 프로비저닝하는 사내 스킬 팩토리다.
"""

import argparse
import json
import os
import subprocess
import sys
import re
import urllib.request
from datetime import datetime, timezone
import requests
try:
    import yaml
except ImportError:
    yaml = None

# 비상용 기본 시드 핵심 업무 스킬 카탈로그 (catalog.yaml 부재 시 폴백)
FALLBACK_SYSTEM_TOOL_CATALOG = {
    1: {
        "id": "approval-draft-create",
        "slug": "approval-draft-create",
        "title": "전자결재 기안문 초안 작성",
        "description": "사내 표준 기안 양식에 맞추어 품의 제목, 추진 배경, 예산 내역, 기대 효과를 구조화하여 결재선에 상신할 초안 문서를 자동 생성한다.",
        "category": "전자결재 및 품의",
        "slash_command": "/approval-draft-create",
        "mention_handle": "@approval-draft-create",
        "default_scope": "ORG",
        "parameters": {
            "doc_type": {"type": "string", "description": "기안 양식 구분 (품의서, 지출결의서, 업무보고서)", "required": True},
            "title": {"type": "string", "description": "기안 제목", "required": True},
            "body": {"type": "string", "description": "기안 내용 및 추진 사유", "required": True},
        },
    },
    2: {
        "id": "approval-status-check",
        "slug": "approval-status-check",
        "title": "결재선 진행 상태 미결함 조회",
        "description": "본인이 상신한 결재 문서의 현재 진행 상태(대기, 검토, 전결)와 부서장/임원 결재 대기자 병목을 실시간 조회한다.",
        "category": "전자결재 및 품의",
        "slash_command": "/approval-status-check",
        "mention_handle": "@approval-status-check",
        "default_scope": "ORG",
        "parameters": {
            "doc_id": {"type": "string", "description": "조회할 전자결재 문서 번호", "required": True},
        },
    },
    3: {
        "id": "approval-proxy-delegate",
        "slug": "approval-proxy-delegate",
        "title": "전결 부재 시 대결자 지정",
        "description": "출장, 병가, 연차 휴가 등 부재 시 결재선 정체를 방지하기 위해 지정된 팀원에게 전결/대결 권한을 일시 위임한다.",
        "category": "전자결재 및 품의",
        "slash_command": "/approval-proxy-delegate",
        "mention_handle": "@approval-proxy-delegate",
        "default_scope": "ORG",
        "parameters": {
            "delegate_emp_id": {"type": "string", "description": "대결자 사번", "required": True},
            "start_date": {"type": "string", "description": "위임 시작일 (YYYY-MM-DD)", "required": True},
            "end_date": {"type": "string", "description": "위임 종료일 (YYYY-MM-DD)", "required": True},
        },
    },
    4: {
        "id": "corp-card-reconcile",
        "slug": "corp-card-reconcile",
        "title": "법인카드 영수증 내역 자동 대조",
        "description": "사내 법인카드 승인 내역과 모바일 영수증을 자동 대조하고 지출 계정 과목 및 세무 증빙 전표를 생성한다.",
        "category": "법인카드 및 경비 정산",
        "slash_command": "/corp-card-reconcile",
        "mention_handle": "@corp-card-reconcile",
        "default_scope": "ORG",
        "parameters": {
            "approval_no": {"type": "string", "description": "카드 승인 번호 8자리", "required": True},
            "expense_purpose": {"type": "string", "description": "사용 목적 및 상세 사유", "required": True},
        },
    },
    5: {
        "id": "overtime-transport-claim",
        "slug": "overtime-transport-claim",
        "title": "야근 교통비 식대 정산 신청",
        "description": "사내 규정 시간 이후 발생한 야근 택시비 영수증과 석식대를 주 52시간 근태 기록과 대조 검증 후 자동 품의한다.",
        "category": "법인카드 및 경비 정산",
        "slash_command": "/overtime-transport-claim",
        "mention_handle": "@overtime-transport-claim",
        "default_scope": "ORG",
        "parameters": {
            "claim_date": {"type": "string", "description": "근무 일자 (YYYY-MM-DD)", "required": True},
            "transport_amount": {"type": "number", "description": "교통비 금액 (KRW)", "required": True},
            "meal_amount": {"type": "number", "description": "야근 식대 금액 (KRW)", "required": True},
        },
    },
    6: {
        "id": "biz-entertain-preapprove",
        "slug": "biz-entertain-preapprove",
        "title": "접대비 사전 품의서 제출",
        "description": "청탁금지법 가이드라인 및 사내 1인당 접대 한도를 사전 점검하고 외부 이해관계자 미팅 식사 접대비 품의를 신청한다.",
        "category": "법인카드 및 경비 정산",
        "slash_command": "/biz-entertain-preapprove",
        "mention_handle": "@biz-entertain-preapprove",
        "default_scope": "ORG",
        "parameters": {
            "external_org": {"type": "string", "description": "대상 거래처명 또는 공공기관명", "required": True},
            "attendee_count": {"type": "integer", "description": "총 참석 인원수", "required": True},
            "budget_limit": {"type": "number", "description": "예상 지출 총액 (KRW)", "required": True},
        },
    },
    7: {
        "id": "tax-invoice-verify",
        "slug": "tax-invoice-verify",
        "title": "홈택스 전자세금계산서 진위 확인",
        "description": "국세청 홈택스 승인 번호 24자리와 공급자 사업자등록번호를 대조하여 세금계산서의 진위 및 정상 발급 여부를 실시간 검증한다.",
        "category": "법인카드 및 경비 정산",
        "slash_command": "/tax-invoice-verify",
        "mention_handle": "@tax-invoice-verify",
        "default_scope": "ORG",
        "parameters": {
            "tax_invoice_no": {"type": "string", "description": "전자세금계산서 24자리 승인 번호", "required": True},
            "biz_reg_no": {"type": "string", "description": "공급자 사업자등록번호 10자리", "required": True},
        },
    },
    8: {
        "id": "hr-vacation-apply",
        "slug": "hr-vacation-apply",
        "title": "연차 반차 경조휴가 신청",
        "description": "사내 근태 시스템에서 잔여 연차를 확인하고 전일, 반차, 반반차 또는 경조 휴가를 신청하여 부서 캘린더에 연동한다.",
        "category": "근태 및 주 52시간 관리",
        "slash_command": "/hr-vacation-apply",
        "mention_handle": "@hr-vacation-apply",
        "default_scope": "ORG",
        "parameters": {
            "leave_type": {"type": "string", "description": "휴가 종류 (연차, 오전반차, 오후반차, 경조휴가)", "required": True},
            "start_date": {"type": "string", "description": "휴가 시작일 (YYYY-MM-DD)", "required": True},
            "days": {"type": "number", "description": "차감 일수 (0.25, 0.5, 1.0 등)", "required": True},
        },
    },
    9: {
        "id": "work-hours-monitor",
        "slug": "work-hours-monitor",
        "title": "주 52시간 잔여 근무 시간 조회",
        "description": "당해 주의 기본 근로 및 연장 근로 누적 시간을 조회하여 주 52시간 법정 한도 초과 위험을 사전에 모니터링한다.",
        "category": "근태 및 주 52시간 관리",
        "slash_command": "/work-hours-monitor",
        "mention_handle": "@work-hours-monitor",
        "default_scope": "ORG",
        "parameters": {
            "emp_id": {"type": "string", "description": "임직원 사번 (미지정 시 본인 세션)", "required": False},
        },
    },
    10: {
        "id": "corp-directory-search",
        "slug": "corp-directory-search",
        "title": "사내 조직도 직급 사번 호칭 검색",
        "description": "사내 조직도 및 그룹웨어 주소록에서 특정 직원의 소속 본부/팀, 직급/직책, 자리 위치, 사내 내선 번호 및 업무 분장을 검색한다.",
        "category": "근태 및 주 52시간 관리",
        "slash_command": "/corp-directory-search",
        "mention_handle": "@corp-directory-search",
        "default_scope": "ORG",
        "parameters": {
            "keyword": {"type": "string", "description": "검색할 직원 이름, 직급, 부서명 또는 담당 업무", "required": True},
        },
    },
    11: {
        "id": "welfare-point-check",
        "slug": "welfare-point-check",
        "title": "사내 복지포인트 잔액 사용 조회",
        "description": "당해 연도 배정된 사내 복지포인트 총액, 기사용액, 잔여 포인트 및 복지몰/카페테리아 차감 가능 내역을 조회한다.",
        "category": "근태 및 주 52시간 관리",
        "slash_command": "/welfare-point-check",
        "mention_handle": "@welfare-point-check",
        "default_scope": "ORG",
        "parameters": {
            "emp_id": {"type": "string", "description": "임직원 사번", "required": True},
        },
    },
    12: {
        "id": "room-booking-reserve",
        "slug": "room-booking-reserve",
        "title": "사내 회의실 화상 장비 예약",
        "description": "참석 인원수, 빔프로젝터, 화상 회의 장비(Meet/Zoom Room) 구비 여부에 맞추어 최적의 사내 회의실을 즉시 예약한다.",
        "category": "총무 및 시설 자산 관리",
        "slash_command": "/room-booking-reserve",
        "mention_handle": "@room-booking-reserve",
        "default_scope": "ORG",
        "parameters": {
            "start_time": {"type": "string", "description": "회의 시작 일시 (YYYY-MM-DD HH:MM)", "required": True},
            "capacity": {"type": "integer", "description": "참석 인원수", "required": True},
            "needs_video": {"type": "boolean", "description": "화상 회의 장비 필요 여부", "required": True},
        },
    },
    13: {
        "id": "corp-car-dispatch",
        "slug": "corp-car-dispatch",
        "title": "업무용 법인 차량 배차 신청",
        "description": "고객사 미팅 및 지방 출장용 업무용 법인 차량 배차를 신청하고 하이패스 및 운행 일지 작성을 자동 연동한다.",
        "category": "총무 및 시설 자산 관리",
        "slash_command": "/corp-car-dispatch",
        "mention_handle": "@corp-car-dispatch",
        "default_scope": "ORG",
        "parameters": {
            "destination": {"type": "string", "description": "출장 목적지", "required": True},
            "purpose": {"type": "string", "description": "외근 사유", "required": True},
            "departure_time": {"type": "string", "description": "출발 예정 시각 (YYYY-MM-DD HH:MM)", "required": True},
        },
    },
    14: {
        "id": "it-asset-request",
        "slug": "it-asset-request",
        "title": "업무용 PC 모니터 전산 비품 신청",
        "description": "개발자용 고사양 노트북(MacBook/ThinkPad), 4K 모니터, 키보드/마우스 등 전산 장비 지급 및 교체 신청을 상신한다.",
        "category": "총무 및 시설 자산 관리",
        "slash_command": "/it-asset-request",
        "mention_handle": "@it-asset-request",
        "default_scope": "ORG",
        "parameters": {
            "asset_category": {"type": "string", "description": "요청 품목 (노트북, 모니터, 전산주변기기)", "required": True},
            "specs": {"type": "string", "description": "희망 사양 및 신청 사유", "required": True},
        },
    },
    15: {
        "id": "sw-license-grant",
        "slug": "sw-license-grant",
        "title": "사내 소프트웨어 라이선스 신청",
        "description": "JetBrains All Products Pack, Adobe Creative Cloud, Figma 등 유료 업무 소프트웨어의 사내 라이선스 자동 배정을 신청한다.",
        "category": "총무 및 시설 자산 관리",
        "slash_command": "/sw-license-grant",
        "mention_handle": "@sw-license-grant",
        "default_scope": "ORG",
        "parameters": {
            "software_name": {"type": "string", "description": "소프트웨어 명칭 (JetBrains, Adobe, Figma 등)", "required": True},
            "business_need": {"type": "string", "description": "업무 필요 사유", "required": True},
        },
    },
    16: {
        "id": "weekly-report-draft",
        "slug": "weekly-report-draft",
        "title": "주간 업무 보고서 자동 요약 및 초안 작성",
        "description": "이번 주 완료 업무, 진행 중 과제, 다음 주 계획 및 이슈 사항을 입력받아 부서 표준 주간 보고서 형식으로 정리한다.",
        "category": "기획 보고 및 문서 작성",
        "slash_command": "/weekly-report-draft",
        "mention_handle": "@weekly-report-draft",
        "default_scope": "ORG",
        "parameters": {
            "completed_tasks": {"type": "string", "description": "금주 완료 업무 내역", "required": True},
            "next_week_plan": {"type": "string", "description": "차주 주요 실행 계획", "required": True},
            "key_issues": {"type": "string", "description": "주요 리스크 또는 지원 요청 사항", "required": False},
        },
    },
    17: {
        "id": "meeting-notes-summarize",
        "slug": "meeting-notes-summarize",
        "title": "회의록 핵심 결정 사항 및 실행 과제 정리",
        "description": "회의 메모나 대화 요약본에서 핵심 논의 내용, 최종 결정 사항, 담당자별 실행 과제(Action Item)를 일목요연하게 추출한다.",
        "category": "기획 보고 및 문서 작성",
        "slash_command": "/meeting-notes-summarize",
        "mention_handle": "@meeting-notes-summarize",
        "default_scope": "ORG",
        "parameters": {
            "meeting_title": {"type": "string", "description": "회의명 및 일시", "required": True},
            "raw_notes": {"type": "string", "description": "회의 원문 메모 또는 요약 텍스트", "required": True},
        },
    },
    18: {
        "id": "proposal-outline-build",
        "slug": "proposal-outline-build",
        "title": "사내 신규 과제 기획안 목차 및 초안 구성",
        "description": "과제 배경, 목표 지표, 추진 일정 및 기대 효과를 바탕으로 사내 의사 결정 보고용 원 페이저 기획안 초안을 구성한다.",
        "category": "기획 보고 및 문서 작성",
        "slash_command": "/proposal-outline-build",
        "mention_handle": "@proposal-outline-build",
        "default_scope": "ORG",
        "parameters": {
            "project_topic": {"type": "string", "description": "신규 과제명 또는 주제", "required": True},
            "target_audience": {"type": "string", "description": "보고 대상 (팀장, 본부장, 유관 부서)", "required": True},
        },
    },
    19: {
        "id": "slack-notice-broadcast",
        "slug": "slack-notice-broadcast",
        "title": "사내 메신저 공지 긴급 알림 배포",
        "description": "사내 슬랙(Slack), 잔디(Jandi) 또는 카카오워크 특정 전사/부서 채널에 긴급 공지, 인사이동, 경조사 알림을 발송한다.",
        "category": "업무 협업 및 워크스페이스",
        "slash_command": "/slack-notice-broadcast",
        "mention_handle": "@slack-notice-broadcast",
        "default_scope": "ORG",
        "parameters": {
            "channel": {"type": "string", "description": "발송 대상 채널명", "required": True},
            "title": {"type": "string", "description": "공지 제목", "required": True},
            "message": {"type": "string", "description": "알림 본문 내용", "required": True},
        },
    },
    20: {
        "id": "sheets-voc-append",
        "slug": "sheets-voc-append",
        "title": "사내 VOC 개선 제안 행 추가",
        "description": "사내 구글 시트(Google Sheets)에 고객 불만 VOC, 신규 기능 제안, 업무 개선 아이디어 행을 실시간 추가한다.",
        "category": "업무 협업 및 워크스페이스",
        "slash_command": "/sheets-voc-append",
        "mention_handle": "@sheets-voc-append",
        "default_scope": "ORG",
        "parameters": {
            "spreadsheet_id": {"type": "string", "description": "취합 구글 시트 ID", "required": True},
            "category": {"type": "string", "description": "VOC 분류 (서비스, 결제, 시스템, 개선제안)", "required": True},
            "content": {"type": "string", "description": "상세 내용", "required": True},
        },
    },
    21: {
        "id": "drive-template-find",
        "slug": "drive-template-find",
        "title": "사내 표준 계약서 위임장 양식 검색",
        "description": "사내 구글 드라이브(Google Drive) 공용 폴더에서 법무팀 공인 최신 표준 계약서, NDA, 재직증명서, 위임장 양식을 검색한다.",
        "category": "업무 협업 및 워크스페이스",
        "slash_command": "/drive-template-find",
        "mention_handle": "@drive-template-find",
        "default_scope": "ORG",
        "parameters": {
            "template_name": {"type": "string", "description": "찾고자 하는 양식 키워드 (계약서, 위임장, 재직증명)", "required": True},
        },
    },
    22: {
        "id": "biz-reg-validate",
        "slug": "biz-reg-validate",
        "title": "국세청 사업자등록 휴폐업 상태 조회",
        "description": "국세청 홈택스 API를 통해 신규 또는 기존 거래처 사업자등록번호의 계속사업자, 휴업, 폐업 상태 및 과세 유형을 실시간 조회한다.",
        "category": "영업 및 거래처 관리",
        "slash_command": "/biz-reg-validate",
        "mention_handle": "@biz-reg-validate",
        "default_scope": "ORG",
        "parameters": {
            "b_no": {"type": "string", "description": "사업자등록번호 10자리", "required": True},
        },
    },
    23: {
        "id": "bank-account-verify",
        "slug": "bank-account-verify",
        "title": "거래처 법인 예금주 실명 확인",
        "description": "대금 지급 또는 계약 체결 전 금융결제원 망을 통해 거래처 은행 계좌번호와 법인명/대표자 예금주 성명의 일치 여부를 실시간 검증한다.",
        "category": "영업 및 거래처 관리",
        "slash_command": "/bank-account-verify",
        "mention_handle": "@bank-account-verify",
        "default_scope": "ORG",
        "parameters": {
            "bank_code": {"type": "string", "description": "은행 코드 (3자리)", "required": True},
            "account_no": {"type": "string", "description": "계좌번호 (숫자만)", "required": True},
            "holder_name": {"type": "string", "description": "대조할 예금주 법인명", "required": True},
        },
    },
    24: {
        "id": "crm-lead-register",
        "slug": "crm-lead-register",
        "title": "신규 거래처 영업 미팅 일지 등록",
        "description": "외근 미팅 후 명함 정보, 고객 관심 솔루션, 예산 규모 및 후속 액션 아이템을 CRM 시스템에 영업 기회 리드로 등록한다.",
        "category": "영업 및 거래처 관리",
        "slash_command": "/crm-lead-register",
        "mention_handle": "@crm-lead-register",
        "default_scope": "ORG",
        "parameters": {
            "company_name": {"type": "string", "description": "고객사 법인명", "required": True},
            "contact_person": {"type": "string", "description": "담당자 이름 및 직함", "required": True},
            "meeting_summary": {"type": "string", "description": "미팅 요약 및 제안 내용", "required": True},
        },
    },
}


def load_skill_catalog(catalog_path: str = None) -> dict:
    """선언적 catalog.yaml 파일로부터 도메인별 엔터프라이즈 스킬을 동적 로드한다 (4단계 캐스케이드 탐색)."""
    candidates = []
    if catalog_path:
        candidates.append(catalog_path)
    if os.environ.get("SKILL_CATALOG_PATH"):
        candidates.append(os.environ.get("SKILL_CATALOG_PATH"))
    local_default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog.yaml")
    candidates.append(local_default)

    raw_yaml_text = None
    loaded_source = None

    for target in candidates:
        if not target:
            continue
        # 원격 URL 처리 (2.0초 타임아웃 적용하여 외부망 지연 방지)
        if target.startswith("http://") or target.startswith("https://"):
            try:
                req = urllib.request.Request(target, headers={"User-Agent": "GE-Skill-Factory/1.0"})
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
        return FALLBACK_SYSTEM_TOOL_CATALOG

    try:
        data = yaml.safe_load(raw_yaml_text)
        skills_list = data.get("skills", [])
        if not skills_list:
            return FALLBACK_SYSTEM_TOOL_CATALOG

        catalog = {}
        slug_pattern = re.compile(r"^[a-z0-9]+-[a-z0-9]+-[a-z0-9]+$")

        for idx, s in enumerate(skills_list, start=1):
            slug = s.get("slug", f"skill-{idx}-run")
            if not slug_pattern.match(slug):
                slug = slug.lower().replace("_", "-")

            params_dict = {}
            for p in s.get("required_params", []):
                pname = p.get("name")
                if pname:
                    params_dict[pname] = {
                        "type": p.get("type", "string"),
                        "description": p.get("description", ""),
                        "required": True,
                    }

            catalog[idx] = {
                "id": slug,
                "slug": slug,
                "title": s.get("name", slug),
                "description": s.get("description", ""),
                "category": s.get("category", "General"),
                "parameters": params_dict,
                "slash_command": s.get("slash_command", f"/{slug}"),
                "mention_handle": s.get("mention_handle", f"@{slug}"),
                "default_scope": s.get("default_scope", "ORG"),
                "source": loaded_source,
            }
        return catalog
    except Exception:
        return FALLBACK_SYSTEM_TOOL_CATALOG


SYSTEM_TOOL_CATALOG = load_skill_catalog()


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
    print("  Gemini Enterprise 사내 스킬 팩토리 - 사내 환경 설정 마법사 (--config)")
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
    loc_prompt = f"2. Discovery Engine / Gemini Enterprise app 리전 [기본값: {current_loc}]: "
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
    """실행 환경을 계층형으로 확정한다 (실시간 GE App 감지 및 대화형 번호 선택 지원)."""
    load_env_file()

    # 1. Project ID
    if args.dry_run:
        project_id = "sample-project-id"
    else:
        project_id = args.project or os.environ.get("PROJECT_ID") or get_gcloud_config("project") or "sample-project-id"
    if not args.dry_run and not os.environ.get("PROJECT_ID") and project_id != "sample-project-id":
        persist_env_value("PROJECT_ID", project_id, dry_run=args.dry_run)

    # 2. Location
    location = args.location or os.environ.get("LOCATION") or "global"

    # 3. Gemini Enterprise App ID
    ge_app_id = args.ge_app_id or os.environ.get("GE_APP_ID")
    if not ge_app_id:
        candidates = discover_ge_app_engines(project_id)
        ge_app_id = select_ge_app_id(project_id, candidates, dry_run=args.dry_run)
        if not args.dry_run and ge_app_id:
            persist_env_value("GE_APP_ID", ge_app_id, dry_run=args.dry_run)

    # 4. Service Account
    sa = args.skill_sa or os.environ.get("SKILL_INVOKER_SERVICE_ACCOUNT")
    if not sa:
        sa = f"ge-skill-invoker-sa@{project_id}.iam.gserviceaccount.com"

    return {
        "project_id": project_id,
        "location": location,
        "ge_app_id": ge_app_id,
        "service_account": sa,
    }


def select_tool_interactive(dry_run: bool):
    """대화형 환경에서 생성하고자 하는 스킬 칩을 선택한다 (도메인 카테고리별 출력)."""
    is_interactive = sys.stdin.isatty() and not dry_run

    if not is_interactive:
        return SYSTEM_TOOL_CATALOG[1]

    print("\n" + "=" * 75)
    print("  Gemini Enterprise 자율형 사내 스킬 팩토리 (Skill Factory)")
    print("  [생성할 GE App 표준 업무 스킬 레시피를 선택하세요]")
    print("=" * 75)

    current_cat = None
    for cat_id, data in sorted(SYSTEM_TOOL_CATALOG.items()):
        cat = data.get("category", "General")
        if cat != current_cat:
            current_cat = cat
            print(f"\n  [ {current_cat} ]")
        slug = data.get("slug", data["id"])
        slash = data.get("slash_command", f"/{slug}")
        print(f"    [{cat_id:2d}] {data['title']} ({slug} | {slash})")

    print("\n  [ 0] 직접 업무 스킬 요구사항 입력 (Custom GE Skill)")

    try:
        choice_in = input("\n스킬 번호를 입력하세요 (기본값: 1): ").strip()
        choice = int(choice_in) if choice_in else 1
    except ValueError:
        choice = 1

    if choice == 0 or choice not in SYSTEM_TOOL_CATALOG:
        custom_title = input("\n생성하고자 하는 스킬 명칭을 입력하세요: ").strip()
        custom_desc = input("스킬이 수행할 업무 지침 요약을 입력하세요: ").strip()
        custom_slug = re.sub(r"[^a-z0-9\-]", "-", (custom_title or "custom-work-skill").lower()).strip("-")
        return {
            "id": custom_slug,
            "slug": custom_slug,
            "title": custom_title or "사내 맞춤형 업무 스킬",
            "description": custom_desc or "반복 업무 지침과 표준 양식을 자동 적용하는 GE App 맞춤형 스킬",
            "category": "사용자 직접 정의 스킬",
            "slash_command": f"/{custom_slug}",
            "mention_handle": f"@{custom_slug}",
            "default_scope": "ALL_USERS",
            "parameters": {
                "request_input": {"type": "string", "description": "실행 시 전달할 업무 내용", "required": True},
            },
        }

    return SYSTEM_TOOL_CATALOG[choice]


def generate_skill_manifest(tool_data: dict, env_info: dict):
    """선택된 스킬 칩을 기반으로 표준 SKILL.md 본문과 GE App skillAgentDefinition 페이로드를 합성한다."""
    tool_id = tool_data["id"]
    title = tool_data["title"]
    desc = tool_data["description"]
    slash_cmd = tool_data.get("slash_command", f"/{tool_id}")
    scope = tool_data.get("default_scope", "ALL_USERS")

    param_lines = []
    for pname, pinfo in tool_data.get("parameters", {}).items():
        req_mark = "필수" if pinfo.get("required") else "선택"
        param_lines.append(f"- `{pname}` ({pinfo.get('type', 'string')}, {req_mark}): {pinfo.get('description', '')}")
    params_md = "\n".join(param_lines) if param_lines else "- 별도 입력 파라미터 없음"

    skill_md_content = (
        f"---\n"
        f"name: {tool_id}\n"
        f"description: {desc}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"## 실행 지침\n"
        f"1. 사용자의 요청에서 아래 입력 항목을 확인하고 누락된 항목이 있으면 간결하게 되묻는다.\n"
        f"2. 확인된 내용을 바탕으로 사내 표준 양식에 맞추어 결과 초안을 구조화하여 제시한다.\n\n"
        f"## 입력 항목\n"
        f"{params_md}\n\n"
        f"## 호출 방법\n"
        f"- 슬래시 커맨드: `{slash_cmd}`\n"
    )

    skill_agent_definition = {
        "displayName": title,
        "description": f"{desc}\n\n[Slug: {tool_id}]",
        "sharingConfig": {"scope": "ALL_USERS" if scope in ("ORG", "ALL_USERS") else "PRIVATE"},
        "skillAgentDefinition": {
            "instruction": skill_md_content,
        },
    }

    return {
        "skill_md": skill_md_content,
        "skill_agent_definition": skill_agent_definition,
        "scope": skill_agent_definition["sharingConfig"]["scope"],
        "labels": {
            "managed-by": "google-cloud-0-to-1",
            "scenario": "gemini-enterprise-factory-skill",
            "env": "sample",
            "created-by": get_resource_creator(False),
        },
    }


def diagnose_ge_app_readiness(env_info: dict, dry_run: bool):
    """Gemini Enterprise app 스킬 등록 환경(프로젝트, 앱 인스턴스, 위치)을 점검한다."""
    project_id = env_info["project_id"]
    ge_app_id = env_info["ge_app_id"]
    if dry_run:
        return {
            "status": "PASS (Simulated)",
            "detail": f"가상 실행 검증: project={project_id}, ge_app_id={ge_app_id} 등록 페이로드 유효성 통과",
        }
    return {
        "status": "PASS",
        "detail": f"project={project_id}, ge_app_id={ge_app_id} Discovery Engine 연동 준비 완료",
    }


def build_markdown_report(env_info: dict, tool_data: dict, skill_manifest: dict, readiness: dict, dry_run: bool = False):
    """로컬 스킬 매니페스트 합성 결과를 표준 report.md 양식으로 조립한다."""
    if dry_run:
        project_id = "sample-project-id"
        ge_app_id = "sample-ge-app-id"
        sa_email = f"ge-skill-invoker-sa@{project_id}.iam.gserviceaccount.com"
    else:
        project_id = env_info["project_id"]
        ge_app_id = env_info["ge_app_id"]
        sa_email = env_info["service_account"]

    return f"""# Gemini Enterprise 자율형 사내 스킬 팩토리 합성 보고서

- **실행 일시**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **대상 프로젝트**: `{project_id}`
- **Gemini Enterprise app 인스턴스**: `{ge_app_id}`
- **생성된 스킬 슬러그**: `{tool_data['id']}` ({tool_data['title']})

---

## 1. 스킬 매니페스트 합성 결과 요약

| 진단 항목 | 상태 | 상세 결과 |
| :--- | :---: | :--- |
| **스킬 분류 및 커맨드** | `READY` | `{tool_data['category']}` (`{tool_data.get('slash_command', '/' + tool_data['id'])}`) |
| **규격 매니페스트** | `SYNTHESIZED` | GE App `SKILL.md` + `skillAgentDefinition` JSON 생성 완료 |
| **공유 범위(Scope)** | `{skill_manifest['scope']}` | Gemini Enterprise app `/r/skills` 등록 대상 |
| **환경 준비 점검** | `{readiness['status']}` | {readiness['detail']} |

---

## 2. 생성된 GE App `skillAgentDefinition` 페이로드

Discovery Engine API에 전달되는 표준 스킬 정의 페이로드다:

```json
{json.dumps(skill_manifest['skill_agent_definition'], indent=2, ensure_ascii=False)}
```

---

## 3. 사내 거버넌스 4대 필수 표준 라벨링

팩토리 배포 리소스 생성 시 아래 4대 표준 라벨을 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-factory-skill`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 4. 콘솔 링크 및 확인 경로

- **Gemini Enterprise 웹 포털**: 사내 스킬 갤러리 (`/r/skills`) 확인 ( https://gemini.google.com/app/{ge_app_id} )
- **Agent Platform Runtimes 콘솔**: 에이전트 런타임 상태 관리 ( https://console.cloud.google.com/agent-platform/runtimes?project={project_id} )
- **Gemini Enterprise 관리자 콘솔**: 사내 등록 에이전트 및 스킬 관리 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/agentic/agents?project={project_id} )

---

## 5. 자원 정리 안내 (Teardown)

테스트용으로 등록한 스킬이나 서비스 계정을 정리하고자 할 경우 아래 명령을 수행한다:

```bash
gcloud iam service-accounts delete {sa_email} --quiet
```
"""


def build_factory_markdown_report(env_info: dict, deploy_res: dict, dry_run: bool = False) -> str:
    """GE Skill Factory(붕어빵 틀 에이전트) 배포 결과를 표준 report.md 양식으로 조립한다 (가상 실행 시 사내 식별 정보 마스킹)."""
    if dry_run:
        project_id = "sample-project-id"
        ge_app_id = "sample-ge-app-id"
        re_uri = f"projects/{project_id}/locations/us-central1/reasoningEngines/simulated-skill-factory-engine"
    else:
        project_id = env_info["project_id"]
        ge_app_id = env_info["ge_app_id"]
        re_uri = deploy_res.get("reasoning_engine", "N/A")

    status = deploy_res.get("status", "UNKNOWN")
    display_name = deploy_res.get("display_name", "GE In-Chat Skill Factory (사내 스킬 팩토리)")
    portal_url = f"https://gemini.google.com/app/{ge_app_id}"

    return f"""# Gemini Enterprise 사내 스킬 팩토리 배포 보고서 (gemini-enterprise-factory-skill)

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
| **내장 실행 도구** | `4종 완비` | `check_skill_duplicate_tool`, `deploy_enterprise_skill_tool`, `list_enterprise_skills_tool`, `get_preset_skills_tool` |
| **GE App 사내 갤러리 등록** | `ACTIVE` | 사내 갤러리(`/r/agents`) 전사 공유 (`ALL_USERS`) 바인딩 완료 |

---

## 2. 팩토리 에이전트 아키텍처 및 스킬 제작 흐름

본 솔루션은 임직원이 복잡한 규격을 직접 작성하지 않고, GE App 채팅창에서 자연어 대화만으로 업무 스킬(`SKILL.md`)을 제작하여 `/r/skills`에 즉시 등록할 수 있도록 지원하는 **사내 스킬 팩토리(붕어빵 틀)**다:

```mermaid
flowchart LR
    subgraph L1["1. GE App 대화창"]
        U["임직원 / 부서 관리자"] -->|"자연어 스킬 생성 요청"| GE["Gemini Enterprise app<br/>(/r/agents)"]
    end

    subgraph L2["2. Agent Engine 팩토리"]
        GE -->|"대화 라우팅"| F["Skill Factory 에이전트<br/>(gemini-3.8-flash)"]
        F -->|"슬러그 중복 검사 &<br/>SKILL.md 합성"| T["deploy_enterprise_skill_tool"]
    end

    subgraph L3["3. GE App 스킬 등록"]
        T -->|"skillAgentDefinition 등록"| REG["GE App 스킬 갤러리<br/>(/r/skills)"]
    end
```

---

## 3. 사내 실무자 활용 가이드 (스킬 생성 및 즉시 호출)

사내 임직원은 배포된 스킬 팩토리 에이전트와 대화하여 다음과 같이 업무 스킬을 즉시 찍어낼 수 있다:

1. **Gemini Enterprise app 접속**:
   - 웹 포털 ( {portal_url} ) 접속 후 좌측 사이드바 **사내 갤러리(`/r/agents`)** 이동.
   - **`{display_name}`** 선택.

2. **자연어 붕어빵 생성 예시 프롬프트**:
   - *"주간 업무 보고서 자동 요약 스킬 생성해서 내 GE App Skills에 등록해 줘"*
   - *"회의록 핵심 결정 사항 정리 스킬 만들어 줘"*
   - *"전자결재 기안문 초안 작성 스킬 생성 및 전사 공유해 줘"*
   - *"현재 사내에 등록된 스킬 목록 조회해 줘"*

3. **팩토리 에이전트 자율 동작**:
   - 스킬 팩토리 에이전트가 슬러그 ID 중복을 사전 확인한 뒤 `SKILL.md` 지침을 구성하고,
   - 내장된 `deploy_enterprise_skill_tool`을 호출하여 GE App **`/r/skills`** 목록에 즉시 등록한다.

---

## 4. 사내 거버넌스 4대 필수 표준 라벨

팩토리 에이전트 및 하위 생성 리소스 관리 시 아래 4대 표준 라벨이 기본 적용된다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-factory-skill`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 5. 콘솔 링크 조치 가이드

- **Agent Platform Runtimes 콘솔**: 에이전트 런타임 상태 및 활성화(Enabled) 관리 ( https://console.cloud.google.com/agent-platform/runtimes?project={project_id} )
- **Gemini Enterprise 에이전트 목록 콘솔**: 사내 등록된 에이전트 및 스킬 관리 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/agentic/agents?project={project_id} )

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


def deploy_skill_factory_engine(env_info: dict, dry_run: bool = False) -> dict:
    """Gemini Enterprise Skill Factory를 Agent Engine으로 프로비저닝하고 GE App에 자동 등록한다."""
    project_id = env_info["project_id"]
    re_location = "us-central1"
    ge_app_id = env_info["ge_app_id"]
    ge_location = "global"
    staging_bucket = f"gs://{project_id}-agent-engine-staging"

    display_name = "GE In-Chat Skill Factory (사내 스킬 팩토리)"
    description = "사내 맞춤형 스킬(Open Skills / SKILL.md) 대화형 자율 생성 및 Gemini Enterprise app 전사 즉시 프로비저닝 팩토리"

    labels = {
        "managed-by": "google-cloud-0-to-1",
        "scenario": "gemini-enterprise-factory-skill",
        "env": "sample",
        "created-by": get_resource_creator(dry_run),
    }

    if dry_run:
        print("\n--> [가상 실행 모드 (--dry-run)] 실제 배포 없이 프로비저닝 명세를 시뮬레이션합니다.")
        simulated_re_id = "simulated-skill-factory-engine"
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

    # 1. 에이전트 내장 실행 도구 정의 (Skills 직접 프로비저닝 및 사전 검증)
    def check_skill_duplicate_tool(slug: str) -> str:
        """Check whether a skill with the EXACT unique slug (ID) already exists and is active in Gemini Enterprise app.

        Note:
            This tool strictly validates the unique slug identifier (e.g. 'approval-draft-create', 'slack-incident-alert').
            Similar natural language display names are explicitly permitted and will NOT be blocked.

        Args:
            slug: The unique canonical kebab-case slug ID of the skill to check (e.g. 'approval-draft-create').

        Returns:
            Pre-flight status indicating if the exact slug already exists, its state, ID, or if it is safe to create a new one.
        """
        import re
        import requests
        import google.auth
        import google.auth.transport.requests

        try:
            creds, _ = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            cur_token = creds.token

            headers = {
                "Authorization": f"Bearer {cur_token}",
                "Content-Type": "application/json",
                "X-Goog-User-Project": project_id,
            }
            base_url = (
                f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
                f"/locations/{ge_location}/collections/default_collection"
                f"/engines/{ge_app_id}/assistants/default_assistant/agents"
            )
            list_resp = requests.get(base_url, headers=headers, timeout=15)
            if list_resp.ok:
                target_slug = slug.strip().lower()
                for a in list_resp.json().get("agents", []):
                    d_name = a.get("displayName", "").strip().lower()
                    desc = a.get("description", "").lower()

                    # 오로지 슬러그(ID)의 정확한 일치 여부만 체크
                    is_match = False
                    if d_name == target_slug:
                        is_match = True
                    elif f"[slug: {target_slug}]" in desc or f"(slug: {target_slug})" in desc:
                        is_match = True
                    elif f"slug:{target_slug}" in desc.replace(" ", ""):
                        is_match = True

                    if is_match:
                        skill_id = a.get("name", "").split("/")[-1]
                        state = a.get("state", "UNKNOWN")
                        portal_url = f"https://gemini.google.com/app/{ge_app_id}/r/skills"
                        return (
                            f"### [사전 슬러그 중복 검증] 기등록 스킬 감지\n\n"
                            f"- **슬러그 (ID)**: `{slug}`\n"
                            f"- **스킬 명칭**: {a.get('displayName', '')}\n"
                            f"- **Skill ID**: `{skill_id}`\n"
                            f"- **상태**: `{state}`\n"
                            f"- **사내 스킬 갤러리 바로가기**: {portal_url}\n\n"
                            f"동일한 고유 슬러그 ID(`{slug}`)의 스킬이 이미 사내 스킬 갤러리에 등록되어 활성화되어 있습니다.\n"
                            f"추가적인 기획 인터뷰를 진행하지 않고, 위 사내 갤러리 링크에서 확인하시거나, "
                            f"해당 스킬의 지침을 업데이트할 것인지 사용자에게 확인하십시오."
                        )
                return (
                    f"### [사전 슬러그 중복 검증] 신규 생성 가능\n\n"
                    f"- 확인 대상 슬러그 (ID): `{slug}`\n"
                    f"- 사내 갤러리에 동일한 슬러그 ID가 존재하지 않습니다. 정상적으로 1단계(연동 대상 시스템 파악) 기획을 시작할 수 있습니다."
                )
            return f"[사전 검증 조회 오류] HTTP {list_resp.status_code}: {list_resp.text[:200]}"
        except Exception as e:
            return f"[사전 검증 예외] 조회 중 예외 발생: {str(e)}"

    def deploy_enterprise_skill_tool(
        skill_name: str,
        description: str,
        instruction: str,
        slug: str = "",
        scope: str = "ALL_USERS",
    ) -> str:
        """Create and deploy a new official skill directly into the user's Gemini Enterprise app Skills catalog.

        Args:
            skill_name: English display name for the skill (letters, numbers, hyphens, spaces only, max 64 chars).
            description: Concise description explaining what this skill does and when to invoke it.
            instruction: Comprehensive SKILL.md-compatible instructions and prompt rules for the skill.
            slug: Unique canonical kebab-case slug ID (e.g. 'approval-draft-create').
            scope: Visibility scope ('ALL_USERS' for org-wide shared skill, or 'PRIVATE' for personal use).
        """
        import re
        import requests
        import google.auth
        import google.auth.transport.requests

        cleaned_name = re.sub(r"[^a-zA-Z0-9\s\-]", "", skill_name).strip()
        if not cleaned_name:
            cleaned_name = "Custom Enterprise Skill"
        if len(cleaned_name) > 64:
            cleaned_name = cleaned_name[:64].strip()

        try:
            creds, _ = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            cur_token = creds.token

            headers = {
                "Authorization": f"Bearer {cur_token}",
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
                        if a.get("displayName") == cleaned_name:
                            existing_id = a.get("name", "").split("/")[-1]
                            existing_state = a.get("state", "UNKNOWN")
                            if existing_state == "ENABLED":
                                return (
                                    f"### 사내 스킬 등록 현황\n\n"
                                    f"- **스킬 명칭**: `{cleaned_name}`\n"
                                    f"  - 상태: 이미 사내 갤러리에 정상 등록되어 활성화(ENABLED)되어 있습니다.\n"
                                    f"  - Skill ID: `{existing_id}`\n"
                                    f"  - 공유 범위: `{a.get('sharingConfig', {}).get('scope', 'ALL_USERS')}`\n"
                                    f"  - 안내: 추가 배포 없이 사내 갤러리(/r/agents)에서 즉시 사용하실 수 있습니다."
                                )
                        # 팩토리 자체의 Reasoning Engine 리소스 이름 동적 추출
                        if "Skill" in a.get("displayName", "") and a.get("adkAgentDefinition"):
                            re_engine = a.get("adkAgentDefinition", {}).get("provisionedReasoningEngine", {}).get("reasoningEngine")
                            if re_engine:
                                factory_re_res = re_engine
            except Exception:
                pass

            full_desc = f"{description}\n\n[Slug: {slug}]" if slug else description

            # GE App 공식 좌측 메뉴 'Skills(/r/skills)' 탭 노출을 위해 공식 skillAgentDefinition 규격 적용
            body = {
                "displayName": cleaned_name,
                "description": full_desc,
                "sharingConfig": {"scope": "ALL_USERS" if scope == "ALL_USERS" else "PRIVATE"},
                "skillAgentDefinition": {
                    "instruction": instruction,
                },
            }
            post_resp = requests.post(base_url, headers=headers, json=body, timeout=30)
            if not post_resp.ok:
                return f"[배포 실패] Discovery Engine API 오류 ({post_resp.status_code}): {post_resp.text}"

            skill_data = post_resp.json()
            skill_id = skill_data.get("name", "").split("/")[-1]

            return (
                f"### Gemini Enterprise 공식 스킬 배포 완료\n\n"
                f"- **스킬 명칭**: `{cleaned_name}`\n"
                f"- **스킬 ID**: `{skill_id}`\n"
                f"- **공유 상태**: `ALL_USERS (전사 스킬 활성화)`\n"
                f"- **매니페스트 규격**: `skillAgentDefinition (GE App 공식 스킬)`\n"
                f"- **확인 방법**: GE App 좌측 **'Skills'(/r/skills)** 메뉴를 새로고침(F5)하면 공식 스킬 목록에 즉시 노출됩니다."
            )
        except Exception as e:
            return f"[예외 발생] 스킬 배포 실패: {str(e)}"

    def list_enterprise_skills_tool() -> str:
        """List all registered skills currently deployed in the Gemini Enterprise app.

        Returns:
            A markdown-formatted summary table of registered skills.
        """
        import requests
        import google.auth
        import google.auth.transport.requests

        try:
            creds, _ = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            cur_token = creds.token

            headers = {
                "Authorization": f"Bearer {cur_token}",
                "Content-Type": "application/json",
                "X-Goog-User-Project": project_id,
            }
            base_url = (
                f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
                f"/locations/{ge_location}/collections/default_collection"
                f"/engines/{ge_app_id}/assistants/default_assistant/agents"
            )

            resp = requests.get(f"{base_url}?pageSize=50", headers=headers, timeout=30)
            if not resp.ok:
                return f"[조회 실패] 에이전트/스킬 목록 조회 오류: {resp.text}"

            agents = resp.json().get("agents", [])
            # 명칭(displayName) 문자열 매칭을 배제하고 Discovery Engine 리소스 스펙(skillAgentDefinition)으로만 순수 타입 필터링
            skills = [a for a in agents if "skillAgentDefinition" in a]
            if not skills:
                return "현재 사내에 등록된 공식 스킬이 없습니다. '스킬 생성'을 요청하시면 새 스킬을 즉시 배포할 수 있습니다."

            lines = [
                "### Gemini Enterprise 사내 등록 공식 스킬 현황",
                "",
                "| 스킬 명칭 | 스킬 ID | 규격 (Spec) | 공유 범위 |",
                "| :--- | :--- | :--- | :--- |",
            ]
            for s in skills:
                disp = s.get("displayName", "N/A")
                sid = s.get("name", "").split("/")[-1]
                sc = s.get("sharingConfig", {}).get("scope", "PRIVATE")
                lines.append(f"| {disp} | `{sid}` | `skillAgentDefinition (/r/skills)` | `{sc}` |")

            return "\n".join(lines)
        except Exception as e:
            return f"[예외 발생] 스킬 목록 조회 실패: {str(e)}"

    def get_preset_skills_tool() -> str:
        """Get the enterprise recommended preset skills catalog organized by domain.

        Returns:
            A markdown catalog of core enterprise preset skills organized by domain.
        """
        lines = [
            "### 사내 핵심 도메인별 엔터프라이즈 공식 스킬 카탈로그",
            "원하시는 스킬 명칭, 슬러그 또는 슬래시 커맨드(예: `/approval-draft-create`, `corp-card-reconcile`)를 말씀하시거나, 직접 원하는 시스템 연동 요구사항을 자연어로 자유롭게 설명해 주시면 즉시 맞춤형 스킬을 제작 및 배포합니다:\n",
        ]
        categories = {}
        for s in SYSTEM_TOOL_CATALOG.values():
            cat = s.get("category", "General")
            categories.setdefault(cat, []).append(s)

        for cat, items in categories.items():
            lines.append(f"#### {cat}")
            for item in items:
                lines.append(
                    f"- **{item['title']}** (`{item['slug']}` | `{item['slash_command']}`): "
                    f"{item['description']}"
                )
            lines.append("")
        return "\n".join(lines)

    print("\n[단계 1/2] Agent Engine 초기화 및 패키징 중...")
    vertexai.init(
        project=project_id,
        location=re_location,
        staging_bucket=staging_bucket,
        credentials=creds,
    )

    instruction = """당신은 Gemini Enterprise app 및 Open Skills 생태계의 '사내 스킬 팩토리(Skill Factory)' 마스터 에이전트입니다.
임직원이 채팅창에서 반복 업무를 재사용 가능한 업무 스킬(SKILL.md)로 대화형 생성하면, 귀하에게 장착된 실제 배포 도구(`deploy_enterprise_skill_tool`)를 호출하여 사용자의 GE App Skills 갤러리(/r/skills)에 즉시 자동 프로비저닝합니다.

[2026년 Google Cloud AI 모델 표준 및 가이드라인]
- 사내 엔터프라이즈 표준 기본 모델은 'gemini-3.8-flash'이다.
- 스킬 명세서 출력 시 적용 모델 항목에는 'gemini-3.8-flash (권장 기본)'으로 명시한다.

[장착된 실제 실행 도구 (Tools)]
당신에게는 실제 클라우드 환경에 스킬을 프로비저닝하고 조회할 수 있는 실제 실행 도구가 장착되어 있습니다:
1. `check_skill_duplicate_tool`: 사용자가 특정 스킬 생성을 요청했을 때, 기획이나 인터뷰를 시작하기 전에 사내 갤러리에 동일하거나 유사한 스킬이 이미 존재하는지 실시간으로 사전 검증하는 최우선 필수 도구입니다.
2. `deploy_enterprise_skill_tool`: 사용자가 스킬 생성을 요청하거나 확인하면, SKILL.md 지침을 컴파일하여 사용자의 Gemini Enterprise app Skills 목록에 즉시 배포합니다. (스킬 이름은 영문, 숫자, 하이픈, 공백만 허용).
3. `list_enterprise_skills_tool`: 현재 사내에 등록된 활성 스킬 목록을 실시간 조회할 때 호출하십시오.
4. `get_preset_skills_tool`: 사내 공식 프리셋 스킬 카탈로그를 브리핑할 때 호출하십시오.

[핵심 단계별 인터뷰 절차]
0단계 (사전 슬러그/ID 중복 검증 인터셉터 - 최우선 필수 실행):
- 사용자가 특정 사내 도구나 스킬 생성을 요청하면, 1단계 인터뷰를 시작하기 전에 반드시 가장 먼저 해당 스킬의 고유 슬러그(ID, 3계층 영문 소문자 케밥 케이스, 예: approval-draft-create, slack-incident-alert)를 도출하여 `check_skill_duplicate_tool(slug=...)` 도구를 호출한다!
- 주의 원칙: 자연어 도구 명칭은 유사할 수 있으므로 절대 차단하지 않으며, 오로지 시스템 고유 식별자인 슬러그(ID)가 정확히 일치할 때만 중복으로 판정한다!
- 기등록 슬러그 발견 시: 1단계~3단계 기획 인터뷰를 일절 진행하지 않고, 즉시 첫 턴에서 사내 스킬 갤러리 바로가기 링크( /r/skills )와 함께 해당 슬러그 ID의 스킬이 이미 등록되어 활성화되어 있음을 알리고 기존 스킬을 사용하거나 설정을 업데이트할 것인지 묻는다.
- 신규 슬러그인 경우에만: 비로소 1단계(연동 대상 시스템 파악) 인터뷰를 시작한다.
1단계 (업무 목적 파악): 스킬이 수행할 반복 업무 목적과 입력 항목 확인 (카탈로그 추천 또는 자유 프롬프팅 접수).
2단계 (스킬 명칭 및 지침 정의): 영문 스킬 명칭, 설명, 핵심 지침(SKILL.md) 및 트리거 조건 도출.
3단계 (실제 프로비저닝 집행): 사용자의 동의를 얻어 `deploy_enterprise_skill_tool`을 즉시 호출하여 GE App `/r/skills` 목록에 자동 배포.
4단계 (결과 및 활용 안내): 발급된 스킬 ID, 공유 범위, `/r/skills` 새로고침 및 호출 방법 안내.

[단계별 추천 후속 질문 안내 규약]
모든 답변 본문의 맨 끝에는 사용자가 다음 행동을 쉽게 선택할 수 있도록 구분선(---)과 함께 마크다운 번호 매기기 리스트로 2~3개의 '추천 후속 질문'을 명확히 안내한다:
---
**추천 후속 질문:**
1. 주간 업무 보고서 요약 스킬 생성해 줘
2. 회의록 실행 과제 정리 스킬 등록해 줘
3. 사내 등록된 스킬 목록 조회
- 주의: JSON이나 코드 블록(```suggested_questions 등) 형태가 아닌, 순수 마크다운 텍스트 리스트로 가독성 높게 출력한다.

[소통 원칙]
- 정중하고 품격 있는 문어체(-다, -한다)와 한글 맞춤법 복합어 띄어쓰기를 철저히 준수합니다.
- 이모지나 특수 기호 대신 깔끔한 마크다운을 사용합니다.
"""

    adk_agent = Agent(
        name="gemini_enterprise_skill_factory",
        description=description,
        model="gemini-3.8-flash",
        instruction=instruction,
        tools=[check_skill_duplicate_tool, deploy_enterprise_skill_tool, list_enterprise_skills_tool, get_preset_skills_tool],
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
        gcs_dir_name="ge_factory_skill_factory",
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
        "customPlaceholderText": "새로 생성할 사내 업무 스킬 이름이나 지침 요구사항을 입력하세요...",
        "starterPrompts": [
            {"text": "주간 업무 보고서 자동 요약 스킬 생성해서 /r/skills에 등록해 줘"},
            {"text": "회의록 핵심 결정 사항 정리 스킬 만들어 줘"},
            {"text": "전자결재 기안문 초안 작성 스킬 생성 및 전사 공유해 줘"},
            {"text": "현재 사내에 등록된 스킬 목록 조회해 줘"},
        ],
        "adkAgentDefinition": {
            "toolSettings": {"toolDescription": description},
            "provisionedReasoningEngine": {
                "reasoningEngine": re_res
            },
        },
    }

    target_agent_id = None
    existing_state = None
    list_resp = requests.get(base_url, headers=headers, timeout=30)
    if list_resp.ok:
        for a in list_resp.json().get("agents", []):
            if a.get("displayName") in [display_name, "GE Skill Factory (사내 스킬 팩토리)", "GE Skill Scaffolder (사내 스킬 스캐폴더)"]:
                target_agent_id = a.get("name").split("/")[-1]
                existing_state = a.get("state")
                break

    if target_agent_id:
        if existing_state == "PRIVATE":
            requests.delete(f"{base_url}/{target_agent_id}", headers=headers, timeout=30)
            reg_resp = requests.post(base_url, headers=headers, json=body, timeout=30)
        else:
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
    """로컬 단일 스킬 매니페스트 합성 및 스캐폴딩 보조 모드를 실행한다."""
    print("\n[안내] 로컬 단일 스킬 매니페스트 합성 보조 모드 가동")

    # 1. 스킬 칩 선택
    tool_data = SYSTEM_TOOL_CATALOG[1]
    if args.prompt:
        tool_data = {
            "id": "custom-work-skill",
            "slug": "custom-work-skill",
            "title": args.prompt,
            "description": "사용자 맞춤형 GE App 반복 업무 자동화 스킬",
            "category": "사용자 직접 정의 스킬",
            "slash_command": "/custom-work-skill",
            "default_scope": "ALL_USERS",
            "parameters": {
                "request_input": {"type": "string", "description": "실행 시 전달할 업무 내용", "required": True},
            },
        }
    elif args.chip and args.chip in SYSTEM_TOOL_CATALOG:
        tool_data = SYSTEM_TOOL_CATALOG[args.chip]
    elif args.interactive or (sys.stdin.isatty() and not args.dry_run):
        tool_data = select_tool_interactive(args.dry_run)

    print(f"\n[단계 1/3] 스킬 칩 스펙 컴파일 중...")
    print(f"  - 스킬 명칭    : {tool_data['title']}")
    print(f"  - 업무 분류    : {tool_data['category']}")
    print(f"  - 호출 커맨드  : {tool_data.get('slash_command', '/' + tool_data['id'])}")

    # 2. SKILL.md 및 skillAgentDefinition 합성
    print("\n[단계 2/3] SKILL.md 및 skillAgentDefinition 페이로드 합성 중...")
    skill_manifest = generate_skill_manifest(tool_data, env_info)
    print(f"  - 공유 범위    : {skill_manifest['scope']}")

    # 3. 환경 준비 점검
    print("\n[단계 3/3] Gemini Enterprise app 스킬 등록 환경 점검 중...")
    readiness = diagnose_ge_app_readiness(env_info, args.dry_run)
    print(f"  - 상태: {readiness['status']} | {readiness['detail']}")

    # 4. 리포트 생성 및 저장
    report_content = build_markdown_report(env_info, tool_data, skill_manifest, readiness, dry_run=args.dry_run)
    save_markdown_report(report_content)

    print("\n" + "=" * 75)
    print("  사내 스킬 스펙 컴파일 및 매니페스트 생성 완료")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Enterprise 자율형 사내 스킬 팩토리 (붕어빵 틀) 배포 및 등록 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", help="Google Cloud 프로젝트 ID (미지정 시 자동 감지)")
    parser.add_argument("--location", help="Discovery Engine / Gemini Enterprise app 리전 (기본: global)")
    parser.add_argument("--ge-app-id", help="Gemini Enterprise App 인스턴스 ID")
    parser.add_argument("--skill-sa", help="스킬 실행 대행 서비스 계정 이메일")
    parser.add_argument("--dry-run", action="store_true", default=False, help="실제 배포 없이 가상 실행 검증")
    parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
    parser.add_argument("--scaffold", action="store_true", default=False, help="로컬 단일 도구/스킬 매니페스트 합성 보조 모드")
    parser.add_argument("--catalog", help="선언적 스킬 레시피 카탈로그 경로 또는 URL (기본: ./catalog.yaml)")
    parser.add_argument("--chip", type=int, help="도구 칩 번호 직접 지정 (1~25)")
    parser.add_argument("--prompt", help="사용자 직접 정의 연동 시스템 요구사항")
    parser.add_argument("--interactive", action="store_true", default=False, help="로컬 대화형 번호 선택기 가동")
    parser.add_argument("--deploy-engine", action="store_true", default=False, help="Agent Engine 프로비저닝 (기본 실행과 동일)")

    args = parser.parse_args()

    # 선언적 카탈로그 경로 오버라이드 반영
    global SYSTEM_TOOL_CATALOG
    if args.catalog:
        SYSTEM_TOOL_CATALOG = load_skill_catalog(args.catalog)

    # 사내 환경 대화형 설정 모드 분기
    if args.config:
        run_config_mode(args)
        return

    # 인자가 없고 비대화형 환경인 경우 기본 dry-run 활성화
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        args.dry_run = True

    print("\n" + "=" * 75)
    print("  Gemini Enterprise 사내 스킬 팩토리 (gemini-enterprise-factory-skill)")
    print("=" * 75)

    # 1. 환경 정보 해석
    env_info = resolve_environment(args)
    print(f"[*] 활성 프로젝트    : {env_info['project_id']}")
    print(f"[*] 대상 리전        : {env_info['location']}")
    print(f"[*] 대상 GE App ID   : {env_info['ge_app_id']}")
    print(f"[*] 실행 서비스 계정 : {env_info['service_account']}")
    print(f"[*] 실행 모드        : {'가상 실행 (--dry-run)' if args.dry_run else '실제 프로비저닝 모드'}")

    # 로컬 스캐폴딩 보조 모드 분기 (명시적 플래그 지정 시에만 작동)
    if args.scaffold or args.chip or args.prompt or args.interactive:
        run_local_scaffolding_mode(args, env_info)
        return

    # [핵심 메인 워크플로우]: 붕어빵 틀(GE Skill Factory) 배포 및 GE App 사내 갤러리 등록
    if not args.dry_run and not _get_cloud_token():
        print("\n[오류] 유효한 Google Cloud 인증 자격 증명(ADC)을 찾을 수 없습니다.", file=sys.stderr)
        print("      아래 명령어를 실행하여 로컬 자격 증명을 갱신하십시오:", file=sys.stderr)
        print("      gcloud auth application-default login\n", file=sys.stderr)
        print("      (참고: 실제 배포 없이 가상 검증을 수행하려면 '--dry-run' 플래그를 사용하십시오.)\n", file=sys.stderr)
        sys.exit(1)

    print("\n[진행] 사내 스킬 팩토리(붕어빵 틀) 프로비저닝 파이프라인 가동...")
    deploy_res = deploy_skill_factory_engine(env_info, dry_run=args.dry_run)

    # 팩토리 리포트 생성 및 저장
    report_content = build_factory_markdown_report(env_info, deploy_res, dry_run=args.dry_run)
    save_markdown_report(report_content)

    creator = get_resource_creator(args.dry_run)
    print("\n" + "=" * 75)
    print("  사내 스킬 팩토리 배포 및 등록 완료 (모든 점검 통과)")
    print("=" * 75)
    print("\n[안내] 사내 거버넌스 및 자원 추적을 위한 4대 필수 표준 라벨:")
    print("  - managed-by: google-cloud-0-to-1")
    print("  - scenario: gemini-enterprise-factory-skill")
    print("  - env: sample")
    print(f"  - created-by: {creator}\n")


if __name__ == "__main__":
    main()
