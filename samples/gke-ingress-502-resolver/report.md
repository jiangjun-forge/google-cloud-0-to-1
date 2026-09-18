# 진단 및 분석 리포트: gke-ingress-502-resolver

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
[GKE Ingress 502 Resolver] 4단계 체인 역추적 프로세스를 시작한다.
[*] 대상 프로젝트: sample-project-id
[*] 대상 위치(Location): asia-northeast3
[*] 대상 네임스페이스: default
[1/4] 가상 실행 모드 활성화: 502 발생 모의 인프라 데이터를 로드한다...
[2/4] 모의 방화벽, 헬스 체크 경로, NEG 게이트, 타임아웃 체인을 검증했다.
[3/4] 종합 원인 역추적 및 맞춤형 YAML/명령어를 도출한다...
[4/4] 진단 리포트를 생성한다...
================================================================================
 GKE Ingress 및 Gateway 502 Bad Gateway 원인 체인 역추적 리포트
================================================================================
[!] 안내: 본 결과는 실제 쿠버네티스 호출이 아닌 내장 모의 인프라 데이터(Dry-Run) 기준이다.

[1] 점검 대상 리소스 개요:
  - GKE 클러스터: gke-prod-asia-northeast3 (위치: asia-northeast3)
  - Ingress 리소스: frontend-external-ingress (네임스페이스: production)
  - 로드 밸런서 공인 IP: 34.149.88.204
  - 대상 백엔드 서비스: frontend-web-svc

[2] 4단계 체인 심층 진단 결과: [CRITICAL]

  [1] [CRITICAL] GCP 헬스 체크 프로브 대역 방화벽 규칙 누락 (FIREWALL_PROBE_BLOCKED)
      - 상세 원인: 구글 클라우드 로드 밸런서 헬스 체크 프로브 대역(35.191.0.0/16, 130.211.0.0/22)에서 GKE 노드/파드로 들어오는 인그레스 트래픽이 차단되어 모든 백엔드가 Unhealthy로 판정됨.

  [2] [CRITICAL] 헬스 체크 요청 경로 불일치 (HEALTH_CHECK_PATH_MISMATCH)
      - 상세 원인: 파드 Readiness Probe 경로('/healthz')와 GCP 로드 밸런서 헬스 체크 경로('/')가 일치하지 않음. 기본 루트('/') 경로가 HTTP 200 이외의 응답(404 Not Found 또는 302 Redirect)을 반환하여 파드가 정상 기동 중임에도 로드 밸런서 헬스 체크가 실패함.

  [3] [WARNING] Pod Readiness Gate 미주입 (NEG_READINESS_GATE_MISSING)
      - 상세 원인: 파드 배포 시 'cloud.google.com/neg-ready' Readiness Gate가 선언되지 않음. 신규 파드 롤아웃 시 컨테이너가 뜨자마자 트래픽이 유입되어 NEG 엔드포인트 등록 완료 전 502 에러 발생 위험.

  [4] [WARNING] 백엔드 Keepalive 타임아웃 역전 장애 (KEEPALIVE_TIMEOUT_INVERSION)
      - 상세 원인: 백엔드 웹 애플리케이션의 Keepalive 타임아웃(5초)이 로드 밸런서 백엔드 서비스 타임아웃(30초)보다 짧거나 같음. 유휴 커넥션을 백엔드가 먼저 TCP FIN/RST로 끊어버려 클라이언트 요청 도중 간헐적 502 발생.

[3] 단계별 즉시 복구 가이드 및 맞춤형 YAML:

  1. GCP 헬스 체크 허용 인그레스 방화벽 규칙 즉시 배포:
     # gcloud 방화벽 생성 명령:
     gcloud compute firewall-rules create allow-gcp-health-checks \
       --network=default \
       --action=ALLOW \
       --direction=INGRESS \
       --source-ranges=35.191.0.0/16,130.211.0.0/22 \
       --rules=tcp:80,tcp:443,tcp:8080

  2. BackendConfig 생성 및 Service 바인딩 (경로 일치 및 타임아웃 보정):
     # custom-backend-config.yaml 파일 적용:
     ---
     apiVersion: cloud.google.com/v1
     kind: BackendConfig
     metadata:
       name: frontend-backend-config
       namespace: production
     spec:
       timeoutSec: 30  # 백엔드 서버 Keepalive 타임아웃보다 작게 유지
       healthCheck:
         type: HTTP
         requestPath: /healthz  # Pod Readiness Probe와 100% 일치
         port: 8080
     ---
     # Service 애노테이션 추가:
     kubectl annotate service frontend-web-svc -n production \
       cloud.google.com/backend-config='{"default": "frontend-backend-config"}' --overwrite

  3. 백엔드 웹 프레임워크 Keepalive 타임아웃 상향 조정:
     - 로드 밸런서 백엔드 타임아웃(30초)보다 최소 5초 이상 크게 설정한다.
     * Node.js / Express 예시:
       server.keepAliveTimeout = (30 + 5) * 1000; // 35000ms
       server.headersTimeout = (30 + 10) * 1000;   // 40000ms
     * Nginx 예시 (`nginx.conf`):
       keepalive_timeout 35s;

  4. 파드 스펙에 Readiness Gate 주입 (롤아웃 502 방지):
     Deployment YAML의 `spec.template.spec`에 아래 항목을 추가한다:
     readinessGates:
       - conditionType: None # GKE 클러스터 버전 1.16+에서 Standalone NEG 활성화 시 자동 주입 권장
     Service 애노테이션 확인: cloud.google.com/neg: '{"ingress": true}'
================================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
