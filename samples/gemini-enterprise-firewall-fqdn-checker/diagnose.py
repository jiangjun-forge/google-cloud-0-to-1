#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini Enterprise App Firewall FQDN Connectivity Diagnostic Tool.

와일드카드 도메인 허용이 불가한 엔터프라이즈 사내망 환경에서 Gemini Enterprise App 정상 구동에
필수적인 Exact FQDN 목록의 DNS 해석 및 TCP 443 아웃바운드 연결성을 일괄 진단한다.
"""

import argparse
import concurrent.futures
import json
import os
import socket
import ssl
import sys
import time

TARGET_FQDNS = [
    # 1. Gemini Enterprise & Discovery Engine 코어 백엔드 API
    {
        "category": "Core API",
        "fqdn": "discoveryengine.googleapis.com",
        "port": 443,
        "critical": True,
        "purpose": "Discovery Engine 코어 API 통신",
    },
    {
        "category": "Core API",
        "fqdn": "global-discoveryengine.googleapis.com",
        "port": 443,
        "critical": True,
        "purpose": "글로벌 멀티 리전 엔드포인트",
    },
    {
        "category": "Core API",
        "fqdn": "us-discoveryengine.googleapis.com",
        "port": 443,
        "critical": False,
        "purpose": "US 리전 전용 API 엔드포인트",
    },
    {
        "category": "Core API",
        "fqdn": "eu-discoveryengine.googleapis.com",
        "port": 443,
        "critical": False,
        "purpose": "EU 리전 전용 API 엔드포인트",
    },
    {
        "category": "Core API",
        "fqdn": "content-discoveryengine.googleapis.com",
        "port": 443,
        "critical": True,
        "purpose": "문서 콘텐츠 및 청크 인덱싱",
    },
    {
        "category": "Core API",
        "fqdn": "vertexaisearch.cloud.google.com",
        "port": 443,
        "critical": True,
        "purpose": "Vertex AI Search 웹 콘솔 및 엔드포인트",
    },
    {
        "category": "Core API",
        "fqdn": "discoveryengine.clients6.google.com",
        "port": 443,
        "critical": True,
        "purpose": "UI 렌더링, Deep Research 및 동적 에셋 처리 (필수)",
    },
    # 2. 계정 인증 및 세션 관리
    {
        "category": "Auth & Session",
        "fqdn": "accounts.google.com",
        "port": 443,
        "critical": True,
        "purpose": "Google Workspace / Cloud Identity 사용자 로그인",
    },
    {
        "category": "Auth & Session",
        "fqdn": "apis.google.com",
        "port": 443,
        "critical": True,
        "purpose": "클라이언트 라이브러리 및 OAuth 자격 증명 교환",
    },
    {
        "category": "Auth & Session",
        "fqdn": "auth.cloud.google.com",
        "port": 443,
        "critical": True,
        "purpose": "클라우드 세션 인가 및 토큰 재발급",
    },
    {
        "category": "Auth & Session",
        "fqdn": "console.cloud.google.com",
        "port": 443,
        "critical": False,
        "purpose": "Google Cloud 웹 콘솔 세션 관리",
    },
    {
        "category": "Auth & Session",
        "fqdn": "reauth.cloud.google.com",
        "port": 443,
        "critical": False,
        "purpose": "민감 작업 시 사용자 재인증",
    },
    # 3. UI 정적 자산 및 폰트
    {
        "category": "Static Assets",
        "fqdn": "www.gstatic.com",
        "port": 443,
        "critical": True,
        "purpose": "UI 자바스크립트 및 CSS 정적 자산 로딩",
    },
    {
        "category": "Static Assets",
        "fqdn": "ssl.gstatic.com",
        "port": 443,
        "critical": True,
        "purpose": "보안 웹 컴포넌트 정적 라이브러리",
    },
    {
        "category": "Static Assets",
        "fqdn": "fonts.gstatic.com",
        "port": 443,
        "critical": False,
        "purpose": "웹 폰트 바이너리 로딩",
    },
    {
        "category": "Static Assets",
        "fqdn": "fonts.googleapis.com",
        "port": 443,
        "critical": False,
        "purpose": "웹 폰트 스타일시트 로딩",
    },
    # 4. 이미지 및 프로필 데이터 레이어
    {
        "category": "User Content",
        "fqdn": "lh3.googleusercontent.com",
        "port": 443,
        "critical": False,
        "purpose": "사용자 프로필 및 멀티모달 이미지 서빙",
    },
    {
        "category": "User Content",
        "fqdn": "lh4.googleusercontent.com",
        "port": 443,
        "critical": False,
        "purpose": "사용자 프로필 및 멀티모달 이미지 서빙",
    },
    {
        "category": "User Content",
        "fqdn": "lh5.googleusercontent.com",
        "port": 443,
        "critical": False,
        "purpose": "사용자 프로필 및 멀티모달 이미지 서빙",
    },
    {
        "category": "User Content",
        "fqdn": "lh6.googleusercontent.com",
        "port": 443,
        "critical": False,
        "purpose": "사용자 프로필 및 멀티모달 이미지 서빙",
    },
]


def probe_fqdn(item: dict, timeout: float = 2.0) -> dict:
  """단일 FQDN에 대해 DNS 해석 및 TCP 443 TLS 핸드셰이크를 테스트한다."""
  fqdn = item["fqdn"]
  port = item["port"]
  category = item["category"]
  critical = item["critical"]
  purpose = item["purpose"]

  res = {
      "fqdn": fqdn,
      "port": port,
      "category": category,
      "critical": critical,
      "purpose": purpose,
      "dns_ok": False,
      "tcp_ok": False,
      "tls_ok": False,
      "ip_addresses": [],
      "latency_ms": 0.0,
      "error": None,
      "status": "PASS",
  }

  t0 = time.perf_counter()
  try:
    # 1. DNS 해석
    addr_info = socket.getaddrinfo(fqdn, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    ips = list({entry[4][0] for entry in addr_info})
    res["ip_addresses"] = ips
    res["dns_ok"] = True
  except socket.gaierror as e:
    res["error"] = f"DNS 해석 실패: {e}"
    res["status"] = "FAIL_DNS"
    res["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return res

  # 2. TCP 연결 및 TLS 핸드셰이크
  try:
    ctx = ssl.create_default_context()
    with socket.create_connection((fqdn, port), timeout=timeout) as sock:
      res["tcp_ok"] = True
      with ctx.wrap_socket(sock, server_hostname=fqdn) as ssock:
        res["tls_ok"] = True
        res["status"] = "PASS"
  except (socket.timeout, TimeoutError):
    res["error"] = "TCP 연결 타임아웃 (방화벽 아웃바운드 443 차단 의심)"
    res["status"] = "FAIL_TIMEOUT"
  except ConnectionRefusedError:
    res["error"] = "TCP 연결 거부 (대상 포트 거부 또는 프록시 차단)"
    res["status"] = "FAIL_REFUSED"
  except ssl.SSLError as e:
    res["error"] = f"TLS 핸드셰이크 실패 (SSL 가로채기/인스펙션 이슈): {e}"
    res["status"] = "FAIL_TLS"
  except Exception as e:
    res["error"] = f"연결 실패: {e}"
    res["status"] = "FAIL_OTHER"

  res["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
  return res


def get_mock_probe_results() -> list[dict]:
  """가상 실행(--dry-run)을 위한 기업 방화벽 차단 시나리오 모의 결과를 반환한다."""
  results = []
  for item in TARGET_FQDNS:
    fqdn = item["fqdn"]
    if fqdn == "discoveryengine.clients6.google.com":
      # UI 렌더링 핵심 엔드포인트 차단 시나리오 모의
      results.append({
          "fqdn": fqdn,
          "port": item["port"],
          "category": item["category"],
          "critical": item["critical"],
          "purpose": item["purpose"],
          "dns_ok": True,
          "tcp_ok": False,
          "tls_ok": False,
          "ip_addresses": ["142.250.196.110"],
          "latency_ms": 2005.12,
          "error": "TCP 연결 타임아웃 (방화벽 아웃바운드 443 차단 의심)",
          "status": "FAIL_TIMEOUT",
      })
    elif fqdn == "ssl.gstatic.com":
      # DNS 해석 실패 시나리오 모의
      results.append({
          "fqdn": fqdn,
          "port": item["port"],
          "category": item["category"],
          "critical": item["critical"],
          "purpose": item["purpose"],
          "dns_ok": False,
          "tcp_ok": False,
          "tls_ok": False,
          "ip_addresses": [],
          "latency_ms": 15.42,
          "error": "DNS 해석 실패: Name or service not known",
          "status": "FAIL_DNS",
      })
    else:
      results.append({
          "fqdn": fqdn,
          "port": item["port"],
          "category": item["category"],
          "critical": item["critical"],
          "purpose": item["purpose"],
          "dns_ok": True,
          "tcp_ok": True,
          "tls_ok": True,
          "ip_addresses": ["142.250.196.106"],
          "latency_ms": 32.5,
          "error": None,
          "status": "PASS",
      })
  return results


def print_table(results: list[dict]):
  """점검 결과를 카테고리별로 정돈하여 콘솔에 출력한다."""
  print("\n" + "=" * 105)
  print(f"{'카테고리':<16} {'FQDN':<42} {'DNS':<6} {'TLS/443':<8} {'지연(ms)':<10} {'결과':<10}")
  print("-" * 105)

  for r in results:
    dns_str = "OK" if r["dns_ok"] else "FAIL"
    tcp_str = "OK" if r["tls_ok"] else "FAIL"
    res_str = "[정상]" if r["status"] == "PASS" else "[차단]"
    print(f"{r['category']:<16} {r['fqdn']:<42} {dns_str:<6} {tcp_str:<8} {r['latency_ms']:<10} {res_str:<10}")
  print("=" * 105)

  failures = [r for r in results if r["status"] != "PASS"]
  critical_fails = [r for r in failures if r["critical"]]
  warning_fails = [r for r in failures if not r["critical"]]

  total_count = len(results)
  pass_count = total_count - len(failures)
  print(f"\n[진단 요약] 총 {total_count}개 FQDN 중 {pass_count}개 정상, {len(failures)}개 차단 또는 실패")

  if failures:
    print("\n[발견된 방화벽 차단 항목 및 처방]")
    for f in critical_fails:
      print(f"\n* [심각-서비스불가] {f['fqdn']} (카테고리: {f['category']}, 용도: {f['purpose']})")
      print(f"  - 증상: {f['error']}")
      if "discoveryengine.clients6.google.com" in f["fqdn"]:
        print("  - 처방: 본 FQDN은 Gemini Enterprise App 웹 UI 렌더링, Deep Research 및 동적 에셋 처리에 필수적이다.")
        print("         사내 방화벽 및 프록시 Allowlist에 TCP 443 아웃바운드 규칙을 즉시 추가한다.")
      else:
        print("  - 처방: 사내 방화벽 아웃바운드 규칙(TCP 443) 또는 프록시 허용 목록에 해당 FQDN을 등록한다.")

    for f in warning_fails:
      print(f"\n* [주의-일부기능제한] {f['fqdn']} (카테고리: {f['category']}, 용도: {f['purpose']})")
      print(f"  - 증상: {f['error']}")
      print("  - 처방: 폰트, 이미지 등 부가 자산 허용을 위해 방화벽 규칙에 FQDN을 추가 등록한다.")
  else:
    print("\n모든 Gemini Enterprise 필수 FQDN과의 443 통신 및 DNS 해석이 정상이다.")


def main():
  parser = argparse.ArgumentParser(
      description="Gemini Enterprise 사내망 FQDN 방화벽 연결성 진단기"
  )
  timeout_env = os.getenv("PROBE_TIMEOUT_SECONDS")
  parser.add_argument(
      "--timeout",
      type=float,
      default=float(timeout_env) if timeout_env else 2.0,
      help="개별 FQDN 연결 타임아웃 (초 단위, 기본값: 2.0초)",
  )
  parser.add_argument("--dry-run", action="store_true", help="실제 통신 없이 모의 차단 시나리오 진단")
  parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
  parser.add_argument(
      "--category",
      choices=["Core API", "Auth & Session", "Static Assets", "User Content"],
      help="특정 카테고리만 한정 진단",
  )
  args = parser.parse_args()

  print("Gemini Enterprise 필수 FQDN 사내망 연결성 진단 시작")
  if args.dry_run:
    print("--> 가상 실행 모드 (--dry-run) 활성화: 모의 방화벽 차단 시나리오를 분석한다.")
    results = get_mock_probe_results()
  else:
    targets = TARGET_FQDNS
    if args.category:
      targets = [t for t in TARGET_FQDNS if t["category"] == args.category]

    print(f"--> 병렬 네트워크 프로브 실행 중... (대상: {len(targets)}개 도메인, 타임아웃: {args.timeout}초)")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
      future_map = {executor.submit(probe_fqdn, t, args.timeout): t for t in targets}
      results = [f.result() for f in concurrent.futures.as_completed(future_map)]
      results.sort(key=lambda x: (x["category"], x["fqdn"]))

  if args.json:
    print(json.dumps(results, indent=2, ensure_ascii=False))
  else:
    print_table(results)


if __name__ == "__main__":
  main()
