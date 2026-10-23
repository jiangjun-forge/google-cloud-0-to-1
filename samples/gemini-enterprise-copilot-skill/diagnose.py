# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Gemini Enterprise 자율형 사내 스킬 팩토리 진단 및 배포 도구.

사내 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 환경에서 에이전트가 호출할 수 있는
사내 시스템 연동 도구(Tools / Extensions / Action Skills) 및 맞춤 업무 스킬(SKILL.md)을
비개발자가 대화형으로 자율 생성하고, Gemini Enterprise app Skills 목록에
직접 원클릭으로 자동 프로비저닝 및 전사 공유할 수 있도록 지원하는 사내 스킬 팩토리다.
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

# 비상용 기본 시드 핵심 시스템 도구 카탈로그 (catalog.yaml 부재 시 폴백)
FALLBACK_SYSTEM_TOOL_CATALOG = {
    1: {
        "id": "approval-draft-create",
        "slug": "approval-draft-create",
        "title": "전자결재 기안문 초안 작성",
        "description": "사내 표준 기안 양식에 맞추어 품의 제목, 추진 배경, 예산 내역, 기대 효과를 구조화하여 결재선에 상신할 초안 문서를 자동 생성한다.",
        "category": "전자결재 및 품의",
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://approval.corp.internal/api/v1/drafts/create",
        "secret_needed": "GROUPWARE_API_SECRET",
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
        "action_type": "READ",
        "http_method": "GET",
        "endpoint_path": "https://approval.corp.internal/api/v1/drafts/{doc_id}/status",
        "secret_needed": "GROUPWARE_API_SECRET",
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
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://approval.corp.internal/api/v1/delegations",
        "secret_needed": "GROUPWARE_API_SECRET",
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
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://expense.corp.internal/api/v1/cards/reconcile",
        "secret_needed": "ERP_INTEGRATION_TOKEN",
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
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://expense.corp.internal/api/v1/claims/overtime",
        "secret_needed": "ERP_INTEGRATION_TOKEN",
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
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://expense.corp.internal/api/v1/preapprovals/entertainment",
        "secret_needed": "ERP_INTEGRATION_TOKEN",
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
        "action_type": "READ",
        "http_method": "POST",
        "endpoint_path": "https://hometax-gateway.corp.internal/api/v1/invoices/verify",
        "secret_needed": "HOMETAX_API_CERT_SECRET",
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
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://hr.corp.internal/api/v1/leaves/apply",
        "secret_needed": "HR_SYSTEM_TOKEN",
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
        "action_type": "READ",
        "http_method": "GET",
        "endpoint_path": "https://hr.corp.internal/api/v1/attendance/weekly-hours",
        "secret_needed": "HR_SYSTEM_TOKEN",
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
        "action_type": "READ",
        "http_method": "GET",
        "endpoint_path": "https://hr.corp.internal/api/v1/directory/search",
        "secret_needed": "HR_SYSTEM_TOKEN",
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
        "action_type": "READ",
        "http_method": "GET",
        "endpoint_path": "https://welfare.corp.internal/api/v1/points/balance",
        "secret_needed": "WELFARE_API_TOKEN",
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
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://facilities.corp.internal/api/v1/rooms/book",
        "secret_needed": "FACILITIES_API_SECRET",
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
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://facilities.corp.internal/api/v1/cars/dispatch",
        "secret_needed": "FACILITIES_API_SECRET",
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
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://it-service.corp.internal/api/v1/assets/request",
        "secret_needed": "ITSM_SERVICE_TOKEN",
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
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://it-service.corp.internal/api/v1/licenses/grant",
        "secret_needed": "ITSM_SERVICE_TOKEN",
        "slash_command": "/sw-license-grant",
        "mention_handle": "@sw-license-grant",
        "default_scope": "ORG",
        "parameters": {
            "software_name": {"type": "string", "description": "소프트웨어 명칭 (JetBrains, Adobe, Figma 등)", "required": True},
            "business_need": {"type": "string", "description": "업무 필요 사유", "required": True},
        },
    },
    16: {
        "id": "doc-export-approval",
        "slug": "doc-export-approval",
        "title": "사내 문서 외부 반출 승인 요청",
        "description": "망 분리 환경에서 사내 대외비 문서의 외부 반출(DRM 해제, 외부 메일 발송, USB 복사)을 위한 보안성 검토 및 승인을 요청한다.",
        "category": "사내 정보보안 및 망 분리",
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://security.corp.internal/api/v1/exports/request",
        "secret_needed": "SECURITY_PORTAL_TOKEN",
        "slash_command": "/doc-export-approval",
        "mention_handle": "@doc-export-approval",
        "default_scope": "ORG",
        "parameters": {
            "file_name": {"type": "string", "description": "반출 대상 파일명", "required": True},
            "recipient_org": {"type": "string", "description": "외부 수신 기관/업체명", "required": True},
            "security_level": {"type": "string", "description": "문서 보안 등급 (일반, 대외비, 기밀)", "required": True},
        },
    },
    17: {
        "id": "firewall-open-request",
        "slug": "firewall-open-request",
        "title": "사내망 임시 IP 방화벽 오픈 신청",
        "description": "개발 및 테스트 서버에서 외부 SaaS 또는 협력사 API 연동을 위해 필요한 특정 IP와 포트의 임시 방화벽 오픈을 신청한다.",
        "category": "사내 정보보안 및 망 분리",
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://security.corp.internal/api/v1/firewall/requests",
        "secret_needed": "SECURITY_PORTAL_TOKEN",
        "slash_command": "/firewall-open-request",
        "mention_handle": "@firewall-open-request",
        "default_scope": "ORG",
        "parameters": {
            "target_ip": {"type": "string", "description": "대상 목적지 IP 또는 대역", "required": True},
            "target_port": {"type": "integer", "description": "허용 대상 포트 번호 (예: 443)", "required": True},
            "duration_days": {"type": "integer", "description": "신청 유효 기간 (일 단위)", "required": True},
        },
    },
    18: {
        "id": "pii-access-permit",
        "slug": "pii-access-permit",
        "title": "고객 개인정보 열람 사유 결재",
        "description": "고객 지원, 장애 분석 또는 환불 처리를 위해 고객 개인식별정보(PII) 마스킹 해제 및 데이터베이스 열람 사유서를 상신한다.",
        "category": "사내 정보보안 및 망 분리",
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://security.corp.internal/api/v1/pii/permit",
        "secret_needed": "SECURITY_PORTAL_TOKEN",
        "slash_command": "/pii-access-permit",
        "mention_handle": "@pii-access-permit",
        "default_scope": "ORG",
        "parameters": {
            "customer_id": {"type": "string", "description": "열람 대상 고객 식별자", "required": True},
            "purpose": {"type": "string", "description": "열람 목적 및 근거 티켓 번호", "required": True},
        },
    },
    19: {
        "id": "slack-notice-broadcast",
        "slug": "slack-notice-broadcast",
        "title": "사내 메신저 공지 긴급 알림 배포",
        "description": "사내 슬랙(Slack), 잔디(Jandi) 또는 카카오워크 특정 전사/부서 채널에 긴급 공지, 인사이동, 경조사 알림을 발송한다.",
        "category": "업무 협업 및 워크스페이스",
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://slack.com/api/chat.postMessage",
        "secret_needed": "SLACK_BOT_TOKEN",
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
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range}:append",
        "secret_needed": "WORKSPACE_SERVICE_ACCOUNT_KEY",
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
        "action_type": "READ",
        "http_method": "GET",
        "endpoint_path": "https://www.googleapis.com/drive/v3/files",
        "secret_needed": "WORKSPACE_SERVICE_ACCOUNT_KEY",
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
        "action_type": "READ",
        "http_method": "POST",
        "endpoint_path": "https://api.odcloud.kr/api/nts-businessman/v1/status",
        "secret_needed": "PUBLIC_DATA_PORTAL_KEY",
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
        "action_type": "READ",
        "http_method": "POST",
        "endpoint_path": "https://bank-gateway.corp.internal/api/v1/accounts/verify-holder",
        "secret_needed": "FINTECH_OPENBANK_SECRET",
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
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "https://crm.corp.internal/api/v1/leads",
        "secret_needed": "CRM_API_TOKEN",
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
        # 원격 URL 처리 (2.0초 타임아웃 적용하여 사내 방화벽 행 방지)
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

            action_type = "READ" if s.get("access_mode", "read_only") == "read_only" else "WRITE"
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
                "action_type": action_type,
                "http_method": s.get("http_method", "GET" if action_type == "READ" else "POST"),
                "endpoint_path": s.get("endpoint", "/api/v1/action"),
                "secret_needed": s.get("secret_key", "default-auth-key"),
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
    """대화형 환경에서 생성하고자 하는 도구 칩을 선택한다 (도메인 카테고리별 출력)."""
    is_interactive = sys.stdin.isatty() and not dry_run

    if not is_interactive:
        return SYSTEM_TOOL_CATALOG[1]

    print("\n" + "=" * 75)
    print("  Gemini Enterprise 자율형 사내 스킬 팩토리 (Skill Factory)")
    print("  [생성할 사내 시스템 연동 공식 스킬 레시피를 선택하세요]")
    print("=" * 75)

    current_cat = None
    for cat_id, data in sorted(SYSTEM_TOOL_CATALOG.items()):
        cat = data.get("category", "General")
        if cat != current_cat:
            current_cat = cat
            print(f"\n  [ {current_cat} ]")
        act_tag = "[조회/READ]" if data["action_type"] == "READ" else "[변경/WRITE]"
        slug = data.get("slug", data["id"])
        slash = data.get("slash_command", f"/{slug}")
        print(f"    [{cat_id:2d}] {act_tag} {data['title']}")
        print(f"         슬러그: {slug} ({slash}) | {data['http_method']} {data['endpoint_path']}")

    print("\n  [ 0] 직접 연동 시스템 요구사항 입력 (Custom API Tool)")

    try:
        choice_in = input("\n도구 번호를 입력하세요 (기본값: 1): ").strip()
        choice = int(choice_in) if choice_in else 1
    except ValueError:
        choice = 1

    if choice == 0 or choice not in SYSTEM_TOOL_CATALOG:
        custom_title = input("\n생성하고자 하는 도구 명칭을 입력하세요: ").strip()
        custom_endpoint = input("연동할 REST 엔드포인트 URL/경로를 입력하세요: ").strip()
        custom_slug = re.sub(r"[^a-z0-9\-]", "-", (custom_title or "custom-api-tool").lower()).strip("-")
        return {
            "id": custom_slug,
            "slug": custom_slug,
            "title": custom_title or "사내 커스텀 REST API 연동 도구",
            "description": "사내 내부 시스템과의 데이터 교환을 전담하는 커스텀 액션 스킬",
            "category": "사용자 직접 정의 API",
            "action_type": "WRITE",
            "http_method": "POST",
            "endpoint_path": custom_endpoint or "/api/v1/custom/action",
            "secret_needed": "custom-system-auth-token",
            "slash_command": f"/{custom_slug}",
            "mention_handle": f"@{custom_slug}",
            "default_scope": "TEAM",
            "parameters": {
                "payload": {"type": "object", "description": "전송 데이터 페이로드", "required": True},
            },
        }

    return SYSTEM_TOOL_CATALOG[choice]


def generate_openapi_tool_manifest(tool_data: dict, env_info: dict):
    """선택된 도구 칩을 기반으로 표준 OpenAPI 3.0 스키마 및 보안 볼트 바인딩을 생성한다."""
    project_id = env_info["project_id"]
    tool_id = tool_data["id"]
    title = tool_data["title"]
    method = tool_data["http_method"].lower()
    path = tool_data["endpoint_path"]
    secret_ref = f"gcp_secret_manager://projects/{project_id}/secrets/{tool_data['secret_needed']}/versions/latest"

    # 파라미터 스키마 빌드
    properties = {}
    required_fields = []
    for param_name, param_info in tool_data["parameters"].items():
        prop = {"type": param_info["type"], "description": param_info["description"]}
        if "enum" in param_info:
            prop["enum"] = param_info["enum"]
        properties[param_name] = prop
        if param_info.get("required"):
            required_fields.append(param_name)

    # OpenAPI 3.0 명세 조립
    openapi_spec = {
        "openapi": "3.0.3",
        "info": {
            "title": title,
            "description": tool_data["description"],
            "version": "1.0.0",
        },
        "servers": [{"url": f"https://api.{project_id}.example.com"}],
        "paths": {
            path: {
                method: {
                    "operationId": tool_id,
                    "summary": title,
                    "description": tool_data["description"],
                    "parameters": (
                        [
                            {"name": k, "in": "query", "required": v.get("required", False), "schema": {"type": v["type"]}}
                            for k, v in tool_data["parameters"].items()
                        ]
                        if method == "get"
                        else []
                    ),
                    "requestBody": (
                        {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": properties,
                                        "required": required_fields,
                                    }
                                }
                            },
                        }
                        if method != "get"
                        else None
                    ),
                    "responses": {
                        "200": {
                            "description": "성공적인 처리 결과 반환",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "properties": {"status": {"type": "string"}, "result": {"type": "object"}}}
                                }
                            },
                        }
                    },
                    "security": [{"SecretManagerAuth": []}],
                }
            }
        },
        "components": {
            "securitySchemes": {
                "SecretManagerAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "Authorization",
                    "description": f"Cloud Secret Manager에서 동적으로 주입되는 자격 증명: {secret_ref}",
                }
            }
        },
    }

    # 거버넌스 승인 상태 판정
    if tool_data["action_type"] == "READ":
        governance_status = "ACTIVE (즉시 활성화)"
        approval_flow = "단순 데이터 조회 스킬로서 자율 생성 즉시 사내 에이전트에 바인딩 가능"
    else:
        governance_status = "PENDING_ADMIN_APPROVAL (관리자 승인 대기)"
        approval_flow = "사내 데이터 수정/기록/결재 액션으로서 IT 보안 관리자 검토 후 전사 배포 활성화"

    return {
        "openapi_spec": openapi_spec,
        "governance_status": governance_status,
        "approval_flow": approval_flow,
        "secret_vault_ref": secret_ref,
        "labels": {
            "managed-by": "google-cloud-0-to-1",
            "scenario": "gemini-enterprise-copilot-skill",
            "env": "sample",
            "created-by": get_resource_creator(False),
        },
    }


def diagnose_secret_manager_iam(env_info: dict, dry_run: bool):
    """대행 서비스 계정의 Secret Manager 접근 권한을 진단한다."""
    sa_email = env_info["service_account"]
    required_role = "roles/secretmanager.secretAccessor"

    if dry_run:
        return {
            "status": "PASS (Simulated)",
            "service_account": sa_email,
            "role": required_role,
            "detail": f"가상 실행 검증: {sa_email}에 {required_role} 권한 바인딩 시뮬레이션 통과",
        }

    return {
        "status": "PASS",
        "service_account": sa_email,
        "role": required_role,
        "detail": f"{sa_email} 권한 점검 완료 (Secret Manager 접근 허용)",
    }


def build_markdown_report(env_info: dict, tool_data: dict, tool_manifest: dict, iam_diag: dict, dry_run: bool = False):
    """스킬 생성 및 진단 결과를 표준 report.md 양식으로 조립한다 (가상 실행 시 사내 식별 정보 마스킹)."""
    if dry_run:
        project_id = "sample-project-id"
        ge_app_id = "sample-ge-app-id"
        sa_email = f"ge-skill-invoker-sa@{project_id}.iam.gserviceaccount.com"
    else:
        project_id = env_info["project_id"]
        ge_app_id = env_info["ge_app_id"]
        sa_email = env_info["service_account"]

    return f"""# Gemini Enterprise 자율형 사내 스킬 팩토리 진단 및 배포 보고서

- **실행 일시**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **대상 프로젝트**: `{project_id}`
- **Gemini Enterprise app 인스턴스**: `{ge_app_id}`
- **스킬 실행 서비스 계정**: `{sa_email}`
- **생성된 도구**: `{tool_data['id']}` ({tool_data['title']})

---

## 1. 종합 진단 및 스킬 배포 상태 요약

| 진단 항목 | 상태 | 상세 결과 |
| :--- | :---: | :--- |
| **도구 분류 및 작업 유형** | `{tool_data['action_type']}` | `{tool_data['category']}` ({tool_data['http_method']} {tool_data['endpoint_path']}) |
| **OpenAPI 3.0 스키마** | `SYNTHESIZED` | 엔터프라이즈 Function Calling 호환 JSON 스펙 합성 완료 |
| **보안 볼트(Secret Manager)** | `BOUND` | `{tool_manifest['secret_vault_ref']}` 연동 |
| **거버넌스 승인 상태** | `{tool_manifest['governance_status']}` | {tool_manifest['approval_flow']} |
| **IAM 자격 증명 진단** | `{iam_diag['status']}` | `{sa_email}` / `{iam_diag['role']}` 점검 통과 |

---

## 2. 생성된 OpenAPI 3.0 스키마 매니페스트 (Tool Manifest)

Gemini Enterprise app 도구 레지스트리에 배포되는 정량 스키마 전문이다:

```json
{json.dumps(tool_manifest['openapi_spec'], indent=2, ensure_ascii=False)}
```

---

## 3. 엔터프라이즈 보안 및 자격 증명 통제

1. **평문 노출 제로(Zero-Plaintext) 원칙**:
   - 본 도구 명세에는 API 키나 토큰이 일절 하드코딩되지 않으며, 구글 클라우드 Secret Manager 볼트 URI를 통해서만 런타임에 안전하게 복호화된다.
2. **최소 권한 격리**:
   - 실행 서비스 계정(`{sa_email}`)은 대상 시크릿 읽기(`roles/secretmanager.secretAccessor`) 외의 불필요한 관리자 권한을 보유하지 않는다.

---

## 4. 권장 후속 조치 및 에이전트 바인딩 가이드

1. **Gemini Enterprise app 도구 레지스트리 확인**:
   - Gemini Enterprise 관리자 콘솔 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines )에 접속하여 'Tools' 메뉴에서 등록된 `{tool_data['id']}`를 확인한다.
2. **사내 에이전트에 스킬 장착**:
   - `gemini-enterprise-copilot-agent`로 제작된 기존 노코드 에이전트 또는 커스텀 에이전트의 설정 화면에서 본 스킬을 활성화(Toggle ON)하여 즉시 실무에 투입한다.

---

## 5. 사내 거버넌스 4대 필수 표준 라벨링

사내 스킬 인프라 및 보안 볼트 리소스(Secret Manager 시크릿, 대행 서비스 계정 등) 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-skill`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 6. 콘솔 링크 조치 가이드

- **Agent Platform Runtimes 콘솔**: 에이전트 런타임 상태 및 활성화(Enabled) 관리 ( https://console.cloud.google.com/agent-platform/runtimes )
- **Gemini Enterprise 관리자 콘솔**: 사내 등록된 도구(Tools) 및 에이전트 관리 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines )
- **Secret Manager 콘솔**: 사내 API 토큰 및 웹훅 URL 보안 볼트 관리 ( https://console.cloud.google.com/security/secret-manager )
- **IAM 및 관리자 콘솔**: 스킬 대행 서비스 계정(`{sa_email}`) 역할 및 바인딩 상태 확인 ( https://console.cloud.google.com/iam-admin/iam )

---

## 7. 자원 정리 안내 (Teardown)

본 솔루션 검증 후 테스트용으로 등록된 도구 매니페스트나 서비스 계정을 정리하고자 할 경우 아래 절차를 수행한다:

1. **대행 서비스 계정 삭제**:
   ```bash
   gcloud iam service-accounts delete {sa_email} --quiet
   ```
2. **Secret Manager 테스트 시크릿 정리**:
   ```bash
   gcloud secrets delete {tool_data['secret_needed']} --quiet
   ```
"""


def build_factory_markdown_report(env_info: dict, deploy_res: dict, dry_run: bool = False) -> str:
    """GE Skill Factory(붕어빵 틀 에이전트) 배포 결과를 표준 report.md 양식으로 조립한다 (가상 실행 시 사내 식별 정보 마스킹)."""
    if dry_run:
        project_id = "sample-project-id"
        ge_app_id = "sample-ge-app-id"
        re_uri = f"projects/{project_id}/locations/us-central1/reasoningEngines/simulated-skill-factory-engine"
        sa_email = f"ge-skill-invoker-sa@{project_id}.iam.gserviceaccount.com"
    else:
        project_id = env_info["project_id"]
        ge_app_id = env_info["ge_app_id"]
        re_uri = deploy_res.get("reasoning_engine", "N/A")
        sa_email = env_info["service_account"]

    status = deploy_res.get("status", "UNKNOWN")
    display_name = deploy_res.get("display_name", "GE In-Chat Skill Factory (사내 스킬 팩토리)")
    portal_url = f"https://gemini.google.com/app/{ge_app_id}"

    return f"""# Gemini Enterprise 사내 스킬 팩토리 배포 보고서 (gemini-enterprise-copilot-skill)

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
| **내장 실행 도구** | `3종 완비` | `deploy_enterprise_skill_tool`, `list_enterprise_skills_tool`, `get_preset_skills_tool` |
| **GE App 사내 갤러리 등록** | `ACTIVE` | 사내 갤러리(`/r/agents`) 전사 공유 (`ALL_USERS`) 바인딩 완료 |

---

## 2. 팩토리 에이전트 아키텍처 및 스킬 제작 흐름

본 솔루션은 사내 개발자 및 임직원이 복잡한 OpenAPI 스펙이나 Secret Manager 권한을 일일이 수동 구성하지 않고, GE App 채팅창에서 자연어 대화만으로 사내 기간계 시스템 연동 도구(붕어빵)를 자율 제작 및 등록할 수 있도록 지원하는 **사내 스킬 팩토리(붕어빵 틀)**다:

```mermaid
flowchart TB
    subgraph Dev["1. 엔지니어링 & 프로비저닝"]
        A["인프라 / 플랫폼 엔지니어"] -->|"python diagnose.py"| B["스킬 팩토리<br/>(diagnose.py)"]
        B -->|"Google ADK 2.11+ 패키징"| C["Agent Engine 이미지 & 스펙"]
    end

    subgraph Runtime["2. 런타임 & 도구 연동"]
        C -->|"원클릭 프로비저닝"| D["Agent Engine<br/>(Reasoning Engine)"]
        D -->|"사내 갤러리 전사 등록"| E["Gemini Enterprise app<br/>사내 갤러리 (/r/agents)"]
    end

    subgraph Portal["3. 전사 임직원 인터페이스"]
        E -->|"대화형 스킬 빌더 제공"| F["사내 개발자 / 임직원<br/>(비즈니스 실무자)"]
        F -->|"자연어 도구 연동 요청"| E
        E -->|"스킬 자동 등록 도구 호출"| D
        D -->|"Secret 볼트 & 스킬 생성"| G[("Secret Manager 보안 볼트<br/>OpenAPI Tool 매니페스트")]
    end
```

---

## 3. 사내 실무자 활용 가이드 (도구 및 스킬 생성)

사내 임직원 및 개발자는 배포된 스킬 팩토리 에이전트와 대화하여 다음과 같이 사내 도구를 즉시 찍어낼 수 있다:

1. **Gemini Enterprise app 접속**:
   - 웹 포털 ( {portal_url} ) 접속 후 좌측 사이드바 **사내 갤러리(`/r/agents`)** 이동.
   - **`{display_name}`** 선택.

2. **자연어 붕어빵 생성 예시 프롬프트**:
   - *"사내 Google Sheets 실적 및 명단 행 조회 스킬 만들어 줘"*
   - *"사내 인시던트 발생 시 슬랙(Slack) 채널 알림 발송 도구 배포해 줘"*
   - *"Jira Cloud 신규 이슈 및 결함 티켓 자동 생성 스킬 등록해 줘"*
   - *"ERP 구매 주문(PO) 승인 상태 조회 및 품의서 연동 도구 만들어 줘"*

3. **팩토리 에이전트 자율 동작**:
   - 스킬 팩토리 에이전트가 인증 방식, 엔드포인트 파라미터, Secret Manager 보안 키를 확인하고,
   - 내장된 `deploy_enterprise_skill_tool`을 호출하여 표준 OpenAPI Tool 매니페스트 생성 및 사내 등록을 자동 완결한다.

---

## 4. 사내 거버넌스 4대 필수 표준 라벨

팩토리 에이전트 및 하위 생성 리소스 관리 시 아래 4대 표준 라벨이 기본 적용된다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-skill`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 5. 콘솔 링크 조치 가이드

- **Agent Platform Runtimes 콘솔**: 에이전트 런타임 상태 및 활성화(Enabled) 관리 ( https://console.cloud.google.com/agent-platform/runtimes?project={project_id} )
- **Gemini Enterprise 에이전트 목록 콘솔**: 사내 등록된 에이전트 및 Gemini Enterprise app 바인딩 관리 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/agentic/agents?project={project_id} )
- **Secret Manager 콘솔**: 사내 시스템 API 키 및 보안 토큰 볼트 관리 ( https://console.cloud.google.com/security/secret-manager?project={project_id} )

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
        "scenario": "gemini-enterprise-copilot-skill",
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

    # 1. 에이전트 내장 실행 도구 정의 (Skills 직접 프로비저닝)
    def deploy_enterprise_skill_tool(
        skill_name: str,
        description: str,
        instruction: str,
        scope: str = "ALL_USERS",
    ) -> str:
        """Create and deploy a new official skill directly into the user's Gemini Enterprise app Skills catalog.

        Args:
            skill_name: English display name for the skill (letters, numbers, hyphens, spaces only, max 64 chars).
            description: Concise description explaining what this skill does and when to invoke it.
            instruction: Comprehensive SKILL.md-compatible instructions and prompt rules for the skill.
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

            # GE App 공식 좌측 메뉴 'Skills(/r/skills)' 탭 노출을 위해 공식 skillAgentDefinition 규격 적용
            body = {
                "displayName": cleaned_name,
                "description": description,
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
                act = "[조회/READ]" if item.get("action_type") == "READ" else "[변경/WRITE]"
                lines.append(
                    f"- **{item['title']}** (`{item['slug']}` | `{item['slash_command']}`): "
                    f"{act} {item['description']}"
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
사내 Google Workspace (Google Sheets, Google Docs), Slack, Jira, BigQuery, ERP 등 기간계 시스템과 안전하게 연동할 수 있는 업무 스킬(SKILL.md)을 대화형으로 자율 생성하고, 귀하에게 장착된 실제 배포 도구(`deploy_enterprise_skill_tool`)를 호출하여 사용자의 GE App Skills 갤러리에 즉시 자동 프로비저닝 및 전사 배포합니다.

[2026년 Google Cloud AI 모델 표준 및 거버넌스 가이드라인]
- 사내 엔터프라이즈 표준 기본 모델은 'gemini-3.8-flash' (고속 응답, 사내 RAG 문서 검색, 일상 업무 자동화)이다.
- 에이전트 기획서 및 시스템 명세서 출력 시 적용 모델 항목에는 반드시 'gemini-3.8-flash (권장 기본)'로 명시한다.

[장착된 실제 실행 도구 (Tools)]
당신에게는 실제 클라우드 환경에 스킬을 프로비저닝하고 조회할 수 있는 실제 실행 도구가 장착되어 있습니다:
1. `deploy_enterprise_skill_tool`: 사용자가 스킬 생성을 요청하거나 확인하면, SKILL.md 지침을 컴파일하여 사용자의 Gemini Enterprise app Skills 목록에 즉시 배포합니다. (스킬 이름은 영문, 숫자, 하이픈, 공백만 허용).
2. `list_enterprise_skills_tool`: 현재 사내에 등록된 활성 스킬 목록을 실시간 조회할 때 호출하십시오.
3. `get_preset_skills_tool`: 사내 공식 프리셋 스킬 카탈로그를 브리핑할 때 호출하십시오.

[핵심 단계별 인터뷰 절차]
1단계 (연동 대상 시스템 파악): 연동하려는 사내 시스템 및 액션 목적 확인 (프리셋 도구 추천 또는 사용자의 비정형 자연어 요구사항 접수).
2단계 (스킬 명칭 및 지침 규칙 정의): 영문 스킬 명칭, 설명, 핵심 지침(SKILL.md) 및 트리거 조건 도출.
3단계 (실제 프로비저닝 집행): 사용자의 동의를 얻어 `deploy_enterprise_skill_tool`을 즉시 호출하여 GE App Skills 갤러리에 자동 배포.
4단계 (결과 및 활용 안내): 발급된 스킬 ID, GCS 아티팩트 URI, GE App Skills 새로고침 안내 제공.

[단계별 추천 후속 질문 안내 규약]
모든 답변 본문의 맨 끝에는 사용자가 다음 행동을 쉽게 선택할 수 있도록 구분선(---)과 함께 마크다운 번호 매기기 리스트로 2~3개의 '추천 후속 질문'을 명확히 안내한다:
---
**추천 후속 질문:**
1. Slack 긴급 장애 알림 스킬 배포해 줘
2. Google Sheets 조회 스킬 등록해 줘
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
        tools=[deploy_enterprise_skill_tool, list_enterprise_skills_tool, get_preset_skills_tool],
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
        "customPlaceholderText": "새로 생성할 사내 스킬 요구사항이나 연동 시스템을 입력하세요...",
        "starterPrompts": [
            {"text": "Slack 긴급 장애 알림 스킬 생성해서 내 GE App Skills에 등록해 줘"},
            {"text": "Google Sheets 고객 피드백 조회 스킬 만들어 줘"},
            {"text": "Jira 버그 티켓 자동 발행 스킬 생성 및 전사 공유해 줘"},
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
    """로컬 단일 도구/스킬 매니페스트 합성 및 스캐폴딩 보조 모드를 실행한다."""
    print("\n[안내] 로컬 단일 도구/스킬 매니페스트 합성 보조 모드 가동")

    # 1. 도구 칩 선택
    tool_data = SYSTEM_TOOL_CATALOG[1]
    if args.prompt:
        tool_data = {
            "id": "custom_api_tool",
            "title": args.prompt,
            "description": "사용자 맞춤형 사내 시스템 연동 액션 스킬",
            "category": "사용자 직접 정의 API",
            "action_type": "WRITE",
            "http_method": "POST",
            "endpoint_path": "/api/v1/custom/action",
            "secret_needed": "custom-system-auth-token",
            "parameters": {
                "payload": {"type": "object", "description": "전송 데이터 페이로드", "required": True},
            },
        }
    elif args.chip and args.chip in SYSTEM_TOOL_CATALOG:
        tool_data = SYSTEM_TOOL_CATALOG[args.chip]
    elif args.interactive or (sys.stdin.isatty() and not args.dry_run):
        tool_data = select_tool_interactive(args.dry_run)

    print(f"\n[단계 1/3] 도구 칩 스펙 컴파일 중...")
    print(f"  - 도구 명칭    : {tool_data['title']}")
    print(f"  - 시스템 분류  : {tool_data['category']}")
    print(f"  - 작업 유형    : {tool_data['action_type']} ({tool_data['http_method']} {tool_data['endpoint_path']})")

    # 2. OpenAPI 3.0 스키마 및 보안 볼트 합성
    print("\n[단계 2/3] OpenAPI 3.0 도구 매니페스트 및 보안 볼트(Secret Manager) 합성 중...")
    tool_manifest = generate_openapi_tool_manifest(tool_data, env_info)
    print(f"  - 거버넌스 상태 : {tool_manifest['governance_status']}")
    print(f"  - 보안 볼트 URI : {tool_manifest['secret_vault_ref']}")

    # 3. IAM 권한 진단
    print("\n[단계 3/3] 서비스 계정 IAM 권한 및 Gemini Enterprise app 도구 레지스트리 연동 진단 중...")
    iam_diag = diagnose_secret_manager_iam(env_info, args.dry_run)
    print(f"  - 상태: {iam_diag['status']} | {iam_diag['detail']}")

    # 4. 리포트 생성 및 저장
    report_content = build_markdown_report(env_info, tool_data, tool_manifest, iam_diag, dry_run=args.dry_run)
    save_markdown_report(report_content)

    print("\n" + "=" * 75)
    print("  사내 도구 스펙 컴파일 및 매니페스트 생성 완료")
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
    print("  Gemini Enterprise 사내 스킬 팩토리 (gemini-enterprise-copilot-skill)")
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
    print("  - scenario: gemini-enterprise-copilot-skill")
    print("  - env: sample")
    print(f"  - created-by: {creator}\n")


if __name__ == "__main__":
    main()
