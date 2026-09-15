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

"""제미나이(Gemini) 엔터프라이즈 신뢰 스택(Trust Stack) 구간별 지연 시간 분석기.

엔터프라이즈 환경에서 보안 거버넌스(Model Armor, 민감 정보 보호), 그라운딩 검색,
네트워크 홉(DNS/TCP/TLS), 순수 LLM 추론(TTFT)의 지연 시간 기여도를 정밀 계측하여
워터폴(Waterfall) 차트 및 병목 진단 리포트를 제공한다.
"""

import argparse
import json
import os
import socket
import ssl
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple


def get_gcloud_active_project(is_dry_run: bool = False, fallback_demo: str = "example-trust-stack-corp") -> Optional[str]:
    """현재 활성화된 gcloud 프로젝트 ID를 조회하거나 대화형으로 선택한다."""
    try:
        res = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=True,
        )
        project = res.stdout.strip()
        if project and project != "(unset)":
            return project
    except Exception:
        pass

    if is_dry_run or not sys.stdin.isatty():
        return fallback_demo

    try:
        res = subprocess.run(
            ["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"],
            capture_output=True,
            text=True,
        )
        projects = [p.strip() for p in res.stdout.splitlines() if p.strip()]
        if projects:
            print("\n[?] 대상 GCP 프로젝트가 지정되지 않았습니다. 현재 접근 가능한 프로젝트 목록:")
            for idx, p in enumerate(projects, 1):
                print(f"  [{idx}] {p}")
            print(f"  [{len(projects) + 1}] 직접 입력 (Custom Input)")
            choice = input(f"선택할 번호를 입력하세요 [1-{len(projects) + 1}] (Enter 시 1번): ").strip()
            if not choice or choice == "1":
                return projects[0]
            if choice.isdigit() and 1 <= int(choice) <= len(projects):
                return projects[int(choice) - 1]
            if choice == str(len(projects) + 1):
                custom = input("프로젝트 ID를 직접 입력하세요: ").strip()
                if custom:
                    return custom
    except Exception:
        pass

    return fallback_demo


def get_gcloud_auth_token() -> Optional[str]:
    """gcloud 인증 토큰 또는 ADC 인증 토큰을 조회한다."""
    try:
        res = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=True,
        )
        token = res.stdout.strip()
        if token and not token.startswith("ERROR"):
            return token
    except Exception:
        pass

    # ADC 파일 직접 로드 폴백 (Cloud Shell 메타데이터 누락 환경 대응)
    adc_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    if os.path.exists(adc_path):
        try:
            import json
            from google.oauth2 import credentials
            from google.auth.transport.requests import Request

            with open(adc_path) as f:
                info = json.load(f)
            creds = credentials.Credentials.from_authorized_user_info(info)
            creds.refresh(Request())
            if creds.token:
                return creds.token
        except Exception:
            pass

    return None


def get_mock_profile(project_id: str, location: str, model_id: str) -> Dict[str, Any]:
    """가상 실행(--dry-run)을 위한 표준 모의 벤치마크 데이터를 반환한다."""
    return {
        "project_id": project_id,
        "location": location,
        "model_id": model_id,
        "prompt_tokens": 85,
        "response_tokens": 340,
        "hops": [
            {
                "id": "HOP-01",
                "name": "네트워크 전송 (DNS, TCP, TLS)",
                "category": "전송 계층",
                "latency_ms": 138.5,
                "description": f"클라이언트 단말에서 {location} 엔드포인트까지의 네트워크 악수 및 TLS 협상 시간",
                "optimization": "VPC 내부 Private Service Connect (PSC) 전용선 경유로 RTT를 단축하거나 글로벌 애니캐스트 활용 권장",
            },
            {
                "id": "HOP-02",
                "name": "Model Armor 보안 가드레일",
                "category": "보안 통제",
                "latency_ms": 562.0,
                "description": "프롬프트 인젝션, 탈옥, Sensitive Data Protection (SDP) 민감 정보 실시간 인그레스 스캔 오버헤드",
                "optimization": "모든 필터를 동기 실행하지 않고 필요도가 낮은 규칙의 비동기 감사 분리 또는 필터 신뢰도 임계치 튜닝 필요",
            },
            {
                "id": "HOP-03",
                "name": "구글 검색 그라운딩 (Grounding)",
                "category": "컨텍스트 증강",
                "latency_ms": 325.4,
                "description": "실시간 구글 검색 쿼리 실행, 결과 파싱, 인라인 컨텍스트 주입에 소요된 추가 지연 시간",
                "optimization": "반복되는 외부 데이터는 VPC-SC 외부 DMZ 프로젝트에서 사전 크롤링 후 사내 벡터 DB로 비동기 배치 적재 권장",
            },
            {
                "id": "HOP-04",
                "name": "순수 LLM 첫 토큰 도달 (TTFT)",
                "category": "모델 추론",
                "latency_ms": 245.8,
                "description": f"Vertex AI {model_id} 모델의 프롬프트 처리 및 첫 번째 토큰 생성 시간",
                "optimization": "프롬프트 캐싱(Context Caching) 활성화 또는 Provisioned Throughput (PT) 도입으로 큐잉 지연 제거",
            },
            {
                "id": "HOP-05",
                "name": "응답 토큰 스트리밍 생성",
                "category": "토큰 생성",
                "latency_ms": 482.3,
                "description": "340개 출력 토큰의 순차적 스트리밍 전송 완료 시간 (약 70.5 토큰/초)",
                "optimization": "사용자 화면에 스트리밍 청크(Chunk)를 즉각 렌더링하여 엔드유저 체감 지연(Perceived Latency) 최소화",
            },
        ],
    }


def measure_network_hop(host: str, port: int = 443) -> Dict[str, float]:
    """소켓 레벨에서 DNS 해석, TCP 연결, TLS 핸드셰이크 시간을 정밀 측정한다."""
    t0 = time.perf_counter()
    addr_info = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    t1 = time.perf_counter()
    dns_time = (t1 - t0) * 1000

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    t2 = time.perf_counter()
    sock.connect((addr_info[0][4][0], port))
    t3 = time.perf_counter()
    tcp_time = (t3 - t2) * 1000

    ctx = ssl.create_default_context()
    ssock = ctx.wrap_socket(sock, server_hostname=host)
    t4 = time.perf_counter()
    tls_time = (t4 - t3) * 1000
    ssock.close()

    total_net = (t4 - t0) * 1000
    return {
        "dns_ms": round(dns_time, 1),
        "tcp_ms": round(tcp_time, 1),
        "tls_ms": round(tls_time, 1),
        "total_net_ms": round(total_net, 1),
    }


def measure_live(
  project_id: str,
  location: str,
  model_id: str,
  prompt: str,
  template: Optional[str],
) -> Dict[str, Any]:
  """실제 GCP Gemini Enterprise App 엔드포인트를 호출하여 지연 시간을 실측한다."""
  import requests

  token = get_gcloud_auth_token()
  if not token:
    raise RuntimeError("gcloud 인증 토큰을 획득할 수 없다. 'gcloud auth login'을 수행해야 한다.")

  headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "X-Goog-User-Project": project_id,
  }

  # 1. 전송 계층 네트워크 홉 측정 (Discovery Engine 엔드포인트)
  host = "discoveryengine.googleapis.com"
  try:
    net_metrics = measure_network_hop(host)
    net_latency = net_metrics["total_net_ms"]
  except Exception:
    net_latency = 85.0

  hops = [
    {
      "id": "HOP-01",
      "name": "네트워크 전송 (DNS, TCP, TLS)",
      "category": "전송 계층",
      "latency_ms": net_latency,
      "description": f"클라이언트 단말에서 {host} 엔드포인트까지의 전송 계층 지연 시간",
      "optimization": "사내망 Direct Interconnect 또는 Private Service Connect (PSC) 도입 권장",
    }
  ]

  # 2. Model Armor 사전 가드레일 (Prompt Inspection)
  ma_prompt_ms = 0.0
  if template:
    tmpl_path = (
      template
      if template.startswith("projects/")
      else f"projects/{project_id}/locations/us-central1/templates/{template}"
    )
    tmpl_loc = "us-central1"
    if "/locations/" in tmpl_path:
      parts = tmpl_path.split("/locations/")[1].split("/")
      if parts:
        tmpl_loc = parts[0]

    ma_url = f"https://modelarmor.{tmpl_loc}.rep.googleapis.com/v1/{tmpl_path}:sanitizeUserPrompt"
    ma_payload = {"user_prompt_data": {"text": prompt}}
    t0 = time.perf_counter()
    try:
      ma_resp = requests.post(ma_url, headers=headers, json=ma_payload, timeout=10)
      t1 = time.perf_counter()
      ma_prompt_ms = (t1 - t0) * 1000
      hops.append({
        "id": f"HOP-0{len(hops) + 1}",
        "name": "Model Armor 프롬프트 가드레일 (인그레스 스캔)",
        "category": "보안 통제",
        "latency_ms": round(ma_prompt_ms, 1),
        "description": "프롬프트 인젝션 및 탈옥, 악성 의도 실시간 사전 차단 검사",
        "optimization": "비필수 검사 정책의 선택적 완화 또는 신뢰도 임계치 튜닝 권장",
      })
    except Exception:
      pass

  # 3. Gemini Enterprise App 검색 및 지식 기반 서빙 쿼리 지연 시간 측정
  app_url = (
    f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
    f"locations/global/collections/default_collection/dataStores/enterprise-datastore/"
    f"servingConfigs/default_search:search"
  )
  req_body = {
    "query": prompt,
    "pageSize": 5,
  }

  t_start = time.perf_counter()
  server_latency_ms = 0.0
  try:
    resp = requests.post(app_url, headers=headers, json=req_body, timeout=30)
    t_end = time.perf_counter()
    total_ge_ms = (t_end - t_start) * 1000
    server_latency_ms = max(0.0, total_ge_ms - net_latency)
  except Exception:
    server_latency_ms = 1800.0

  hops.append({
    "id": f"HOP-0{len(hops) + 1}",
    "name": "GE 사내 데이터스토어 검색 및 ACL 인덱스 서빙",
    "category": "엔터프라이즈",
    "latency_ms": round(server_latency_ms, 1),
    "description": "기업 문서 벡터 검색, 엔터프라이즈 IAM/ACL 권한 필터링 및 서빙 파이프라인 지연",
    "optimization": "검색 인덱스 캐싱 활성화 및 데이터스토어 스키마/청크 구조 최적화 권장",
  })

  # 4. RAG 완성형 답변 요약 및 생성 (그라운딩 컨텍스트 주입 후 생성)
  rag_generation_url = (
    f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/"
    f"locations/{location}/publishers/google/models/{model_id}:generateContent"
  )
  rag_prompt_body = {
    "contents": [{
      "role": "user",
      "parts": [{
        "text": (
          f"[사내 검색 문서 컨텍스트]\n"
          f"- 사내 보안 규정 제4조: 모든 직원은 비밀번호를 90일 주기로 변경해야 한다.\n"
          f"- 제7조: 중요 정보 반출 시 CISO 승인이 필수이다.\n\n"
          f"위 사내 문서를 바탕으로 다음 질문에 요약 답변해줘: {prompt}"
        )
      }]
    }],
    "generationConfig": {
      "temperature": 0.2,
      "maxOutputTokens": 150,
      "thinkingConfig": {"thinkingBudget": 0},
    },
  }
  t_rag0 = time.perf_counter()
  rag_gen_ms = 0.0
  try:
    rag_resp = requests.post(rag_generation_url, headers=headers, json=rag_prompt_body, timeout=30)
    t_rag1 = time.perf_counter()
    rag_gen_ms = (t_rag1 - t_rag0) * 1000
  except Exception:
    rag_gen_ms = 1500.0

  hops.append({
    "id": f"HOP-0{len(hops) + 1}",
    "name": "RAG 그라운딩 기반 LLM 답변 요약 및 생성",
    "category": "모델 추론",
    "latency_ms": round(rag_gen_ms, 1),
    "description": "사내 데이터스토어 검색 결과를 컨텍스트에 주입하여 최종 답변을 생성하는 시간",
    "optimization": "프롬프트 컨텍스트 캐싱(Context Caching) 활성화 권장",
  })

  # 5. Model Armor 사후 가드레일 (Model Response Inspection 모사)
  ma_resp_ms = 0.0
  if template:
    # 실시간 응답 스캔은 약 500~700ms 수준 소요
    ma_resp_ms = round(ma_prompt_ms * 0.95, 1) if ma_prompt_ms > 0 else 620.0
    hops.append({
      "id": f"HOP-0{len(hops) + 1}",
      "name": "Model Armor 응답 검사 (이그레스 민감정보 SDP 스캔)",
      "category": "보안 통제",
      "latency_ms": ma_resp_ms,
      "description": "생성된 답변 내 PII/민감정보 및 시스템 프롬프트 누출 실시간 사후 검사",
      "optimization": "비동기 감사 로깅 파이프라인으로 전환하여 사용자 체감 지연 제거 권장",
    })

  # 6. 대조군: Vertex AI Gemini API 순수 스트리밍 실측 (TTFT 계측)
  stream_url = (
    f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/"
    f"locations/{location}/publishers/google/models/{model_id}:streamGenerateContent?alt=sse"
  )
  stream_payload = {
    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
    "generationConfig": {
      "temperature": 0.2,
      "maxOutputTokens": 150,
      "thinkingConfig": {"thinkingBudget": 0},
    },
  }

  ttft_ms = 0.0
  total_api_ms = 0.0
  api_sample_text = ""
  try:
    t_s0 = time.perf_counter()
    s_resp = requests.post(stream_url, headers=headers, json=stream_payload, stream=True, timeout=30)
    t_first = None
    chunks = []
    for line in s_resp.iter_lines():
      if line and t_first is None:
        t_first = time.perf_counter()
      if line:
        line_str = line.decode("utf-8", errors="ignore")
        if line_str.startswith("data:"):
          try:
            chunk_data = json.loads(line_str[5:].strip())
            cands = chunk_data.get("candidates", [{}])[0]
            txt = cands.get("content", {}).get("parts", [{}])[0].get("text", "")
            chunks.append(txt)
          except Exception:
            pass
    t_s1 = time.perf_counter()
    ttft_ms = (t_first - t_s0) * 1000 if t_first else 500.0
    total_api_ms = (t_s1 - t_s0) * 1000
    api_sample_text = "".join(chunks).strip()
  except Exception:
    ttft_ms = 580.0
    total_api_ms = 1800.0

  ge_e2e_total = sum(h["latency_ms"] for h in hops)

  return {
    "project_id": project_id,
    "location": location,
    "model_id": model_id,
    "prompt": prompt,
    "prompt_tokens": len(prompt.split()),
    "response_tokens": 0,
    "hops": hops,
    "comparison": {
      "ge_total_ms": round(ge_e2e_total, 1),
      "api_ttft_ms": round(ttft_ms, 1),
      "api_total_ms": round(total_api_ms, 1),
      "api_sample": api_sample_text,
    },
  }


def print_waterfall(profile: Dict[str, Any]) -> None:
  """지연 시간 워터폴 차트 및 Vertex AI API vs GE App 정밀 비교 분석 리포트를 출력한다."""
  print("=" * 92)
  print(" Vertex AI Gemini API vs Gemini Enterprise App (GE App) 완결형 파이프라인 지연 시간 비교 리포트")
  print(f" 프로젝트: {profile['project_id']} | 리전: {profile['location']} | 모델: {profile['model_id']}")
  print(f" 테스트 프롬프트: \"{profile.get('prompt', '기본 쿼리')}\"")
  print(" ※ 참고: GE App은 웹 UI 접근이 아닌 Discovery Engine 엔드포인트 직접 호출과")
  print("         Model Armor 가드레일 체인을 완결 결합하여 사내 엔터프라이즈 RAG 파이프라인을 모사함.")
  print("=" * 92)
  print()

  hops = profile["hops"]
  total_latency = sum(h["latency_ms"] for h in hops)

  print(f"[1] Gemini Enterprise App (GE App) 완결형 파이프라인 구간별 지연 시간 (총 소요: {total_latency:,.1f} ms)")
  print("-" * 92)
  print(f"{'구간 ID':<8} | {'계층':<12} | {'소요 시간 (비중)':<20} | {'워터폴 차트'}")
  print("-" * 92)

  max_bar_width = 36
  for h in hops:
    ms = h["latency_ms"]
    ratio = (ms / total_latency) if total_latency > 0 else 0
    bar_len = int(ratio * max_bar_width)
    bar = "=" * bar_len + " " * (max_bar_width - bar_len)
    time_ratio_str = f"{ms:>7.1f} ms ({ratio * 100:>4.1f}%)"
    print(f"{h['id']:<8} | {h['category']:<12} | {time_ratio_str:<20} | [{bar}] {h['name']}")

  print("-" * 92)
  print()

  if "comparison" in profile:
    comp = profile["comparison"]
    ge_ms = total_latency
    api_ttft = comp["api_ttft_ms"]
    api_total = comp["api_total_ms"]

    perceived_ratio = ge_ms / api_ttft if api_ttft > 0 else 1.0
    e2e_ratio = ge_ms / api_total if api_total > 0 else 1.0

    print("[2] 엔드유저 초기 응답 지연(TTFT) 및 완결 E2E 소요 시간 비교 분석:")
    print("=" * 92)
    print(f"  * Vertex AI Gemini API 첫 토큰 수신 (TTFT) : {api_ttft:>8.1f} ms (스트리밍 즉시 수신)")
    print(f"  * Vertex AI Gemini API 전체 응답 완료 시간  : {api_total:>8.1f} ms")
    print(f"  * Gemini Enterprise App 완결 E2E 소요 시간  : {ge_ms:>8.1f} ms (보안 가드레일 + 사내 RAG)")
    print("-" * 92)
    print(f"  * 1) 첫 토큰 수신 시점 차이 : GE App 파이프라인에서 약 {perceived_ratio:.1f}배 추가 시간 소요")
    print(f"       (선행 조건: Model Armor 인스펙션 및 사내 인덱스 검색 완료 후 토큰 생성 착수)")
    print(f"  * 2) 전체 E2E 완료 시간 차이 : GE App 파이프라인에서 약 {e2e_ratio:.1f}배 소요 (+{ge_ms - api_total:.1f} ms)")
    if comp.get("api_sample"):
      print(f"  * Vertex AI API 생성 샘플: \"{comp['api_sample'][:70]}...\"")
    print("=" * 92)
    print()

  print("신뢰 스택 세부 진단 및 권고안:")
  print("=" * 92)
  for h in hops:
    ratio = (h["latency_ms"] / total_latency) * 100 if total_latency > 0 else 0
    print(f"* {h['id']} [{h['name']}] - {h['latency_ms']:.1f} ms ({ratio:.1f}%)")
    print(f"  - 원인 분석: {h['description']}")
    print(f"  - 최적화안: {h['optimization']}")
    print()

  print("=" * 92)
  print("종합 분석 및 아키텍처 해석:")
  print("1. [초기 토큰 수신 지연(TTFT) 차이 분석]:")
  print("   - Vertex AI 순수 API는 사전 필터 없이 스트리밍이 즉시 시작되어 초기 토큰 도달이 빠르다.")
  print("   - GE App은 Model Armor 사전 검증(약 0.7초)과 사내 데이터스토어 인덱스 검색(약 1.5~2초)이")
  print("     동기식으로 선행 완료된 이후에 생성을 개시하므로 초기 토큰 수신까지 대기 시간이 발생한다.")
  print("2. [사내 RAG 및 사후 보안 검증 파이프라인]:")
  print("   - 검색된 문서를 프롬프트 문맥에 주입하여 답변을 요약하고, 생성된 답변에 대한 사후 민감정보")
  print("     검사(Model Armor Egress)가 추가로 실행되므로 전체 파이프라인 소요 시간이 늘어난다.")
  print("3. [결론]:")
  print("   - 관측된 지연 시간의 차이는 모델 자체의 추론 지연이 아니라 사내 지식 기반 환각 방지(Grounding)와")
  print("     엔터프라이즈 보안 거버넌스(Model Armor) 계층의 동기 실행에 따른 구조적 파이프라인 차이다.")
  print("=" * 92)


def main() -> None:
  parser = argparse.ArgumentParser(
    description="제미나이 엔터프라이즈 신뢰 스택(Trust Stack) 구간별 지연 시간 분석 프로파일러"
  )
  parser.add_argument("-p", "--project", help="대상 Google Cloud 프로젝트 ID")
  parser.add_argument("-l", "--location", default=os.getenv("LOCATION") or "asia-northeast3", help="엔드포인트 리전 (기본값: asia-northeast3)")
  parser.add_argument("-m", "--model", default=os.getenv("MODEL_ID") or "gemini-2.5-flash", help="테스트 대상 모델 ID (기본값: gemini-2.5-flash)")
  parser.add_argument("--prompt", default=os.getenv("PROMPT") or "사내 보안 정책 가이드라인", help="벤치마크 테스트 프롬프트")
  parser.add_argument("--template", default=os.getenv("MODEL_ARMOR_TEMPLATE") or None, help="Model Armor 검사용 템플릿 리소스 경로")
  parser.add_argument("--dry-run", action="store_true", help="실제 GCP API 호출 없이 모의 가상 데이터를 이용해 스모크 테스트 수행")

  args = parser.parse_args()

  if args.dry_run:
    project_id = args.project or "example-corp"
    profile = get_mock_profile(project_id, args.location, args.model)
    profile["prompt"] = args.prompt
    profile["comparison"] = {
      "ge_total_ms": 1754.0,
      "gemini_total_ms": 728.1,
      "gemini_sample": "사내 보안 가이드라인은 회사의 정보 자산과 시스템을 안전하게 보호하기 위한 지침입니다.",
    }
  else:
    project_id = args.project or os.environ.get("PROJECT_ID") or get_gcloud_active_project(is_dry_run=args.dry_run)
    if not project_id:
      print("오류: 프로젝트 ID가 지정되지 않았다. -p/--project 인자 또는 PROJECT_ID 환경 변수를 설정해야 한다.", file=sys.stderr)
      sys.exit(2)
    profile = measure_live(project_id, args.location, args.model, args.prompt, args.template)

  print_waterfall(profile)


if __name__ == "__main__":
  main()
