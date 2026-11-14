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

"""금융위원회 혁신 금융 서비스(생성형 AI 망 분리 샌드박스) 사전 심사, 반려 사례 대조 및 참조 아키텍처 진단 도구.

본 모듈은 금융회사가 생성형 AI 및 SaaS 활용을 위해 혁신 금융 서비스(규제 샌드박스) 지정을 신청할 때,
금융위원회와 금융감독원, 금융보안원의 4대 심사 영역(15개 세부 항목, 46개 가중치 체크리스트) 충족도를 점검하고,
역대 불승인 및 보완 요구 사례 대조, Gemini 기반 서울 리전(asia-northeast3) 참조 블루프린트 생성,
그리고 인용 규제/기술 문서 URL의 실시간 HTTP 도달성(Fact-check)을 일괄 검증한다.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import urllib.error

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


SCENARIO_SLUG = "korea-fsc-sandbox-helper"
DEFAULT_REGION = "asia-northeast3"
DEFAULT_LOCATION = "global"
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
MANDATORY_LABELS = (
    f"managed-by=google-cloud-0-to-1,scenario={SCENARIO_SLUG},"
    "env=sample,created-by=customer-engineer"
)

# ---------------------------------------------------------------------------
# 1. 샘플 제출 신청서 초안 (초기 미비점이 포함된 현실적 샌드박스 신청서 텍스트)
# ---------------------------------------------------------------------------
SAMPLE_DRAFT_APPLICATION = """[혁신 금융 서비스 지정 신청서 초안 - example-fsi-corp]
서비스 명칭: Gemini 파인튜닝 및 RAG 기반 실시간 포용 금융 상담 및 소상공인 초고속 정산 서비스
신청 부문: 금융혁신지원 특별법 제13조 / 전자금융감독규정 제15조(망 분리 의무) 선별적 규제 특례 신청

1. 서비스의 혁신성 및 독창적 차별성
본 서비스는 대형 언어 모델을 금융 특화 데이터셋으로 미세 조정하고, 자체 특허 출원한 '실시간 금융 컨텍스트 의미 분석 인덱서 및 환각 원천 차단 파이프라인(출원번호: 10-2026-0034567)'을 탑재해 독점적 기술 장벽을 구현했다. 이는 시중 은행의 고정형 시나리오 단순 챗봇이 지닌 상황 대응적 경직성과 오안내 위협을 해결한다.

2. 규제 특례 필요성 및 지정 만료 후 출구 전략
전자금융감독규정 제15조(망 분리 의무)에 따른 선별적 규제 특례 배제를 신청한다. 이는 안전하게 보호된 클라우드 생성형 AI 게이트웨이 호출 연동을 보장받기 위한 최소 특례 조치다. 실증 보호 장치로서 일일 총 쿼리 수(QPS) 한도 및 가맹점 일일 누적 정산 자금을 총 10억 원으로 제한하고, 임계 초과 즉시 트래픽을 자동 차단하는 서킷 브레이커를 가동한다. 지정 취소나 특례 만료 시 클라우드 연동을 즉시 단절하고 소상공인 정산 데이터를 오프라인 주 전산망으로 롤백 이관하는 3단계 철수 시나리오를 구비했다.

3. 금융 소비자 편익 증대 및 포용 금융 실현 방안
금융 이력 부족자(씬파일러) 및 고령층 등 소외 계층을 배려해 AI 음성 합성 속도 조율 기능 및 모바일 간편 대화 인터페이스를 장착하여 포용 금융을 달성한다. 소상공인 정산 시스템 정합성을 T+0으로 단축해 기존 PG 카드 수수료율 대비 약 40% 감면 혜택을 부여하여 소상공인 실질 수수료를 연간 약 85억 원 경감시킨다.

4. 물리적 및 논리적 보안 통제 대책
개발, 테스트, 운영(Prod) 환경을 프로젝트 단위(GCP Project)로 분리 구획했다. 클라우드 관리 콘솔 통제를 위해 관리 단말에 VDI 가상 데스크톱 및 물리 망 분리 PC 환경을 강제화하고 하드웨어 보안 토큰(YubiKey)을 결합한 다중 인증(MFA)을 상시 강제한다. 외부 API 연동 시 사설 전용 통신망(Private Service Connect 및 전용선)만 허용하며, 단일 NAT 게이트웨이를 통한 아웃바운드 단일 경로 통제를 실현했다. 또한 1년 이상의 백업 감사 로그 보관을 위해 Cloud Storage 보존 기한 잠금을 가동하며 온프레미스 주 SIEM 관제망과 실시간 연동한다.

5. 소비자 보호 및 금융 사고 배상 구제 프로세스
환각 사고나 오답변에 의한 금전 손실 시 보상하기 위해 손해보험사와 배상 보험 계약을 유지한다. 금융감독원 분쟁조정제도와 연계된 실시간 AI 전담 사고 민원 24시간 핫라인 창구를 개설하고 접수 후 48시간 이내 피해 판정 및 구제 절차를 가동한다. 개인정보 보호법 제29조 준수를 위해 고유식별정보 및 예금계좌 원장에 무결성 서명 검증 및 HSM AES-256 하드웨어 암호화를 적용하며, 미국 중부 리전과 동부 리전 간 액티브-액티브 실시간 복제 재해 복구(DR) 시나리오를 구성해 복구 시간(RTO)을 2시간 이내로 단축한다.
"""

# ---------------------------------------------------------------------------
# 2. 금융위원회 혁신 금융 서비스 3계층 심사 트리 (4대 대분류 / 15개 중분류 / 46개 소분류, 총점 102점)
# ---------------------------------------------------------------------------
AUDIT_CHECKLIST_DB: Dict[str, Dict[str, Any]] = {
    "consumer_benefit": {
        "title": "[소비자] 금융 소비자 편익 및 보호 대책",
        "statute": "금융혁신지원 특별법 제13조 제4항 제2호, 제5호 및 시행령 제17조",
        "subcategories": {
            "1": {
                "title": "정량화된 소비자 편익 증대 증명",
                "items": {
                    "1": {
                        "title": "비용 부담 경감 요건",
                        "desc": "플랫폼 활성화를 통한 수수료 절감, 금리 인하 등 정량 증명 요건",
                        "weight": 3,
                        "keywords": ["수수료", "절감", "감면", "85억", "40%"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 기존 PG 카드 수수료율 대비 약 40% 감면 및 연간 약 85억 원 실질 수수료 경감 수치가 명시되어 있다.",
                        "remedy_clause": "본 서비스는 AI 정산 매핑을 통해 가맹점 결제 대행 수수료율을 연간 40% 이상 감면하여 소상공인 실질 수수료 비용 부담을 연 85억 원 경감시킨다.",
                    },
                    "2": {
                        "title": "거래 편의성 제공",
                        "desc": "복잡한 서류 제출 프로세스 간소화 등 거래 편의성 제공",
                        "weight": 3,
                        "keywords": ["서류", "간소화", "생략", "오프라인 검증", "편의성"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 모바일 간편 대화 인터페이스만 언급되었을 뿐, 기존 대비 어떤 오프라인 서류 제출 및 심사 단계가 몇 단계 생략/단축되는지 구체적 절차 비교가 누락되었다.",
                        "remedy_clause": "모바일 간편 대화 인터페이스를 탑재해 기존 가입 과정에서 요구되던 5종 오프라인 서류 제출 및 대면 검증 단계를 전면 생략함으로써 가입 소요 시간을 3일에서 3분 이내로 단축했다.",
                    },
                    "3": {
                        "title": "포용 금융 달성",
                        "desc": "씬파일러, 고령층 등 정규 금융 소외계층 접근성 지원 대책",
                        "weight": 3,
                        "keywords": ["씬파일러", "고령층", "소외", "포용", "음성"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 금융 이력 부족자(씬파일러) 및 고령층 대상 AI 음성 합성 속도 조율 기능과 초간편 대화 인터페이스가 명시되어 있다.",
                        "remedy_clause": "금융 이력 부족 소상공인(씬파일러) 및 고령층 대상 AI 음성 속도 조율 인터페이스와 큰 글씨 UI를 기본 제공하여 금융 소외 계층 접근성을 보장한다.",
                    },
                    "4": {
                        "title": "금전적 수혜 시뮬레이션",
                        "desc": "서비스 출시 이후 연간 기대 금융 편익의 시뮬레이션 및 정량 예측",
                        "weight": 3,
                        "keywords": ["가맹점 평균", "시뮬레이션", "1인당", "누적", "산출 근거"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 전체 연간 85억 원 총액만 기재되어 있고, 가맹점 1곳당 평균 연간 절감액 및 영세 사업자 등급별 금전적 수혜 시뮬레이션 산출 근거가 결여되었다.",
                        "remedy_clause": "서비스 출시 이후 가맹점 1곳당 평균 연 120만 원 직접 비용 절감 및 영세 사업자 금융 비용 누적 24억 원 절감 등 등급별 금전적 수혜 시뮬레이션 산출표를 구비했다.",
                    },
                },
            },
            "2": {
                "title": "금융 사고 배상 책임 및 보상 체계 마련",
                "items": {
                    "1": {
                        "title": "전문인 배상책임보험 의무 가입",
                        "desc": "시행령 제17조에 의거 사고당 10억, 연간 총 20억 배상보험 가입",
                        "weight": 3,
                        "keywords": ["10억", "20억", "시행령 제17조", "배상책임보험"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] '50억 원 배상 보험 유지'라고만 모호하게 기재되어 있으며, 시행령 제17조 법정 필수 기준인 '1사고당 10억 원 이상, 연간 총한도 20억 원 이상' 세부 보상 한도 구분 및 보험증권 증빙이 누락되었다.",
                        "remedy_clause": "금융혁신지원 특별법 시행령 제17조에 의거하여 사고 발생 시 1사고당 10억 원, 연간 총한도 20억 원 이상의 피해를 보전하는 전문인 배상 책임 보험 가입 계약을 체결 완료했다.",
                    },
                    "2": {
                        "title": "신속한 민원 및 분쟁 처리",
                        "desc": "금융감독원 연계 전담 민원 창구 구축 및 구제 가이드라인 수립",
                        "weight": 3,
                        "keywords": ["금융감독원", "분쟁", "민원", "24시간", "핫라인"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 금융감독원 분쟁조정제도와 연계된 실시간 AI 전담 사고 민원 24시간 핫라인 창구 개설이 명시되어 있다.",
                        "remedy_clause": "금융 사고 및 AI 환각 오답변 대처를 위해 금융감독원 연계 전담 민원 조정 절차와 24시간 AI 전담 민원 및 분쟁 처리 핫라인 창구를 독자 구축했다.",
                    },
                    "3": {
                        "title": "보상 시한 및 구제 프로세스 명시",
                        "desc": "민원 접수 후 처리 기한 및 구체적 배상 실행 구조를 약관화",
                        "weight": 3,
                        "keywords": ["약관", "선보상", "일시금", "영업일", "구상권"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 48시간 이내 피해 판정만 언급되어 있을 뿐, 클라우드/외부 AI 장애 시 금융회사가 선(先)보상 후 구상권을 행사한다는 약관화 조항과 배상금 지급 시한이 명시되지 않았다.",
                        "remedy_clause": "민원 접수 후 영업일 기준 3일(72시간) 이내 피해 여부를 최종 판정하고 외부 AI 공급자 귀책 시에도 당사가 선(先)보상 일시금을 지급하는 보상 시한 및 구제 프로세스를 서비스 약관에 명시했다.",
                    },
                },
            },
            "3": {
                "title": "개인 정보 및 민감 정보 완전 보호",
                "items": {
                    "1": {
                        "title": "신용정보법 및 개인정보 보호법 준수",
                        "desc": "고유식별정보 및 예금 계좌 데이터의 무결성 격리 조치",
                        "weight": 2,
                        "keywords": ["개인정보", "고유식별정보", "제29조", "가명", "격리"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 개인정보 보호법 제29조 준수 및 고유식별정보/예금계좌 원장 보호 조치가 기술되어 있다.",
                        "remedy_clause": "고유식별정보(주민등록번호 등) 및 예금 원장 계좌 데이터 처리를 Sensitive Data Protection(Cloud DLP)으로 사전 가명화 격리하여 신용정보법 및 개인정보 보호법 제29조 기술적 보호 조치를 준수한다.",
                    },
                    "2": {
                        "title": "데이터 무결성 및 검증",
                        "desc": "예금 거래 및 금융 잔액 원장 데이터의 고강도 위변조 통제 기준",
                        "weight": 2,
                        "keywords": ["무결성", "서명 검증", "위변조", "원장"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 예금계좌 원장에 무결성 서명 검증 및 HSM AES-256 암호화 적용이 명시되어 있다.",
                        "remedy_clause": "원장 예금 거래 잔액 데이터의 위변조 방지를 위해 트랜잭션 전송 구간 해시 서명 검증 및 불변 감사 추적 필터를 이중으로 가동한다.",
                    },
                    "3": {
                        "title": "구체적인 재해 복구 계획",
                        "desc": "시스템 전면 셧다운 시 개인정보 및 백업본 복구용 실질적 대책",
                        "weight": 2,
                        "keywords": ["재해 복구", "RTO", "서울 리전", "국내", "다중 가용 영역"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 치명적 갭(Gap)] 신청서에 '미국 중부 리전과 동부 리전 간 액티브-액티브 실시간 복제 재해 복구(DR)'로 기재되어 있어, 국내 금융 데이터 국외 무단 이전 및 데이터 주권 위반으로 즉시 반려 대상이다.",
                        "remedy_clause": "주 시스템 전면 셧다운에 대비해 대한민국 서울 리전(asia-northeast3) 다중 가용 영역(Multi-Zone) 및 국내 온프레미스 DR 센터 간 실시간 복제 백업망을 구획하여 국외 데이터 유출 없이 사고 시 복구 소요 시간(RTO)을 2시간 이내로 보장한다.",
                    },
                },
            },
        },
    },
    "regulatory_necessity": {
        "title": "[규제특례] 규제 특례 적용 필요성 및 실증 계획",
        "statute": "금융혁신지원 특별법 제13조 제4항 제3호, 제17조, 제21조, 제24조",
        "subcategories": {
            "1": {
                "title": "면제 신청 대상 법령의 한계 한정 요건",
                "items": {
                    "1": {
                        "title": "구체적인 개별 법 조항 적시",
                        "desc": "걸림돌이 되는 법령, 시행령, 감독규정의 특정 조항 정밀 명시",
                        "weight": 3,
                        "keywords": ["전자금융감독규정 제15조", "제13조", "특례"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 금융혁신지원 특별법 제13조 및 전자금융감독규정 제15조(망 분리 의무) 조항이 적시되어 있다.",
                        "remedy_clause": "클라우드 기반 생성형 AI 연동을 위해 전자금융거래법 제21조 및 전자금융감독규정 제15조 제1항 제3호(외부 통신망 연결 제한) 등 규제 걸림돌이 되는 구체적 개별 법 조항을 정밀 적시하여 완화를 청구한다.",
                    },
                    "2": {
                        "title": "최소 특례의 원칙",
                        "desc": "테스트에 절대적으로 필수 불가결한 최소한의 규제 완화 범위 신청",
                        "weight": 3,
                        "keywords": ["최소 특례", "선별적", "한정", "게이트웨이"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 보호된 클라우드 생성형 AI 게이트웨이 호출 연동 구간에 국한한 선별적 최소 특례 신청임이 명시되어 있다.",
                        "remedy_clause": "오직 안전하게 격리된 클라우드 가상 사설망 내부에서 생성형 AI 추론 게이트웨이(Private Service Connect)를 제한적으로 연동하는 범위에만 한정하여 최소 특례의 원칙을 준수한다.",
                    },
                    "3": {
                        "title": "법적 걸림돌 분석 소명",
                        "desc": "현행법 적용 상태에서 사업 추진이 법적으로 불가능한 장벽 소명",
                        "weight": 3,
                        "keywords": ["원천 금지", "불가능", "걸림돌", "물리적 망분리"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 특례 신청 조항만 적시했을 뿐, 현행 물리적 망 분리 규정 하에서 왜 온프레미스 구축이나 기존 방식으로는 본 서비스 구현이 법적/기술적으로 불가능한지 걸림돌 분석 소명이 누락되었다.",
                        "remedy_clause": "현행 물리적 망 분리 규정 하에서는 사내 전산망과 외부 초거대 AI 클라우드 인프라 간 실시간 API 연동이 원천 금지되어 있어, 특례 없이는 실시간 금융 컨텍스트 추론 서비스 구현이 불가능함을 소명한다.",
                    },
                },
            },
            "2": {
                "title": "금융 시장 리스크 방지를 위한 실증 한도 설정",
                "items": {
                    "1": {
                        "title": "실증 지역, 고객 수, 거래 규모 캡 제한",
                        "desc": "부작용 방지를 위한 누적 실증 인원 및 거래 액수 규모 제한",
                        "weight": 3,
                        "keywords": ["고객 수", "만 명", "실증 지역", "10억", "QPS"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 일일 QPS와 일일 누적 정산 자금(10억 원) 한도는 기재되어 있으나, 가장 중요한 '실증 대상 지역' 및 '누적 가입 고객(소상공인 가맹점) 수 상한(Cap)'이 누락되었다.",
                        "remedy_clause": "리스크 파급 방지를 위해 실증 대상 고객 수는 수도권 소상공인 5만 명 이내, 일일 API 트래픽 한도는 10,000 QPS 이내, 일일 누적 정산 한도는 최대 10억 원 이내로 상한(Cap)을 설정한다.",
                    },
                    "2": {
                        "title": "실시간 한도 제어 체계",
                        "desc": "거래 한도나 모집인 수 초과 방지를 위한 물리적 차단 시스템",
                        "weight": 3,
                        "keywords": ["서킷 브레이커", "자동 차단", "물리적", "Drop"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 한도 임계 초과 즉시 트래픽을 자동 차단하는 서킷 브레이커 가동이 명시되어 있다.",
                        "remedy_clause": "일일 누적 정산금이나 가입 고객 수, API 호출량이 설정 캡에 도달할 경우 게이트웨이 단에서 초과 요청을 즉시 차단하고 기존 룰 시스템으로 우회시키는 실시간 한도 제어 체계(Circuit Breaker)를 가동한다.",
                    },
                    "3": {
                        "title": "한도 초과 예방 비상 절차",
                        "desc": "한도 임계치 90% 도달 시 알림 발생 및 제어 작동 프로세스",
                        "weight": 3,
                        "keywords": ["90%", "사전 경보", "임계치", "SMS", "예방"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 한도 100% 초과 시 차단만 언급되어 있고, 한도 임계치 90% 도달 시 관리자 사전 경보 발송 및 신규 유입 속도 제어 등 사전 예방 비상 절차가 누락되었다.",
                        "remedy_clause": "누적 정산액 또는 트래픽 한도가 임계치 90%에 도달하는 즉시 Cloud Monitoring 및 Pub/Sub을 통해 전담 보안 운영자에게 비상 경보를 자동 발송하고 신규 유입을 제한하는 한도 초과 예방 절차를 완비했다.",
                    },
                },
            },
            "3": {
                "title": "지정 만료 이후 소비자 보호 및 출구 전략",
                "items": {
                    "1": {
                        "title": "사업 인수가 및 정식 허가 조속 추진",
                        "desc": "라이선스 획득, 정식 제휴 약정 등 유효기간 만료 후 연착륙 계획",
                        "weight": 3,
                        "keywords": ["정식 허가", "라이선스", "법제화", "연착륙", "위탁 계약"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 취소/만료 시 철수 시나리오만 기재되어 있으며, 특례 유효 기간(2년) 내 정식 인허가 취득이나 본사업 전환을 위한 연착륙 추진 로드맵이 누락되었다.",
                        "remedy_clause": "2년의 특례 기간 만료 전 전자금융감독규정 개정 정합성 확보 및 정식 보안성 심의 통과를 조속 추진하며, 서비스 운영 중 파운데이션 모델 버전 업그레이드 시에는 2026년 4월 시행된 생성형 AI 모델 변경 간소화 절차(서면확인서 제출 및 금융보안원 경미/보통/상당 영향도 분류)를 준수하여 중단 없는 정식 서비스 전환(연착륙)을 완수한다.",
                    },
                    "2": {
                        "title": "사업 정리 절차 구축",
                        "desc": "실증 실패 시 가입자 금융 자산과 정보의 회수/소멸 방안",
                        "weight": 2,
                        "keywords": ["롤백", "이관", "철수", "3단계", "회수"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 클라우드 연동을 즉시 단절하고 정산 데이터를 오프라인 주 전산망으로 롤백 이관하는 3단계 철수 시나리오가 명시되어 있다.",
                        "remedy_clause": "실증 종료 또는 중단 시 이용자 금융 자산과 데이터를 주 전산망 오프라인 스토리지로 무손실 롤백 이관하고 클라우드 내 잔존 데이터를 안전 파기하는 3단계 사업 정리 절차를 구축했다.",
                    },
                    "3": {
                        "title": "중도 중단 통지 체계",
                        "desc": "최소 30일 전 이용자 개별 고지 및 금융위 자진 보고 프로세스 마련",
                        "weight": 2,
                        "keywords": ["30일", "사전 고지", "개별 고지", "자진 보고"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 서비스 중도 중단 또는 만료 시 '최소 30일 이전 이용자 개별 고지 및 금융위원회/금융감독원 사전 자진 보고' 절차와 시한이 누락되었다.",
                        "remedy_clause": "서비스 중도 정리 또는 종료가 결정될 경우 중단 시점 최소 30일 이전에 가입 고객에게 개별 통지(앱 알림, 문자, 이메일)를 시행하고 금융위원회 및 금융감독원에 즉시 자진 보고하는 통지 체계를 수립했다.",
                    },
                },
            },
        },
    },
    "service_innovativeness": {
        "title": "[혁신성] 서비스의 혁신성 및 차별성",
        "statute": "금융혁신지원 특별법 제13조 제4항 제1호 및 제6호",
        "subcategories": {
            "1": {
                "title": "기존 금융 서비스와의 본질적 차별성 입증",
                "items": {
                    "1": {
                        "title": "유사 서비스 한계 분석",
                        "desc": "기존 금융권 유사 비즈니스 모델 및 상품의 한계 상세 분석",
                        "weight": 2,
                        "keywords": ["시중 은행", "고정형", "단순 챗봇", "경직성", "한계"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 시중 은행의 고정형 시나리오 단순 챗봇이 지닌 상황 대응적 경직성과 오안내 한계가 분석되어 있다.",
                        "remedy_clause": "시중 금융권의 기존 챗봇은 고정 시나리오 룰 기반으로 작동하여 복합 세무/정산 질의 시 유연성이 결여되고 오안내가 발생하는 한계가 있어 이를 정밀 분석해 극복했다.",
                    },
                    "2": {
                        "title": "독창성과 차별적 구조",
                        "desc": "제공 방법, 형태, 거래 구조 면에서 기존에 없던 독창성 확보",
                        "weight": 2,
                        "keywords": ["미세조정", "SFT", "인덱서", "환각 원천 차단", "벡터"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 금융 특화 지도 미세 조정(SFT)과 실시간 금융 컨텍스트 의미 분석 인덱서를 결합한 차별적 구조가 명시되어 있다.",
                        "remedy_clause": "금융 도메인 특화 미세 조정 모델과 실시간 금융 컨텍스트 의미 인덱서(RAG) 및 가드레일을 결합하여 환각 오답률을 99% 이상 차단하는 독창적 파이프라인 구조를 확보했다.",
                    },
                    "3": {
                        "title": "차별적 혜택 차트 제시",
                        "desc": "현행 금융 인프라 대비 혁신성이 확연히 드러나는 대비 표 제시",
                        "weight": 2,
                        "keywords": ["대조 차트", "비교표", "대비 표", "Table"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 정산 기간 단축(T+0)과 수수료 절감 문장만 서술되어 있을 뿐, 기존 금융 인프라 대비 항목별(처리 속도, 수수료율, 환각 차단율 등) 정량 대비 표(Comparison Chart)가 첨부되지 않았다.",
                        "remedy_clause": "기존 금융권 정산/상담 프로세스 대비 정산 소요 시간(T+5 -> T+0), 수수료 절감률(40%), 위협 차단율 지표를 직관적으로 대조한 정량 비교표(Table)를 신청서 별첨으로 제시했다.",
                    },
                },
            },
            "2": {
                "title": "결합된 기술적 실체 및 우수성 검증",
                "items": {
                    "1": {
                        "title": "고도화된 IT 기술 융합",
                        "desc": "AI, 머신 러닝, 생체인증 등 첨단 기술이 융합되어 구동되는 형태",
                        "weight": 2,
                        "keywords": ["Gemini", "파인튜닝", "벡터", "파이프라인"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 거대 언어 모델 파인튜닝, 의미 분석 인덱서, 벡터 변환 필터링 계층의 융합 구조가 제시되어 있다.",
                        "remedy_clause": "Google Cloud Vertex AI 기반 Gemini 모델과 고강도 금융 의미 임베딩 레이어, 실시간 보안 살균 가드레일을 유기적으로 결합하여 고도화된 IT 기술 융합 실체를 구현했다.",
                    },
                    "2": {
                        "title": "기술 장벽 및 독점성 소명",
                        "desc": "무단 복제 방지를 위한 특허 출원 및 독점적 알고리즘 증명",
                        "weight": 2,
                        "keywords": ["독점적", "기술 장벽", "무단 복제", "벡터 변환"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 타 기업의 무단 복제를 차단하기 위한 고유 벡터 변환 필터링 계층 및 독점적 기술 장벽이 소명되어 있다.",
                        "remedy_clause": "무단 모방이나 도용을 배제하기 위해 독점적 전처리 캐싱 인덱싱 및 금융 도메인 가드레일 알고리즘을 내재화하여 기술 장벽을 구축했다.",
                    },
                    "3": {
                        "title": "특허 및 지식재산권 내역",
                        "desc": "자체 핵심 기술에 관한 원천 설계안 및 특허 등록 번호 증적 명시",
                        "weight": 2,
                        "keywords": ["출원번호", "10-2026-0034567", "특허"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 특허 출원번호(10-2026-0034567) 및 원천 파이프라인 명칭이 구체적으로 명시되어 있다.",
                        "remedy_clause": "실시간 금융 컨텍스트 의미 분석 인덱서 및 보안 해시 마스킹 장치 특허 출원(출원번호: 10-2026-0034567) 등 지식재산권 증적 내역을 구비했다.",
                    },
                },
            },
            "3": {
                "title": "금융 시장 파급력 및 효율화 기여도",
                "items": {
                    "1": {
                        "title": "시장 혁신 및 비효율 개선",
                        "desc": "비금융 데이터 결합 등을 통한 사회적 금융 비용 경감 기여도",
                        "weight": 3,
                        "keywords": ["비금융 데이터", "대기 시간", "만 시간", "비효율 개선"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 정산 T+0 단축만 언급되었고, 비금융 대안 데이터 결합 효과 및 연간 총 몇 시간의 심사/정산 비효율을 절감하는지 사회적 비용 경감 산출치가 누락되었다.",
                        "remedy_clause": "기존 소상공인 정산 주기(T+5)를 T+0으로 단축하고 비금융 대안 데이터를 결합함으로써 연간 약 150만 시간의 심사 대기 및 사회적 금융 비효율을 감축한다.",
                    },
                    "2": {
                        "title": "핀테크 기술 생태계 활성화",
                        "desc": "이종 산업 결합을 통한 금융 생태계 외연 확장 및 활성화",
                        "weight": 3,
                        "keywords": ["생태계", "오픈소스", "스타트업", "표준", "외연 확장"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 자사 독점 기술 보호만 강조되어 있을 뿐, 국내 핀테크 스타트업이나 금융 생태계 외연 확장에 어떻게 기여하는지 생태계 활성화 방안이 전혀 없다.",
                        "remedy_clause": "금융 보안 규제를 준수하는 AI API 게이트웨이 연동 표준 규격을 중소 핀테크 기업 및 소상공인 연합회에 개방하여 국내 금융 AI 기술 생태계 활성화를 견인한다.",
                    },
                    "3": {
                        "title": "금융 생태계 활성화 수치",
                        "desc": "신시장 개척 및 고용 유발 효과에 관한 계량화된 파급 효과",
                        "weight": 2,
                        "keywords": ["고용", "인력", "창출", "신시장", "유발"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 본 서비스 도입을 통한 전문 인력 신규 고용 창출 인원수 및 연관 산업 신규 거래 유발 금액 등 계량화된 파급 효과 수치가 누락되었다.",
                        "remedy_clause": "금융 AI 보안 및 데이터 엔지니어 전문 인력 120명 직접 고용 창출 및 연관 소프트웨어 신규 거래 연 30억 원 달성 등 계량화된 생태계 파급 지표를 제시한다.",
                    },
                },
            },
        },
    },
    "technical_security": {
        "title": "[물적설비] 기술, 보안 및 논리적 망 분리 방안",
        "statute": "전자금융거래법 제21조, 전자금융감독규정 제14조의2, 제15조, 제37조 및 금융보안원 가이드라인",
        "subcategories": {
            "1": {
                "title": "환경 및 네트워크의 논리적 분리 의무",
                "items": {
                    "1": {
                        "title": "개발/테스트/운영 분리",
                        "desc": "개발, 테스트, 운영 환경 간의 완전한 논리적/물리적 분리",
                        "weight": 3,
                        "keywords": ["개발", "테스트", "운영", "프로젝트 단위", "분리"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 개발, 테스트, 운영(Prod) 환경을 GCP 프로젝트 단위로 완벽 분리 구획했음이 명시되어 있다.",
                        "remedy_clause": "클라우드 리소스를 GCP 프로젝트 및 독립 VPC 단위로 구획하여 개발, 테스트, 운영(Prod) 환경을 물리적/논리적으로 완전 분리한다.",
                    },
                    "2": {
                        "title": "비인가 접근 차단",
                        "desc": "허가된 경로 이외의 비인가 직접 통신 선로 연계 원천 차단",
                        "weight": 1,
                        "keywords": ["비인가", "횡적", "방화벽", "직접 통신 차단"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 프로젝트 분리만 언급되어 있고, 환경 간 무단 횡적 연결(Lateral Movement) 및 비인가 선로 개설을 차단하는 VPC 방화벽 기본 거부(Deny-all) 통제 명시가 누락되었다.",
                        "remedy_clause": "승인된 전용 게이트웨이 목적지 외의 환경 간 무단 횡적 통신이나 비인가 선로 개설을 VPC 방화벽 기본 거부(Default Deny) 규칙으로 원천 차단한다.",
                    },
                    "3": {
                        "title": "망 분리 예외 적용 범위",
                        "desc": "공통 관리 인프라와 외부 연계망 간의 보안성 심의 기준 준수",
                        "weight": 1,
                        "keywords": ["예외 적용 범위", "금융보안원", "한정"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 금융보안원 보안 가이드라인에 따라 망 분리 예외 적용 대상을 사내 코어 원장 DB가 아닌 전용 AI 추론 게이트웨이 서브넷으로 최소 한정한다는 경계 정의가 누락되었다.",
                        "remedy_clause": "금융보안원 보안 가이드라인에 부합하도록 내부 코어 뱅킹 원장 망은 철저히 격리하고 오직 전용 AI 추론 게이트웨이 구간에 대해서만 망 분리 예외 적용 범위를 최소 한정한다.",
                    },
                },
            },
            "2": {
                "title": "외부 인터넷 차단 및 비공개 통신 요건",
                "items": {
                    "1": {
                        "title": "외부 인터넷 직결 금지",
                        "desc": "고유식별정보나 데이터망 내부 VM의 외부 인터넷 직결 금지",
                        "weight": 3,
                        "keywords": ["Public IP", "공인 IP", "외부 인터넷 직결 금지", "vmExternalIpAccess"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] NAT 게이트웨이 경유만 기재되어 있을 뿐, 내부 VM 및 데이터 노드에 공인 IP(Public IP) 할당을 원천 금지(`constraints/compute.vmExternalIpAccess`)한다는 조항이 누락되었다.",
                        "remedy_clause": "내부 전산 자산 및 데이터 처리 노드에 공인 IP(Public IP)를 원천 할당하지 않는 조직 정책(constraints/compute.vmExternalIpAccess)을 강제하여 외부 인터넷 직결을 금지한다.",
                    },
                    "2": {
                        "title": "비공개 API 접근 통제",
                        "desc": "클라우드 서비스 API 호출 시 사설 전용 통신 경로 강제",
                        "weight": 1,
                        "keywords": ["Private Service Connect", "PSC", "사설 전용"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 외부 API 연동 시 사설 전용 통신망(Private Service Connect 및 전용선)만 허용함이 명시되어 있다.",
                        "remedy_clause": "Vertex AI 등 클라우드 API 호출 시 공인 인터넷 노출을 배제하고 Private Service Connect(PSC) 사설 전용 엔드포인트만 통과하도록 강제한다.",
                    },
                    "3": {
                        "title": "아웃바운드 단일 경로 제어",
                        "desc": "외부 인터넷 통신 필요 시 통제된 단일 게이트웨이만 통과",
                        "weight": 1,
                        "keywords": ["단일 경로", "NAT 게이트웨이", "아웃바운드"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 단일 NAT 게이트웨이를 통한 아웃바운드 경로 단일 지점 통제가 명시되어 있다.",
                        "remedy_clause": "외부 통신이 불가피한 경우 통제된 보안 프록시(SWG) 및 단일 NAT 게이트웨이로 아웃바운드 경로를 단일화하고 패킷 감사를 수행한다.",
                    },
                },
            },
            "3": {
                "title": "데이터 유출 방지 및 가상 보안 경계 설정",
                "items": {
                    "1": {
                        "title": "클라우드 내부 데이터 반출 차단",
                        "desc": "비인가된 프로젝트나 외부 IP의 데이터 무단 반출 방지 장벽",
                        "weight": 2,
                        "keywords": ["반출 차단", "내보내기", "외부 전송"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 신청서에 클라우드 내부 스토리지/데이터셋에서 외부 비인가 프로젝트로 데이터가 복사/반출되는 것을 막는 통제 대책이 전혀 기술되지 않았다.",
                        "remedy_clause": "IAM Deny 정책 및 조직 정책으로 비인가 외부 스토리지 내보내기(Export) 행위를 원천 금지하여 클라우드 내부 데이터 무단 반출을 차단한다.",
                    },
                    "2": {
                        "title": "PaaS/SaaS 보안 경계 보호",
                        "desc": "클라우드 API 레벨 신원 및 컨텍스트 기반의 보안 가상 경계",
                        "weight": 2,
                        "keywords": ["VPC Service Controls", "VPC-SC", "가상 경계", "보안 경계"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 치명적 갭(Gap)] 금융보안원 심의 핵심 요건인 VPC Service Controls(VPC-SC) 가상 보안 경계 설정(Enforced 모드)이 신청서에 완전히 누락되어 있다.",
                        "remedy_clause": "Vertex AI, Cloud Storage, BigQuery, Cloud KMS를 단일 VPC Service Controls(Enforced 강제 모드) 가상 보안 경계로 묶어 PaaS/SaaS API 레벨 보안 경계를 보호한다.",
                    },
                    "3": {
                        "title": "데이터 유출 방지 모니터링",
                        "desc": "데이터 무단 다운로드 및 반출 시도 탐지 시 실시간 차단 룰 가동",
                        "weight": 1,
                        "keywords": ["유출 방지 모니터링", "대량", "차단 룰", "Model Armor"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] 대량 파일 다운로드나 프롬프트 인젝션/탈옥 공격 기반 데이터 유출 징후 탐지 시 세션을 즉시 차단하는 DLP/Model Armor 실시간 모니터링 룰 및 금융보안원 모의 공격 기반 AI 보안성 검증 계획이 누락되었다.",
                        "remedy_clause": "서울 리전(asia-northeast3) 엄격한 데이터 레지던시 환경의 Model Armor 네이티브 SDP 필터와 온소일(On-Soil) 인라인 프롬프트 인젝션/탈옥 방어 가드레일을 이중 결합하고, 금융보안원 모의 공격 기반 AI 모델 보안성 검증을 통과하여 민감 정보 반출 징후 탐지 시 즉시 API 세션을 차단한다.",
                    },
                },
            },
            "4": {
                "title": "관리자 단말망 격리 및 접근 통제 (Bastion/IAP)",
                "items": {
                    "1": {
                        "title": "콘솔 접속 망분리 규정",
                        "desc": "콘솔 접속 단말의 논리적/물리적 망분리 및 전용 VDI 구성",
                        "weight": 3,
                        "keywords": ["VDI", "물리 망분리", "관리 단말"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 관리 단말에 대해 VDI 가상 데스크톱 및 물리 망 분리 PC 환경을 강제화함이 명시되어 있다.",
                        "remedy_clause": "클라우드 관리 콘솔 접속은 사내 물리 망 분리 단말 및 보안 VDI 가상 데스크톱에서만 Identity-Aware Proxy(IAP)를 경유하여 접속하도록 강제한다.",
                    },
                    "2": {
                        "title": "다중 인증 및 다차원 통제",
                        "desc": "콘솔 및 원격 접속 시 MFA 가동 및 단말기 무결성 검증",
                        "weight": 1,
                        "keywords": ["MFA", "다중인증", "YubiKey", "하드웨어 보안 토큰"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 하드웨어 보안 토큰(YubiKey)을 결합한 다중 인증(MFA) 상시 강제가 명시되어 있다.",
                        "remedy_clause": "하드웨어 보안 토큰(YubiKey) 기반 피싱 저항성 다중 인증(MFA)과 Context-Aware Access 단말 무결성 검증을 결합한 다차원 접근 통제를 수행한다.",
                    },
                    "3": {
                        "title": "세션 타임아웃 강제화",
                        "desc": "원격 관리 콘솔 세션의 15분 미사용 시 자동 끊김 타임아웃 강제",
                        "weight": 1,
                        "keywords": ["15분", "타임아웃", "자동 단절", "세션"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] VDI 및 MFA는 기재되어 있으나, 금융보안원 필수 점검 항목인 '관리자 콘솔 세션 15분 이상 입력 부재 시 자동 로그아웃(세션 타임아웃 강제화)' 설정이 누락되었다.",
                        "remedy_clause": "원격 관리자 콘솔 및 VDI 세션에서 15분 이상 입력 부재 발생 시 즉시 접속 세션을 자동 단절하는 세션 타임아웃 강제화 정책(gcloud auth/Cloud Identity 세션 제어)을 적용했다.",
                    },
                },
            },
            "5": {
                "title": "데이터 암호화 및 암호 키 통제 권한",
                "items": {
                    "1": {
                        "title": "전송 및 보관 암호화 의무",
                        "desc": "전송 중 TLS 1.3 및 보관 중 AES-256 고강도 암호화 의무 준수",
                        "weight": 3,
                        "keywords": ["AES-256", "TLS", "암호화"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 고유식별정보 및 원장에 AES-256 하드웨어 암호화 적용이 명시되어 있다.",
                        "remedy_clause": "모든 네트워크 전송 구간에 TLS 1.3 암호화를 강제하고 보관 스토리지 및 원장 DB에 AES-256 암호화를 적용하여 전송 및 보관 암호화 의무를 이행한다.",
                    },
                    "2": {
                        "title": "금융회사 직접 통제 권한",
                        "desc": "암호 키 생성, 회전, 폐기 전 과정에 대한 직접 제어권 확보",
                        "weight": 1,
                        "keywords": ["직접 통제", "CMEK", "키 회전", "주기적", "폐기"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] HSM AES-256 사용만 언급되어 있고, 클라우드 사업자 기본 키(GMEK)가 아닌 금융회사가 암호 키의 생성, 90일 주기 회전, 긴급 폐기 권한을 직접 행사(CMEK)한다는 소명이 누락되었다.",
                        "remedy_clause": "암호 키의 생성, 90일 주기 자동 순환(Rotation), 긴급 폐기 전 과정에 대한 통제권을 클라우드 사업자에 위임하지 않고 당사가 고객 관리 암호화 키(CMEK)로 직접 행사한다.",
                    },
                    "3": {
                        "title": "HSM 기반 키 관리",
                        "desc": "중요 암호 키의 안전한 보관을 위한 전용 KMS 또는 HSM 장비 활용",
                        "weight": 1,
                        "keywords": ["HSM", "하드웨어 암호"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] HSM 하드웨어 기반 암호화 적용이 명시되어 있다.",
                        "remedy_clause": "서울 리전(asia-northeast3) Cloud HSM(FIPS 140-3 Level 3 인증 하드웨어 보안 모듈) 내부에서 암호 키를 생성 및 보관하여 물리적 키 탈취를 원천 방지한다.",
                    },
                },
            },
            "6": {
                "title": "보안 관제 및 실시간 감사 로깅",
                "items": {
                    "1": {
                        "title": "감사 로그 위변조 방지",
                        "desc": "작업 감사 로그의 최소 2년 이상 보존 및 안전한 분리 백업 통제",
                        "weight": 3,
                        "keywords": ["2년", "730일", "위변조 방지", "Bucket Lock"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 치명적 갭(Gap)] 신청서 4번 항목에 '1년 이상의 백업 감사 로그 보관'이라고 잘못 기재되어 있다. 금융보안원 가이드라인상 감사 로그는 최소 '2년(730일) 이상' 불변 보존(WORM Bucket Lock)해야 하므로 즉시 반려 사유다.",
                        "remedy_clause": "내부자나 해킹에 의한 로그 삭제/위변조를 막기 위해 Cloud Storage Bucket Lock(보존 기한 잠금)을 2년(730일) 이상으로 강제 설정하여 감사 로그 및 프롬프트 이력의 위변조 방지를 이행한다.",
                    },
                    "2": {
                        "title": "통합 모니터링 체계",
                        "desc": "네트워크 흐름 및 감사 로그의 실시간 중앙 관제 연동 체계",
                        "weight": 1,
                        "keywords": ["SIEM", "관제망", "실시간 연동"],
                        "sample_fulfilled": True,
                        "sample_reason": "[신청서 확인] 온프레미스 주 SIEM 관제망과 24시간 실시간 연동함이 명시되어 있다.",
                        "remedy_clause": "클라우드 내 VPC 플로우 로그 및 Data Access 감사 로그를 당사 온프레미스 중앙 SIEM 통합 보안 관제 체계와 실시간 연동하여 상시 감사한다.",
                    },
                    "3": {
                        "title": "감사 로그 모니터링 경보",
                        "desc": "중요 보안 정책 변경 또는 침해 탐지 시 즉각 경보 발생 룰 적용",
                        "weight": 1,
                        "keywords": ["경보", "Alert", "정책 변경", "침해 탐지"],
                        "sample_fulfilled": False,
                        "sample_reason": "[제출서 갭(Gap)] SIEM 연동만 언급되어 있고, KMS 키 정책 변경이나 VPC-SC 경계 해제 등 중요 보안 이벤트 발생 시 보안 책임자에게 즉각 발송되는 실시간 경보(Alert) 룰 명세가 누락되었다.",
                        "remedy_clause": "보안 정책 무단 변경이나 침해 징후 탐지 시 즉시 보안 관리 책임자에게 긴급 알림(SMS/PubSub Alert)을 발송하는 실시간 감사 로그 모니터링 경보 규칙을 적용했다.",
                    },
                },
            },
        },
    },
}

# ---------------------------------------------------------------------------
# 2. 금융위원회/금융보안원 역대 주요 반려 및 보완 요구 사례 DB (15개 세부 영역 대표 사례)
# ---------------------------------------------------------------------------
REJECTION_CASES_DB: List[Dict[str, str]] = [
    {
        "category": "consumer_benefit",
        "sub_id": "1",
        "case_id": "REJ-CB-01",
        "title": "정량적 소비자 편익 수치 및 산출 근거 누락",
        "reason": "AI 도입을 통한 내부 임직원 업무 효율성만 강조하고, 일반 금융 소비자에게 돌아가는 수수료 인하율이나 처리 시간 단축 등 정량화된 금전적/시간적 편익 수치를 제시하지 못하여 보완 요구 판정을 받았다.",
        "ref_url": "https://sandbox.fsc.or.kr",
    },
    {
        "category": "consumer_benefit",
        "sub_id": "2",
        "case_id": "REJ-CB-02",
        "title": "법정 한도(사고당 10억 원/연간 20억 원) 미달 및 외주 책임 전가",
        "reason": "클라우드 및 외부 AI 모델 오류로 인한 소비자 피해 발생 시 클라우드 사업자 약관에 책임을 전가하거나, 시행령 제17조가 정한 배상 책임 보험 가입 증빙을 누락하여 심사에서 탈락했다.",
        "ref_url": "https://www.fintech.or.kr",
    },
    {
        "category": "consumer_benefit",
        "sub_id": "3",
        "case_id": "REJ-CB-03",
        "title": "외부 생성형 AI 전송 구간 가명 처리 및 무학습 보장 미비",
        "reason": "고객 실명, 계좌번호 등 개인 신용 정보가 가명화/마스킹 필터링 없이 외부 LLM 프롬프트에 평문 유입될 위험이 방치되어 있고, 모델 사업자의 무학습(No-Training) 기술적 통제 증빙이 누락되어 반려되었다.",
        "ref_url": "https://www.fsec.or.kr",
    },
    {
        "category": "regulatory_necessity",
        "sub_id": "1",
        "case_id": "REJ-RN-01",
        "title": "대상 법령 조항 불명확 및 포괄적 망 분리 면제 신청",
        "reason": "전자금융감독규정 제15조의 특정 호/목이 아닌 보안 규정 전반에 대한 포괄적 특례를 신청하거나, 현행 규정 하에서도 온프레미스 구현이 가능한 단순 워크로드를 신청하여 최소 특례 원칙 위반으로 기각되었다.",
        "ref_url": "https://sandbox.fsc.or.kr",
    },
    {
        "category": "regulatory_necessity",
        "sub_id": "2",
        "case_id": "REJ-RN-02",
        "title": "실증 한도(Cap) 미설정 및 이상 징후 서킷 브레이커 부재",
        "reason": "실증 기간 중 대상 고객 수와 거래 한도를 제한하지 않고 전 고객 대상 전면 오픈을 계획하거나, AI 환각 급증 시 즉각 서비스를 차단하고 기존 시스템으로 복귀하는 차단기(Circuit Breaker)가 없어 반려되었다.",
        "ref_url": "https://www.fintech.or.kr",
    },
    {
        "category": "regulatory_necessity",
        "sub_id": "3",
        "case_id": "REJ-RN-03",
        "title": "특례 만료 후 소비자 데이터 이관 및 출구 전략(Exit Plan) 누락",
        "reason": "특례 지정 기간(2년) 종료 후 법령 개정이 지연되거나 정식 인허가를 받지 못할 경우의 30일 전 고객 통지, 데이터 무손실 백업 및 대체 절차 전환 계획이 전무하여 심사 보류 판정을 받았다.",
        "ref_url": "https://sandbox.fsc.or.kr",
    },
    {
        "category": "service_innovativeness",
        "sub_id": "1",
        "case_id": "REJ-SI-01",
        "title": "단순 상용 LLM API 래퍼(Wrapper) 구조로 기존 서비스 대비 차별성 미달",
        "reason": "금융 도메인 특화 지식 베이스(RAG) 결합이나 독자적 리스크 통제 파이프라인 없이 범용 챗봇 UI만 연결한 구조로, 시중 금융 앱 대비 혁신성과 차별성이 부족하다는 평가를 받았다.",
        "ref_url": "https://www.fintech.or.kr",
    },
    {
        "category": "service_innovativeness",
        "sub_id": "2",
        "case_id": "REJ-SI-02",
        "title": "사내 PoC 실측 검증 데이터 부재 및 구상 단계 신청",
        "reason": "아키텍처 설계도와 PoC 정확도/환각 차단율 실측 데이터가 전혀 준비되지 않은 아이디어 구상 상태에서 신청하여, 지정 후 조속한 실증 착수가 불가능하다고 판단되어 탈락했다.",
        "ref_url": "https://sandbox.fsc.or.kr",
    },
    {
        "category": "technical_security",
        "sub_id": "1",
        "case_id": "REJ-TS-01",
        "title": "개발망/운영망 VPC 혼용 및 내부 코어 뱅킹 DB 직접 연결 방치",
        "reason": "클라우드 샌드박스 환경 내 개발/테스트 리소스와 운영 리소스가 동일 VPC 서브넷에 혼재되어 있고, 외부 AI 응답이 내부 코어 뱅킹 망으로 무검증 역유입될 수 있는 구조여서 부적격 판정을 받았다.",
        "ref_url": "https://www.fsec.or.kr",
    },
    {
        "category": "technical_security",
        "sub_id": "2",
        "case_id": "REJ-TS-02",
        "title": "공인 IP 경유 퍼블릭 인터넷 API 호출 및 비공개 연결(PSC) 미적용",
        "reason": "Vertex AI 및 외부 SaaS 호출 시 Private Service Connect(PSC)나 전용선 비공개 경로를 구성하지 않고 공인 IP NAT 게이트웨이를 통해 공중 인터넷으로 통신하도록 설계하여 망 분리 대체 통제 미달로 반려되었다.",
        "ref_url": "https://www.fsec.or.kr",
    },
    {
        "category": "technical_security",
        "sub_id": "3",
        "case_id": "REJ-TS-03",
        "title": "VPC Service Controls(VPC-SC) 미설정 또는 감사 모드(Dry-run) 방치",
        "reason": "클라우드 내부 데이터 유출을 막는 가상 보안 경계(VPC-SC)를 아예 구성하지 않거나 실제 차단 효력이 없는 Dry-run 모드로만 열어두어, 인가되지 않은 외부 프로젝트로의 데이터 반출 위험이 지적되었다.",
        "ref_url": "https://cloud.google.com/vpc-service-controls/docs/overview",
    },
    {
        "category": "technical_security",
        "sub_id": "4",
        "case_id": "REJ-TS-04",
        "title": "관리자 단말(VDI) 망 분리 미준수 및 Context-Aware Access 누락",
        "reason": "클라우드 콘솔 및 API에 일반 인터넷 단말에서 직접 접속이 가능하고, IP/기기 인증서 기반 맥락 인식 접근 통제(CAA)와 15분 세션 타임아웃 정책이 누락되어 금융보안원 취약점 점검에서 불합격했다.",
        "ref_url": "https://cloud.google.com/beyondcorp-enterprise/docs/context-aware-access-overview",
    },
    {
        "category": "technical_security",
        "sub_id": "5",
        "case_id": "REJ-TS-05",
        "title": "클라우드 기본 암호화 키(GMEK) 사용 및 금융회사 키 통제권(CMEK) 부재",
        "reason": "고객 관리 암호화 키(CMEK)와 Cloud HSM을 적용하지 않고 클라우드 사업자 기본 키(GMEK)에 의존하여, 금융회사의 암호 키 직접 통제 및 폐기 권한 요건(전자금융감독규정 제37조)을 충족하지 못했다.",
        "ref_url": "https://cloud.google.com/kms/docs/cmek",
    },
    {
        "category": "technical_security",
        "sub_id": "6",
        "case_id": "REJ-TS-06",
        "title": "감사 로그 WORM(Bucket Lock) 미적용 및 프롬프트 입출력 이력 누락",
        "reason": "Data Access 감사 로그와 AI 프롬프트/응답 로그를 일반 스토리지에만 보관하여 관리자에 의한 임의 삭제/위변조가 가능했고, 2년 이상 불변 보존(Bucket Lock) 정책이 빠져 보완 조치가 요구되었다.",
        "ref_url": "https://cloud.google.com/storage/docs/bucket-lock",
    },
]

# ---------------------------------------------------------------------------
# 3. 검증 대상 공식 규제 기관 및 Google Cloud 기술 문서 URL 목록
# ---------------------------------------------------------------------------
CANONICAL_REFERENCE_URLS: List[Tuple[str, str]] = [
    ("금융규제 샌드박스 공식 포털", "https://sandbox.fsc.or.kr"),
    ("금융보안원 (FSEC)", "https://www.fsec.or.kr"),
    ("한국핀테크지원센터", "https://www.fintech.or.kr"),
    ("VPC Service Controls 아키텍처 가이드", "https://cloud.google.com/vpc-service-controls/docs/overview"),
    ("Cloud KMS 고객 관리 암호화 키(CMEK)", "https://cloud.google.com/kms/docs/cmek"),
    ("Cloud Storage Bucket Lock (WORM)", "https://cloud.google.com/storage/docs/bucket-lock"),
    ("Sensitive Data Protection (Cloud DLP)", "https://cloud.google.com/sensitive-data-protection/docs/concepts-one-to-one"),
    ("Vertex AI 데이터 거버넌스 및 무학습 보장", "https://cloud.google.com/vertex-ai/generative-ai/docs/data-governance"),
]


def run_gcloud_cmd(args: List[str], timeout: int = 12) -> Tuple[int, str, str]:
    """gcloud CLI 명령어를 안전하게 실행하고 (returncode, stdout, stderr)를 반환한다."""
    try:
        proc = subprocess.run(
            ["gcloud"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)


def resolve_project_id(cli_project: Optional[str], dry_run: bool) -> str:
    """5단계 캐스케이드 우선순위에 따라 대상 GCP 프로젝트 ID를 결정한다."""
    if cli_project:
        return cli_project
    env_proj = os.getenv("PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if env_proj:
        return env_proj
    if dry_run:
        return "sample-project-id"

    rc, out, _ = run_gcloud_cmd(["config", "get-value", "project"])
    if rc == 0 and out and out != "(unset)":
        return out

    if sys.stdin.isatty():
        rc_list, out_list, _ = run_gcloud_cmd(
            ["projects", "list", "--format=value(projectId)", "--limit=10"]
        )
        candidates = [line.strip() for line in out_list.splitlines() if line.strip()] if rc_list == 0 else []
        if len(candidates) > 1:
            print("\n[안내] 다수의 GCP 프로젝트가 감지되었다. 진단할 프로젝트 번호를 선택한다:")
            for idx, cand in enumerate(candidates, 1):
                print(f"  [{idx}] {cand}")
            choice = input("번호 입력 (Enter 입력 시 1번 자동 선택): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(candidates):
                return candidates[int(choice) - 1]
            return candidates[0]
        if len(candidates) == 1:
            return candidates[0]

    return "sample-project-id"


def run_config_wizard() -> int:
    """대화형 환경 설정 마법사(--config)를 실행하여 .env 파일을 생성한다."""
    print("=" * 76)
    print("[대화형 설정 마법사] 금융위원회 혁신 금융 서비스 샌드박스 사전 심사 환경 구성")
    print("=" * 76)

    _, default_proj, _ = run_gcloud_cmd(["config", "get-value", "project"])
    if not default_proj or default_proj == "(unset)":
        default_proj = "sample-project-id"

    if sys.stdin.isatty():
        proj = input(f"1. 대상 GCP 프로젝트 ID [{default_proj}]: ").strip() or default_proj
        region = input(f"2. 금융 인프라 리전 [{DEFAULT_REGION}]: ").strip() or DEFAULT_REGION
        loc = input(f"3. Gemini API 리전 [{DEFAULT_LOCATION}]: ").strip() or DEFAULT_LOCATION
        cat = input("4. 집중 심사 영역 (all/consumer_benefit/regulatory_necessity/service_innovativeness/technical_security) [all]: ").strip() or "all"
        prop = input("5. 신청서 초안 파일 경로 (없으면 Enter): ").strip()
    else:
        proj, region, loc, cat, prop = default_proj, DEFAULT_REGION, DEFAULT_LOCATION, "all", ""

    env_path = Path(__file__).resolve().parent / ".env"
    env_content = (
        "# Copyright 2026 Google LLC. All Rights Reserved.\n"
        "# SPDX-License-Identifier: Apache-2.0\n\n"
        f"PROJECT_ID={proj}\n"
        f"REGION={region}\n"
        f"GOOGLE_CLOUD_LOCATION={loc}\n"
        f"GEMINI_MODEL={DEFAULT_GEMINI_MODEL}\n"
        f"SANDBOX_CATEGORY={cat}\n"
        f"PROPOSAL_PATH={prop}\n"
    )
    env_path.write_text(env_content, encoding="utf-8")
    print(f"\n[완료] 환경 변수 파일이 생성되었다: {env_path}")
    return 0


def load_proposal_text(proposal_path_str: str) -> Tuple[Optional[str], str]:
    """신청서 초안 파일(.md, .txt, .pdf)을 읽어 텍스트와 출처 설명을 반환한다."""
    if not proposal_path_str:
        return None, "내장 샘플 신청서 초안 (example-fsi-corp 초기 제출본)"

    prop_path = Path(proposal_path_str).expanduser()
    if not prop_path.is_file():
        return None, f"지정 파일 미존재({proposal_path_str}) -> 내장 샘플 신청서 초안 자동 적용"

    if prop_path.suffix.lower() == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(prop_path))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages).strip()
            if text:
                return text, f"제출 신청서 PDF ({prop_path.name}, {len(reader.pages)}쪽)"
        except Exception as exc:
            return None, f"PDF 파싱 실패({exc}) -> 내장 샘플 신청서 초안 자동 적용"

    text = prop_path.read_text(encoding="utf-8", errors="ignore").strip()
    if text:
        return text, f"제출 신청서 문서 ({prop_path.name}, {len(text)}자)"
    return None, "빈 신청서 파일 -> 내장 샘플 신청서 초안 자동 적용"


def evaluate_single_leaf_item(
    cat_key: str,
    sub_id: str,
    item_id: str,
    item_data: Dict[str, Any],
    proposal_text: Optional[str],
    live_signals: Dict[str, bool],
    dry_run: bool,
) -> Tuple[bool, str]:
    """단일 소분류(category:sub_id:item_id) 요건과 제출 신청서 본문 간의 1:1 갭(Gap)을 판정한다."""
    if proposal_text:
        lower_text = proposal_text.lower()
        keywords = item_data.get("keywords", [])
        matched_kws = [kw for kw in keywords if kw.lower() in lower_text]

        # 치명적 위반 패턴 검사 (미국 리전 DR, 1년 감사 로그 등)
        if cat_key == "consumer_benefit" and sub_id == "3" and item_id == "3":
            if "미국" in proposal_text or "us-central" in lower_text or "us-east" in lower_text:
                return (
                    False,
                    "[제출서 치명적 갭(Gap)] 신청서 내 해외(미국) 리전 재해 복구 복제가 기재되어 있어 국내 금융 데이터 주권 위반으로 반려 대상이다.",
                )
        if cat_key == "technical_security" and sub_id == "6" and item_id == "1":
            if "1년" in proposal_text and "2년" not in proposal_text and "730일" not in proposal_text:
                return (
                    False,
                    "[제출서 치명적 갭(Gap)] 감사 로그 보존 기한이 '1년'으로 기재되어 있어 법정 의무(최소 2년/730일 이상 WORM 잠금) 미달이다.",
                )

        required_hits = max(2, (len(keywords) + 1) // 2)
        if len(matched_kws) >= required_hits:
            return (
                True,
                f"[신청서 소명 확인] 핵심 요건 키워드({', '.join(matched_kws[:4])}) 및 구체적 이행 방안이 신청서 본문에서 확인되었다.",
            )
        return (
            False,
            item_data["sample_reason"],
        )

    # 신청서 별도 파일 미지정 시 내장 초기 제출서(SAMPLE_DRAFT_APPLICATION) 대조 결과 사용
    fulfilled = bool(item_data["sample_fulfilled"])
    reason = str(item_data["sample_reason"])

    if not dry_run:
        if cat_key == "technical_security" and sub_id == "5" and item_id == "2" and live_signals.get("has_cmek_keyring"):
            fulfilled = True
            reason = "[실환경 확인] 서울 리전 Cloud KMS 키링이 감지되어 CMEK 직접 통제 기반이 확인되었다."
        if cat_key == "technical_security" and sub_id == "6" and item_id == "1" and live_signals.get("has_locked_bucket"):
            fulfilled = True
            reason = "[실환경 확인] Cloud Storage 버킷 Retention Policy(WORM 잠금) 설정이 확인되었다."

    return fulfilled, reason


def evaluate_sandbox_readiness(
    project_id: str,
    region: str,
    category_filter: str,
    proposal_text: Optional[str],
    dry_run: bool,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, str]]]:
    """4대 대분류 / 15개 중분류 / 46개 소분류 전수 대조 및 갭(Gap) 분석을 수행한다."""
    leaf_results: List[Dict[str, Any]] = []
    sub_results: List[Dict[str, Any]] = []
    matched_rejections: List[Dict[str, str]] = []

    live_signals: Dict[str, bool] = {}
    gemini_eval_map: Dict[str, Tuple[bool, str]] = {}
    if not dry_run:
        if proposal_text:
            try:
                from google import genai
                client = genai.Client(vertexai=True, project=project_id, location=DEFAULT_LOCATION)
                items_spec = []
                for ck, cd in AUDIT_CHECKLIST_DB.items():
                    if category_filter != "all" and ck != category_filter:
                        continue
                    for sid, sd in cd["subcategories"].items():
                        for iid, idata in sd["items"].items():
                            items_spec.append(f"- {ck}:{sid}:{iid} | {idata['title']}: {idata['desc']}")
                eval_prompt = (
                    "너는 금융위원회 혁신 금융 서비스 신청서의 46개 소분류 요건을 제출 신청서 본문과 1:1로 대조 판정하는 AI 심사역이다.\n"
                    "각 소분류 ID에 대해 신청서가 구체적 수치와 기술적 통제를 명시했으면 fulfilled=true, 미비하거나 위반이면 fulfilled=false와 문어체(-다 체) 사유(reason)를 JSON 배열로 반환하라.\n"
                    "출력 형식: [{\"item_id\": \"category:sub:item\", \"fulfilled\": true, \"reason\": \"...\"}]\n\n"
                    "[소분류 요건 목록]\n" + "\n".join(items_spec) + "\n\n[제출 신청서 본문]\n" + proposal_text[:12000]
                )
                resp = client.models.generate_content(model=DEFAULT_GEMINI_MODEL, contents=eval_prompt)
                raw_txt = (getattr(resp, "text", "") or "").strip()
                json_match = re.search(r"\[.*\]", raw_txt, flags=re.S)
                if json_match:
                    parsed_list = json.loads(json_match.group(0))
                    for entry in parsed_list:
                        if isinstance(entry, dict) and "item_id" in entry:
                            gemini_eval_map[str(entry["item_id"])] = (
                                bool(entry.get("fulfilled", False)),
                                str(entry.get("reason", "")),
                            )
            except Exception:
                pass
        else:
            rc_kms, out_kms, _ = run_gcloud_cmd(
                ["kms", "keyrings", "list", f"--location={region}", f"--project={project_id}", "--format=json"]
            )
            live_signals["has_cmek_keyring"] = rc_kms == 0 and out_kms not in ("", "[]")
            rc_bkt, out_bkt, _ = run_gcloud_cmd(
                ["storage", "buckets", "list", f"--project={project_id}", "--format=json"]
            )
            live_signals["has_locked_bucket"] = rc_bkt == 0 and '"retentionPolicy"' in out_bkt

    for cat_key, cat_data in AUDIT_CHECKLIST_DB.items():
        if category_filter != "all" and cat_key != category_filter:
            continue

        for sub_id, sub_data in sorted(cat_data["subcategories"].items(), key=lambda x: int(x[0])):
            sub_earned = 0
            sub_max = 0
            sub_gap_titles: List[str] = []
            sub_leafs: List[Dict[str, Any]] = []

            for item_id, item_data in sorted(sub_data["items"].items(), key=lambda x: int(x[0])):
                weight = int(item_data["weight"])
                sub_max += weight
                item_id_full = f"{cat_key}:{sub_id}:{item_id}"

                if item_id_full in gemini_eval_map:
                    fulfilled, reason = gemini_eval_map[item_id_full]
                else:
                    fulfilled, reason = evaluate_single_leaf_item(
                        cat_key=cat_key,
                        sub_id=sub_id,
                        item_id=item_id,
                        item_data=item_data,
                        proposal_text=proposal_text,
                        live_signals=live_signals,
                        dry_run=dry_run,
                    )
                earned = weight if fulfilled else 0
                sub_earned += earned
                if not fulfilled:
                    sub_gap_titles.append(f"{item_id_full} {item_data['title']}")

                leaf_entry = {
                    "item_id_full": item_id_full,
                    "category_key": cat_key,
                    "category_title": cat_data["title"],
                    "statute": cat_data["statute"],
                    "sub_id": sub_id,
                    "sub_title": sub_data["title"],
                    "item_id": item_id,
                    "item_title": item_data["title"],
                    "item_desc": item_data["desc"],
                    "weight": weight,
                    "fulfilled": fulfilled,
                    "status": "PASS" if fulfilled else "GAP",
                    "earned_score": earned,
                    "reason": reason,
                    "remedy_clause": item_data["remedy_clause"],
                }
                leaf_results.append(leaf_entry)
                sub_leafs.append(leaf_entry)

            if sub_earned == sub_max:
                sub_status = "PASS"
                sub_finding = f"하위 소분류 {len(sub_leafs)}개 요건 전수 충족"
            elif sub_earned == 0 or sub_earned <= sub_max // 3:
                sub_status = "REJECT_RISK"
                sub_finding = f"미비 소분류 {len(sub_gap_titles)}건 ({', '.join(sub_gap_titles)})"
            else:
                sub_status = "WARN"
                sub_finding = f"보완 필요 소분류 {len(sub_gap_titles)}건 ({', '.join(sub_gap_titles)})"

            sub_results.append({
                "category_key": cat_key,
                "category_title": cat_data["title"],
                "statute": cat_data["statute"],
                "sub_id": sub_id,
                "sub_name": sub_data["title"],
                "status": sub_status,
                "earned_score": sub_earned,
                "max_score": sub_max,
                "leaf_count": len(sub_leafs),
                "gap_count": len(sub_gap_titles),
                "finding": sub_finding,
            })

            if sub_status in ("REJECT_RISK", "WARN"):
                for rej in REJECTION_CASES_DB:
                    if rej["category"] == cat_key and rej["sub_id"] == sub_id:
                        matched_rejections.append(rej)

    return leaf_results, sub_results, matched_rejections


def simulate_remedy_clause(
    item_id_full: str,
    remedy_text: str,
    project_id: str,
    location: str,
    model_name: str,
    dry_run: bool,
) -> int:
    """특정 소분류(category:sub_id:item_id)에 대한 사용자 보완 문구(remedy_text)의 적합성과 가점 효과를 시뮬레이션한다."""
    parts = item_id_full.split(":")
    if len(parts) != 3:
        print(f"[오류] 유효하지 않은 소분류 ID 형식이다 ({item_id_full}). 예: technical_security:6:1")
        return 1

    cat_key, sub_id, item_id = parts
    cat_data = AUDIT_CHECKLIST_DB.get(cat_key)
    sub_data = cat_data["subcategories"].get(sub_id) if cat_data else None
    item_data = sub_data["items"].get(item_id) if sub_data else None
    if not item_data:
        print(f"[오류] 체크리스트에서 해당 소분류 ID를 찾을 수 없다: {item_id_full}")
        return 1

    weight = int(item_data["weight"])
    keywords = item_data.get("keywords", [])
    matched_kws = [kw for kw in keywords if kw.lower() in remedy_text.lower()]
    fulfilled = len(matched_kws) >= max(1, len(keywords) // 2) and len(remedy_text.strip()) >= 30
    reason = (
        f"보완 문구 내 핵심 법정/기술 요건 키워드({', '.join(matched_kws)})와 구체적 실행 방안이 확인되어 요건을 충족한다."
        if fulfilled
        else f"보완 문구에 구체적 법령 수치 또는 핵심 기술 통제 키워드({', '.join(keywords)})가 부족하여 추가 구체화가 필요하다."
    )

    if not dry_run:
        try:
            from google import genai
            client = genai.Client(vertexai=True, project=project_id, location=location)
            prompt = (
                f"너는 금융위원회 혁신 금융 서비스 소분류 요건 검증 시뮬레이터다.\n"
                f"- 대상 소분류 ID: {item_id_full}\n"
                f"- 요건명: {item_data['title']}\n"
                f"- 상세 기준: {item_data['desc']}\n"
                f"- 제출된 보완 문구: \"{remedy_text}\"\n\n"
                "위 보완 문구가 해당 소분류 요건을 충족하는지 2문장 이내의 문어체(-다 체)로 판정 사유를 작성하라."
            )
            resp = client.models.generate_content(model=model_name, contents=prompt)
            if resp and getattr(resp, "text", None):
                reason = resp.text.strip()
        except Exception:
            pass

    print("=" * 84)
    print(f"[소분류 핀포인트 자가 보완 시뮬레이션 결과] 대상 ID: {item_id_full}")
    print("=" * 84)
    print(f" - 대분류 / 중분류 : {cat_data['title']} > {sub_data['title']}")
    print(f" - 소분류 요건명   : {item_data['title']} (배점: {weight}점)")
    print(f" - 법정 상세 기준  : {item_data['desc']}")
    print(f" - 입력 보완 문구  : {remedy_text}")
    print(f" - 시뮬레이션 판정 : {'[PASS / 충족]' if fulfilled else '[GAP / 보완 미흡]'} (획득 가점: +{weight if fulfilled else 0}점)")
    print(f" - 상세 판정 사유  : {reason}")
    print(f" - 모범 극복 문구  : {item_data['remedy_clause']}")
    print("=" * 84)
    return 0


def generate_reference_blueprint(
    project_id: str,
    region: str,
    location: str,
    model_name: str,
    sub_results: List[Dict[str, Any]],
    dry_run: bool,
) -> Tuple[str, str]:
    """Gemini(gemini-3.8-flash, global) 또는 결정론적 엔진을 통해 금융 보안 참조 블루프린트를 생성한다."""
    risk_items = [r["sub_name"] for r in sub_results if r["status"] != "PASS"]
    deterministic_blueprint = (
        f"1. **망 분리 대체 논리적 격리 및 비공개 전용 통신 (`{region}`)**:\n"
        f"   - 사내 업무망/전산망(On-Premises)과 GCP 금융 샌드박스 프로젝트(`{project_id}`) 간 Dedicated Interconnect 및 Private Service Connect(PSC) 엔드포인트를 구성하여 공중 인터넷 경로를 원천 배제한다 (`technical_security:1:1~2:3` 충족).\n"
        "   - 조직 정책(`constraints/compute.vmExternalIpAccess`)으로 모든 워크로드의 공인 IP 할당을 차단한다.\n"
        "2. **가상 보안 경계(VPC-SC Enforced) 및 입출력 가드레일 결합**:\n"
        "   - Vertex AI, BigQuery, Cloud Storage, Cloud KMS를 단일 VPC Service Controls(Enforced 모드) 보안 경계로 묶어 외부 프로젝트로의 데이터 반출을 차단한다 (`technical_security:3:1~3:3` 충족).\n"
        "   - 프롬프트 전송 전 Sensitive Data Protection(Cloud DLP)으로 개인 신용 정보를 가명/익명화하고, Model Armor로 프롬프트 인젝션 및 유해 응답을 실시간 살균한다 (`consumer_benefit:3:1` 충족).\n"
        f"3. **금융회사 직접 통제 암호화(Cloud HSM CMEK), 2년 불변 감사 로깅(WORM) 및 국내 DR**:\n"
        f"   - 서울 리전(`{region}`) Cloud HSM 기반 CMEK 키를 바인딩하여 전자금융감독규정 제37조 암호 키 직접 통제권 요건을 충족한다 (`technical_security:5:1~5:3` 충족).\n"
        "   - 모든 관리자 행위, 데이터 접근(Data Access), Gemini 프롬프트/응답 이력을 Bucket Lock(730일 Retention)이 걸린 서울 리전 불변 스토리지에 강제 싱크하고(`technical_security:6:1~6:3` 충족), 실증 한도 90% 도달 시 자동 서킷 브레이커(Circuit Breaker)를 발동한다 (`regulatory_necessity:2:1~2:3` 충족)."
    )

    if dry_run:
        return deterministic_blueprint, f"Dry-Run Deterministic Blueprint ({model_name} / {location})"

    try:
        from google import genai
        client = genai.Client(vertexai=True, project=project_id, location=location)
        prompt = (
            "당신은 대한민국 금융위원회 혁신 금융 서비스(생성형 AI 망 분리 규제 샌드박스) 및 금융보안원 보안성 심의 수석 아키텍트다. "
            f"대상 프로젝트 `{project_id}`(인프라 리전 `{region}`)에서 점검된 미비 중분류 항목({', '.join(risk_items) or '없음'})을 보완하기 위한 "
            "3단계 핵심 참조 아키텍처 블루프린트를 문어체 평서문(-다 체)으로 간결하게 작성하라. "
            "반드시 Private Service Connect, VPC Service Controls(Enforced), Cloud DLP 가명화, Cloud HSM CMEK, Bucket Lock(2년 WORM), 서킷 브레이커를 포함하라."
        )
        response = client.models.generate_content(model=model_name, contents=prompt)
        if response and getattr(response, "text", None):
            return response.text.strip(), f"Vertex AI Live Generation ({model_name} / {location})"
    except Exception:
        pass

    return deterministic_blueprint, f"Fallback Deterministic Blueprint ({model_name} / {location})"


def verify_reference_urls(
    urls: List[Tuple[str, str]], live_ping: bool
) -> List[Dict[str, str]]:
    """참조 규제 기관 및 기술 문서 URL의 문법 정합성과 HTTP 도달성을 검증한다."""
    verified: List[Dict[str, str]] = []

    def _probe(item: Tuple[str, str]) -> Dict[str, str]:
        label, url = item
        if not live_ping:
            is_valid = url.startswith("https://") and "." in url
            return {
                "label": label,
                "url": url,
                "http_code": "200 (Simulated)" if is_valid else "INVALID_FORMAT",
                "status": "VERIFIED" if is_valid else "BROKEN",
            }
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": "Mozilla/5.0 (compatible; GoogleCloud0to1Verifier/1.0)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                code = resp.getcode()
                return {
                    "label": label,
                    "url": url,
                    "http_code": str(code),
                    "status": "VERIFIED" if 200 <= code < 400 else "WARN",
                }
        except urllib.error.HTTPError as he:
            status = "VERIFIED" if he.code in (401, 403, 405) else "BROKEN"
            return {"label": label, "url": url, "http_code": str(he.code), "status": status}
        except Exception:
            return {"label": label, "url": url, "http_code": "TIMEOUT/ERR", "status": "WARN"}

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_probe, u): u for u in urls}
        for fut in as_completed(futures):
            verified.append(fut.result())

    verified.sort(key=lambda x: x["label"])
    return verified


def render_report_markdown(
    project_id: str,
    region: str,
    location: str,
    model_name: str,
    proposal_source: str,
    dry_run: bool,
    leaf_results: List[Dict[str, Any]],
    sub_results: List[Dict[str, Any]],
    matched_rejections: List[Dict[str, str]],
    blueprint_text: str,
    blueprint_source: str,
    url_checks: List[Dict[str, str]],
) -> str:
    """3계층(4대 대분류 / 15개 중분류 / 46개 소분류) 갭 분석 및 극복안이 포함된 report.md를 생성한다."""
    total_earned = sum(r["earned_score"] for r in leaf_results)
    total_max = sum(r["weight"] for r in leaf_results) or 1
    normalized_100 = int(round((total_earned / total_max) * 100))
    readiness_pct = round((total_earned / total_max) * 100, 1)

    leaf_pass_cnt = sum(1 for r in leaf_results if r["fulfilled"])
    leaf_gap_cnt = sum(1 for r in leaf_results if not r["fulfilled"])
    gap_weight_sum = sum(r["weight"] for r in leaf_results if not r["fulfilled"])

    sub_pass_cnt = sum(1 for r in sub_results if r["status"] == "PASS")
    sub_warn_cnt = sum(1 for r in sub_results if r["status"] == "WARN")
    sub_risk_cnt = sum(1 for r in sub_results if r["status"] == "REJECT_RISK")

    overall_grade = (
        "사전 보완 필수 (High Rejection Risk)"
        if sub_risk_cnt > 0 or normalized_100 < 80
        else ("조건부 적격 (Remediation Needed)" if leaf_gap_cnt > 0 else "신청 적격 (Ready for Filing)")
    )
    exec_mode = "Dry-Run (가상 시뮬레이션 모드)" if dry_run else "Live (실환경 및 신청서 정밀 진단 모드)"

    lines: List[str] = [
        "<!--",
        "Copyright 2026 Google LLC. All Rights Reserved.",
        "SPDX-License-Identifier: Apache-2.0",
        "",
        "NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.",
        "It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.",
        "All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.",
        "",
        "[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.",
        "프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.",
        "-->",
        "",
        "> [!IMPORTANT]",
        "> **구글 (Google LLC) 참조용 샘플 고지 사항**:",
        "> 본 프로젝트의 모든 소스 코드와 문서는 Google LLC의 소유이며, Apache-2.0 라이선스에 따라 오직 **참조용 샘플 (Sample / Reference Only)** 목적으로만 제공된다. 프로덕션 환경에 그대로 사용할 수 없으며, 사전 통지 없이 언제든 내용이 수정, 변경 또는 삭제될 수 있다.",
        "",
        "# 금융위원회 혁신 금융 서비스(생성형 AI 망 분리 샌드박스) 3계층(46개 소분류) 갭 분석 및 극복안 리포트",
        "",
        f"- **진단 대상 프로젝트**: `{project_id}`",
        f"- **금융 인프라 기준 리전**: `{region}` (대한민국 서울 리전 Data Boundary)",
        f"- **대조 신청서 출처**: `{proposal_source}`",
        f"- **생성형 AI 블루프린트 엔진**: `{blueprint_source}`",
        f"- **실행 모드**: `{exec_mode}`",
        f"- **종합 정량 심사 점수**: **{normalized_100} / 100점** (원점수 **{total_earned} / {total_max}점**, {readiness_pct}%) — **{overall_grade}**",
        f"- **3계층 판정 요약**: 4대 대분류 / 15개 중분류(적격 {sub_pass_cnt}, 보완 {sub_warn_cnt}, 위험 {sub_risk_cnt}) / **46개 소분류(충족 `PASS` {leaf_pass_cnt}건, 미비 `GAP` {leaf_gap_cnt}건 — 보완 시 +{gap_weight_sum}점 -> 100점 달성)**",
        "",
        "---",
        "",
        "## 1. [대분류 / 중분류] 4대 법정 심사 영역 및 15개 중분류 집계표",
        "",
        "| 대분류 영역 | 중분류 ID 및 명칭 | 중분류 판정 | 획득/만점 | 하위 소분류 충족 현황 및 검출된 갭(Gap) 요약 |",
        "| :--- | :--- | :---: | :---: | :--- |",
    ]

    for row in sub_results:
        lines.append(
            f"| {row['category_title']} | `{row['category_key']}:{row['sub_id']}` {row['sub_name']} "
            f"| **{row['status']}** | {row['earned_score']} / {row['max_score']} | {row['finding']} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 2. [소분류 전수 대조] 46개 세부 심사 요건(`category:sub_id:item_id`) vs 제출 신청서 1:1 갭(Gap) 진단표",
        "",
        "금융위원회 및 금융보안원의 46개 소분류 체크리스트 각각을 제출 신청서 본문과 1:1로 대조한 정밀 판정 결과다.",
        "",
        "| 소분류 ID | 중분류 명칭 | 소분류 요건명 및 법정 상세 기준 | 배점 | 판정 | 제출 신청서 1:1 대조 근거 및 미비점(Gap) 분석 |",
        "| :---: | :--- | :--- | :---: | :---: | :--- |",
    ])

    for leaf in leaf_results:
        badge = "**PASS**" if leaf["fulfilled"] else "**GAP (미비)**"
        lines.append(
            f"| `{leaf['item_id_full']}` | {leaf['sub_title']} | **{leaf['item_title']}**<br/>({leaf['item_desc']}) "
            f"| {leaf['earned_score']}/{leaf['weight']} | {badge} | {leaf['reason']} |"
        )

    lines.extend([
        "",
        "---",
        "",
        f"## 3. [소분류 갭 극복안] 미비 소분류({leaf_gap_cnt}건) 신청서 즉시 삽입용 모범 보완 문구 (Remedy Clauses)",
        "",
        f"제출된 신청서에서 누락되거나 부적격 판정을 받은 소분류 항목을 극복하기 위해, **신청서 해당 섹션에 즉시 복사하여 반영할 수 있는 모범 소명 문구**다. 아래 문구와 아키텍처 조치를 모두 반영하면 원점수 `+{gap_weight_sum}점`이 가산되어 **100점(만점)** 기준을 충족한다.",
        "",
        "| 미비 소분류 ID 및 요건명 | 감점 배점 | 제출서 결함 요약 (Gap) | 신청서 즉시 삽입용 모범 보완 문구 (Remedy Clause) |",
        "| :--- | :---: | :--- | :--- |",
    ])

    gap_leafs = [l for l in leaf_results if not l["fulfilled"]]
    if gap_leafs:
        for gl in gap_leafs:
            lines.append(
                f"| `{gl['item_id_full']}`<br/>**{gl['item_title']}** | -{gl['weight']}점 "
                f"| {gl['reason']} | `{gl['remedy_clause']}` |"
            )
    else:
        lines.append("| 전 소분류 충족 | 0점 | 검출된 소분류 갭 없음 | 현행 신청서 소명 문구 유지 |")

    lines.extend([
        "",
        "---",
        "",
        "## 4. 역대 금융위원회/금융보안원 반려 사례 교차 대조표",
        "",
        "식별된 소분류 갭(Gap)과 직접 연결되는 역대 주요 불승인 및 보완 요구 사례다.",
        "",
        "| 반려 사례 ID | 관련 중분류 항목 | 역대 주요 반려 사유 요약 | 참고 포털 및 기술 문서 |",
        "| :---: | :--- | :--- | :--- |",
    ])

    if matched_rejections:
        for rej in matched_rejections:
            lines.append(
                f"| `{rej['case_id']}` | `{rej['category']}:{rej['sub_id']}` {rej['title']} "
                f"| {rej['reason']} | 공식 안내 ( {rej['ref_url']} ) |"
            )
    else:
        lines.append("| `NONE` | 전 영역 충족 | 매칭되는 반려 위험 사례 없음 | 금융규제 샌드박스 ( https://sandbox.fsc.or.kr ) |")

    lines.extend([
        "",
        "---",
        "",
        f"## 5. 서울 리전(`{region}`) 금융 AI 망 분리 샌드박스 참조 블루프린트",
        "",
        blueprint_text,
        "",
        "---",
        "",
        "## 6. 신청서 인용 규제 기관 및 기술 레퍼런스 URL 도달성 검증 (Fact-Check)",
        "",
        "혁신 금융 서비스 신청서 내 깨진 링크(404 Dead Link)나 환각 인용을 방지하기 위한 공식 레퍼런스 검증 결과다.",
        "",
        "| 레퍼런스 명칭 | 검증 대상 URL | HTTP 응답 상태 | 정합성 판정 |",
        "| :--- | :--- | :---: | :---: |",
    ])

    for u in url_checks:
        lines.append(f"| {u['label']} | ( {u['url']} ) | `{u['http_code']}` | **{u['status']}** |")

    lines.extend([
        "",
        "---",
        "",
        "## 7. 물적 설비 및 논리적 망 분리 즉시 조치 명령어 (4대 필수 라벨 포함)",
        "",
        "금융보안원 보안성 심의에서 반려 빈도가 가장 높은 **CMEK 암호 키 직접 통제권(`technical_security:5:2~5:3`)**, **감사 로그 2년 WORM 불변 잠금(`technical_security:6:1`)**, **실증 한도 90% 경보 토픽(`regulatory_necessity:2:3`)**을 서울 리전(`asia-northeast3`)에 즉시 구성하는 표준 명령어다.",
        "",
        "```bash",
        "# 1. 서울 리전(asia-northeast3) Cloud HSM 기반 고객 관리 암호화 키(CMEK) 생성 및 4대 표준 라벨 부여",
        f"gcloud kms keyrings create fsc-sandbox-keyring \\\n  --location={region} \\\n  --project={project_id}",
        "",
        f"gcloud kms keys create fsc-ai-cmek-key \\\n  --keyring=fsc-sandbox-keyring \\\n  --location={region} \\\n  --purpose=encryption \\\n  --protection-level=hsm \\\n  --rotation-period=90d \\\n  --next-rotation-time=$(date -u -d '+90 days' +%Y-%m-%dT%H:%M:%SZ) \\\n  --labels={MANDATORY_LABELS} \\\n  --project={project_id}",
        "",
        "# 2. 감사 로그 및 프롬프트 이력 2년(730일) 불변 보존(WORM Bucket Lock) 버킷 생성",
        f"gcloud storage buckets create gs://{project_id}-fsc-audit-worm \\\n  --location={region} \\\n  --uniform-bucket-level-access \\\n  --public-access-prevention \\\n  --retention-period=730d \\\n  --default-encryption-key=projects/{project_id}/locations/{region}/keyRings/fsc-sandbox-keyring/cryptoKeys/fsc-ai-cmek-key \\\n  --labels={MANDATORY_LABELS} \\\n  --project={project_id}",
        "",
        "# 3. 실증 한도(Cap) 90% 도달 및 서킷 브레이커 발동 알림용 Pub/Sub 토픽 생성",
        f"gcloud pubsub topics create fsc-sandbox-circuit-breaker-alerts \\\n  --labels={MANDATORY_LABELS} \\\n  --project={project_id}",
        "```",
        "",
    ])
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    """표준 3대 플래그(--dry-run, --config, --project) 및 소분류 갭 시뮬레이션 인자 파서를 생성한다."""
    parser = argparse.ArgumentParser(
        description="금융위원회 혁신 금융 서비스(생성형 AI 망 분리 샌드박스) 3계층(46개 소분류) 사전 심사, 제출서 갭 분석 및 극복안 도출 도구"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="GCP 과금 및 실시간 API 호출 없이 내장 신청서 초안을 기반으로 46개 소분류 갭 및 극복안을 즉시 진단한다.",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="대화형 환경 설정 마법사를 실행하여 .env 설정 파일을 생성한다.",
    )
    parser.add_argument(
        "-p",
        "--project",
        type=str,
        default=None,
        help="진단 대상 GCP 프로젝트 ID (미지정 시 환경 변수 또는 gcloud 활성 설정 자동 감지)",
    )
    parser.add_argument(
        "-r",
        "--region",
        type=str,
        default=None,
        help=f"금융 인프라 배포 기준 리전 (기본값: {DEFAULT_REGION})",
    )
    parser.add_argument(
        "--location",
        type=str,
        default=None,
        help=f"Gemini API 호출 리전 (기본값: {DEFAULT_LOCATION})",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["all", "consumer_benefit", "regulatory_necessity", "service_innovativeness", "technical_security"],
        default=None,
        help="집중 점검할 혁신 금융 서비스 대분류 심사 영역 (기본값: all)",
    )
    parser.add_argument(
        "--proposal",
        type=str,
        default=None,
        help="사전 점검할 혁신 금융 서비스 신청서 초안 파일 경로 (.md, .txt, .pdf 지원)",
    )
    parser.add_argument(
        "--simulate-item",
        type=str,
        default=None,
        help="자가 보완 시뮬레이션을 수행할 소분류 ID (예: consumer_benefit:3:3 또는 technical_security:6:1)",
    )
    parser.add_argument(
        "--remedy-text",
        type=str,
        default=None,
        help="--simulate-item 대상 소분류에 대해 적합성 및 가점을 테스트할 보완 작성 문구",
    )
    parser.add_argument(
        "--verify-urls",
        action="store_true",
        help="참조 규제 기관 및 기술 문서 URL에 대해 실시간 HTTP HEAD 도달성 검사를 수행한다.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.config:
        return run_config_wizard()

    project_id = resolve_project_id(args.project, args.dry_run)
    region = args.region or os.getenv("REGION") or DEFAULT_REGION
    location = args.location or os.getenv("GOOGLE_CLOUD_LOCATION") or DEFAULT_LOCATION
    model_name = os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    category = args.category or os.getenv("SANDBOX_CATEGORY") or "all"
    proposal_path_str = args.proposal or os.getenv("PROPOSAL_PATH") or ""

    if args.simulate_item:
        if not args.remedy_text:
            print("[오류] --simulate-item 사용 시 --remedy-text 인자로 보완 문구를 함께 입력해야 한다.")
            return 1
        return simulate_remedy_clause(
            item_id_full=args.simulate_item,
            remedy_text=args.remedy_text,
            project_id=project_id,
            location=location,
            model_name=model_name,
            dry_run=args.dry_run,
        )

    proposal_text, proposal_source = load_proposal_text(proposal_path_str)

    mode_str = "DRY-RUN (가상 시뮬레이션)" if args.dry_run else "LIVE (실환경 및 신청서 정밀 점검)"
    print("=" * 88)
    print("[금융위원회 혁신 금융 서비스(생성형 AI 망 분리 샌드박스) 3계층(46개 소분류) 갭 분석 및 극복안 진단]")
    print("=" * 88)
    print(f" - 대상 프로젝트 ID : {project_id}")
    print(f" - 금융 인프라 리전 : {region} (대한민국 서울 리전)")
    print(f" - Gemini 모델/리전 : {model_name} / {location}")
    print(f" - 대조 신청서 출처 : {proposal_source}")
    print(f" - 심사 영역 필터   : {category}")
    print(f" - 실행 모드        : {mode_str}")
    print("-" * 88)

    print("[1/4] 3계층 심사 기준(4대 대분류 / 15개 중분류 / 46개 소분류) vs 제출서 1:1 갭 분석 중...")
    leaf_results, sub_results, matched_rejections = evaluate_sandbox_readiness(
        project_id=project_id,
        region=region,
        category_filter=category,
        proposal_text=proposal_text,
        dry_run=args.dry_run,
    )

    for row in sub_results:
        badge = f"[{row['status']}]"
        print(
            f"  {badge:<14} {row['category_key']}:{row['sub_id']} {row['sub_name']} "
            f"({row['earned_score']}/{row['max_score']}점) -> {row['finding']}"
        )

    gap_leafs = [l for l in leaf_results if not l["fulfilled"]]
    print(f"\n[2/4] 검출된 소분류 갭(Gap) {len(gap_leafs)}건에 대한 핀포인트 극복안 및 역대 반려 사례 매칭 중...")
    for gl in gap_leafs[:8]:
        print(f"  - [GAP -{gl['weight']}점] {gl['item_id_full']} ({gl['item_title']}): {gl['reason']}")
    if len(gap_leafs) > 8:
        print(f"  ... 외 {len(gap_leafs) - 8}건의 소분류 갭 및 모범 보완 문구(Remedy Clause)가 report.md에 전수 수록됨")

    print(f"\n[3/4] 서울 리전({region}) 망 분리 대체 통제 참조 블루프린트 생성 중...")
    blueprint_text, blueprint_source = generate_reference_blueprint(
        project_id=project_id,
        region=region,
        location=location,
        model_name=model_name,
        sub_results=sub_results,
        dry_run=args.dry_run,
    )

    print("[4/4] 신청서 인용 규제 기관 및 기술 문서 URL 도달성(Fact-Check) 검증 중...")
    url_checks = verify_reference_urls(
        CANONICAL_REFERENCE_URLS, live_ping=(args.verify_urls and not args.dry_run)
    )

    report_md = render_report_markdown(
        project_id=project_id,
        region=region,
        location=location,
        model_name=model_name,
        proposal_source=proposal_source,
        dry_run=args.dry_run,
        leaf_results=leaf_results,
        sub_results=sub_results,
        matched_rejections=matched_rejections,
        blueprint_text=blueprint_text,
        blueprint_source=blueprint_source,
        url_checks=url_checks,
    )

    report_path = Path(__file__).resolve().parent / "report.md"
    report_path.write_text(report_md, encoding="utf-8")

    total_earned = sum(r["earned_score"] for r in leaf_results)
    total_max = sum(r["weight"] for r in leaf_results) or 1
    normalized_100 = int(round((total_earned / total_max) * 100))
    leaf_pass_cnt = sum(1 for r in leaf_results if r["fulfilled"])
    leaf_gap_cnt = len(gap_leafs)

    print("-" * 88)
    print(
        f"[진단 요약] 100점 환산: {normalized_100}/100점 (원점수 {total_earned}/{total_max}점) | "
        f"46개 소분류 중 충족(PASS): {leaf_pass_cnt}건, 미비(GAP): {leaf_gap_cnt}건"
    )
    print(f"[산출물] 46개 소분류 1:1 갭 진단표 및 모범 보완 문구 리포트: {report_path}")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    sys.exit(main())
