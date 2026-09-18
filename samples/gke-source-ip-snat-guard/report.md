# 진단 및 분석 리포트: gke-source-ip-snat-guard

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
GKE 소스 IP(Client IP) 보존 및 SNAT 상태 진단 시작 (프로젝트: sample-project-id, 클러스터: prod-core-cluster)
--> 가상 실행 모드 (--dry-run) 활성화: 사전 시뮬레이션 클러스터 및 인그레스 데이터를 분석한다.

=========================================================================================================
네임스페이스/서비스                         LB 유형                    extPolicy    노드/파드          심각도       
---------------------------------------------------------------------------------------------------------
ingress-gateway/kong-proxy-internal Internal Passthrough NLB Cluster      3노드/2파드        CRITICAL  
ingress-nginx/nginx-ingress-external External Passthrough NLB Local        3노드/4파드        WARNING   
billing/payment-api-service        Internal Passthrough NLB Local        3노드/6파드        HEALTHY   
=========================================================================================================

[발견된 주요 네트워크 결함 및 권고 조치]

* [CRITICAL] ingress-gateway/kong-proxy-internal (IP: 10.130.46.71, extPolicy: Cluster)
  - 원인: externalTrafficPolicy가 'Cluster'로 설정되어 파드가 없는 노드로 인입된 트래픽이 2-Hop 전달 시 kube-proxy에 의해 노드 IP로 SNAT되어 원본 Client IP가 손실됨
  - 원인: internalTrafficPolicy가 'Cluster'로 설정되어 내부 클러스터 통신 경로에서 동일 노드 내 로컬 전달 최적화가 적용되지 않음
  - 원인: Ingress Controller의 X-Forwarded-For 프록시 헤더 신뢰 설정(use-forwarded-headers)이 비활성화됨
  - 처방: Service 'kong-proxy-internal'의 externalTrafficPolicy를 'Local'로 변경하여 1-Hop 직접 전달을 강제한다: kubectl patch svc kong-proxy-internal -n ingress-gateway -p '{"spec":{"externalTrafficPolicy":"Local"}}'
  - 처방: 클러스터 내부 통신 지연을 최소화하려면 spec.internalTrafficPolicy를 'Local'로 지정을 검토한다.
  - 처방: Ingress ConfigMap에서 use-forwarded-headers: 'true' 및 compute-full-forwarded-for: 'true'를 설정하고 신뢰 프록시 대역을 등록한다.

* [WARNING] ingress-nginx/nginx-ingress-external (IP: 34.64.120.15, extPolicy: Local)
  - 원인: 총 3개 노드 중 1개 노드에 대상 파드가 배치되지 않아 해당 노드로 들어온 NLB 헬스체크가 실패하거나 트래픽 유입 시 드롭될 위험이 존재함
  - 원인: 노드별 파드 수 편차(최대 3개, 최소 1개)로 인해 로드 밸런서가 노드 단위로 트래픽을 균등 분산할 때 파드별 심각한 부하 불균형(Hotspotting) 발생
  - 처방: DaemonSet으로 배포하거나, Deployment의 TopologySpreadConstraints를 적용하여 모든 노드에 파드를 균등 배치한다.
  - 처방: GKE Weighted Load Balancing 애너테이션('networking.gke.io/weighted-load-balancing': 'true')을 활성화하여 노드별 파드 수에 비례하여 트래픽이 가중 분산되도록 구성한다.
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
