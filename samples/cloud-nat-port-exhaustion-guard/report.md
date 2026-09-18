# 진단 및 분석 리포트: cloud-nat-port-exhaustion-guard

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
[Cloud NAT Port Exhaustion Guard] 진단 프로세스를 시작한다.
[*] 대상 프로젝트: sample-project-id
[*] 대상 리전: asia-northeast3
[1/3] 가상 실행 모드 활성화: 모의 인프라 데이터를 로드한다...
[2/3] 모의 포트 할당 및 드롭 지표 분석을 완료했다.
[3/3] 종합 평가 리포트를 생성한다...
================================================================================
 Cloud NAT 포트 고갈 및 패킷 드롭 종합 진단 리포트
================================================================================
[!] 안내: 본 결과는 실제 GCP 호출이 아닌 내장 모의 인프라 데이터(Dry-Run) 기준이다.

[1] 대상 게이트웨이 사양:
  - Cloud Router: cr-prod-asia-northeast3 (리전: asia-northeast3)
  - Cloud NAT: nat-gw-prod-main
  - IP 할당 모드: AUTO_ONLY (보유 공인 IP 수: 2개)
  - Dynamic Port Allocation (DPA): 활성화 (Enabled)
  - VM/노드당 최소 할당 포트 (minPortsPerVm): 64개
  - VM/노드당 최대 확장 포트 (maxPortsPerVm): 1024개

[2] 모니터링 텔레메트리 실측 결과 (최근 분석 기간):
  - 자원 고갈 패킷 드롭 수 (OUT_OF_RESOURCES): 1,420건
  - VM/노드 피크 포트 사용량: 1012개
  - 고위험 VM 및 파드 노드 수: 2대

[3] 종합 진단 결과: [CRITICAL]
  * 원인 분석: Cloud NAT 게이트웨이에서 1,420건의 아웃바운드 패킷 드롭(OUT_OF_RESOURCES)이 실제 발생함

[4] 포트 임계치 초과 인스턴스 상세:
  인스턴스 식별자                         영역(Zone)           피크 사용      할당 포트      사용률      드롭 수
  ----------------------------------------------------------------------------------------
  gke-prod-core-pool-a1b2          asia-northeast3-a  1012       1024       98.8%    860건
  gke-prod-core-pool-c3d4          asia-northeast3-b  980        1024       95.7%    560건

[5] 긴급 조치 가이드 및 아키텍처 처방:
  1. Cloud NAT 최소 할당 포트(min-ports-per-vm) 즉시 상향:
     - 트래픽 버스트 시 DPA가 추가 포트를 프로비저닝하는 지연 시간(최대 240초) 동안의 드롭을 원천 예방한다.
     # gcloud 수정 명령어:
     gcloud compute routers nats update nat-gw-prod-main \
       --router=cr-prod-asia-northeast3 \
       --region=asia-northeast3 \
       --enable-dynamic-port-allocation \
       --min-ports-per-vm=256 \
       --max-ports-per-vm=2048

  2. 클라이언트 OS 커널 TCP SYN 재시도 횟수 조정 (GKE 노드 / GCE VM):
     - DPA가 새 포트 블록을 바인딩하는 동안 클라이언트의 일시적 SYN 드롭을 견딜 수 있도록 재시도 횟수를 상향한다.
     # Linux 호스트 또는 DaemonSet 실행 명령:
     sudo sysctl -w net.ipv4.tcp_syn_retries=6
     # 영구 적용 (/etc/sysctl.d/99-gcp-nat.conf):
     echo 'net.ipv4.tcp_syn_retries = 6' | sudo tee -a /etc/sysctl.d/99-gcp-nat.conf && sudo sysctl -p

  3. TCP 타임아웃 단축을 통한 포트 재사용성 개선:
     - 비정상 종료된 연결이 포트를 불필요하게 점유하지 않도록 Transitory Idle Timeout 단축을 검토한다.
     # tcp-transitory-idle-timeout-sec 권장값: 15초 (현재: 30초)
================================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
