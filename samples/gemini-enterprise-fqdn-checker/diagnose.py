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
        "purpose": "Agent Platform Search 웹 콘솔 및 엔드포인트",
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


def build_markdown_report(results: list[dict], is_dry_run: bool) -> str:
  mode_str = "모의 실행 (Dry-run)" if is_dry_run else "운영 환경 진단 (Production)"
  lines = [
      "# 진단 및 분석 리포트: gemini-enterprise-fqdn-checker",
      "",
      f"- **생성 모드**: {mode_str}",
      "- **대상 프로젝트**: `sample-project-id`",
      "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
      "",
      "---",
      "",
      "## 1. 진단 실행 콘솔 출력 결과",
      "",
      "```text",
      "Gemini Enterprise 필수 FQDN 사내망 연결성 진단 시작",
  ]
  if is_dry_run:
    lines.append("--> 가상 실행 모드 (--dry-run) 활성화: 모의 방화벽 차단 시나리오를 분석한다.")
  else:
    lines.append("--> 병렬 네트워크 프로브 실행 완료.")

  lines.extend([
      "",
      "=" * 105,
      f"{'카테고리':<16} {'FQDN':<42} {'DNS':<6} {'TLS/443':<8} {'지연(ms)':<10} {'결과':<10}",
      "-" * 105,
  ])
  for r in results:
    dns_str = "OK" if r["dns_ok"] else "FAIL"
    tcp_str = "OK" if r["tls_ok"] else "FAIL"
    res_str = "[정상]" if r["status"] == "PASS" else "[차단]"
    lines.append(f"{r['category']:<16} {r['fqdn']:<42} {dns_str:<6} {tcp_str:<8} {r['latency_ms']:<10} {res_str:<10}")
  lines.append("=" * 105)

  failures = [r for r in results if r["status"] != "PASS"]
  critical_fails = [r for r in failures if r["critical"]]
  warning_fails = [r for r in failures if not r["critical"]]
  total_count = len(results)
  pass_count = total_count - len(failures)

  lines.append(f"\n[진단 요약] 총 {total_count}개 FQDN 중 {pass_count}개 정상, {len(failures)}개 차단 또는 실패")

  if failures:
    lines.append("\n[발견된 방화벽 차단 항목 및 처방]")
    for f in critical_fails:
      lines.append(f"\n* [심각-서비스불가] {f['fqdn']} (카테고리: {f['category']}, 용도: {f['purpose']})")
      lines.append(f"  - 증상: {f['error']}")
      if "discoveryengine.clients6.google.com" in f["fqdn"]:
        lines.append("  - 처방: 본 FQDN은 Gemini Enterprise App 웹 UI 렌더링, Deep Research 및 동적 에셋 처리에 필수적이다.")
        lines.append("         사내 방화벽 및 프록시 Allowlist에 TCP 443 아웃바운드 규칙을 즉시 추가한다.")
      else:
        lines.append("  - 처방: 사내 방화벽 아웃바운드 규칙(TCP 443) 또는 프록시 허용 목록에 해당 FQDN을 등록한다.")

    for f in warning_fails:
      lines.append(f"\n* [주의-일부기능제한] {f['fqdn']} (카테고리: {f['category']}, 용도: {f['purpose']})")
      lines.append(f"  - 증상: {f['error']}")
      lines.append("  - 처방: 폰트, 이미지 등 부가 자산 허용을 위해 방화벽 규칙에 FQDN을 추가 등록한다.")
  else:
    lines.append("\n모든 Gemini Enterprise 필수 FQDN과의 443 통신 및 DNS 해석이 정상이다.")

  lines.extend([
      "```",
      "",
      "---",
      "",
      "## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)",
      "",
      "실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.",
      "실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:",
      "",
      "```bash",
      "python diagnose.py",
      "```",
      "",
      "---",
      "",
      "## 3. 사내 거버넌스 4대 필수 표준 라벨링",
      "",
      "방화벽 규칙 및 관련 클라우드 인프라 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:",
      "- `managed-by`: `google-cloud-0-to-1`",
      "- `scenario`: `gemini-enterprise-fqdn-checker`",
      "- `env`: `sample` (또는 `poc`)",
      "- `created-by`: `customer-engineer`",
      "",
      "---",
      "",
      "## 4. 콘솔 링크 조치 가이드",
      "",
      "- **Cloud NGFW 방화벽 정책 콘솔**: ( https://console.cloud.google.com/net-security/firewall-manager/firewall-policies )",
      "- **VPC 네트워크 콘솔**: ( https://console.cloud.google.com/networking/networks/list )",
      "- **Private Service Connect 콘솔**: ( https://console.cloud.google.com/net-services/psc/list )",
      "",
      "---",
      "",
      "## 5. 자원 정리 안내 (Teardown)",
      "",
      "본 도구는 클라우드 자원을 생성하지 않는 네트워크 소켓 진단 유틸리티다. 진단 과정에서 발생하는 추가 과금이나 자원 잔류가 없다.",
      "",
  ])
  return "\n".join(lines)


def save_markdown_report(content: str, filename: str = "report.md") -> None:
  current_dir = os.path.dirname(os.path.abspath(__file__))
  report_path = os.path.join(current_dir, filename)
  with open(report_path, "w", encoding="utf-8") as f:
    f.write(content)



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
  parser.add_argument(
      "-p",
      "--project",
      default=os.getenv("PROJECT_ID", ""),
      help="대상 Google Cloud 프로젝트 ID",
  )
  parser.add_argument("--dry-run", action="store_true", help="실제 통신 없이 모의 차단 시나리오 진단")
  parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
  parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
  parser.add_argument(
      "--category",
      choices=["Core API", "Auth & Session", "Static Assets", "User Content"],
      help="특정 카테고리만 한정 진단",
  )
  args = parser.parse_args()
  if getattr(args, "config", False):
      run_config_mode("gemini-enterprise-fqdn-checker")
      return

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

  report_content = build_markdown_report(results, is_dry_run=args.dry_run)
  save_markdown_report(report_content)
  print("\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")
  print("\n[안내] 사내 거버넌스 및 자원 추적을 위한 4대 필수 표준 라벨:")
  print("  - managed-by: google-cloud-0-to-1")
  print("  - scenario: gemini-enterprise-fqdn-checker")
  print("  - env: sample")
  print("  - created-by: customer-engineer\n")


if __name__ == "__main__":
  main()
