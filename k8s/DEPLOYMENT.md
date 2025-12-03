# Wadeulwadeul Heroes Backend - Kubernetes Deployment Guide

## 📋 목차

- [개요](#개요)
- [사전 요구사항](#사전-요구사항)
- [Jenkins를 통한 배포 (권장)](#jenkins를-통한-배포-권장)
- [수동 배포](#수동-배포)
- [배포 확인](#배포-확인)
- [롤백](#롤백)
- [트러블슈팅](#트러블슈팅)

---

## 개요

이 프로젝트는 AWS EKS에서 실행되는 FastAPI 백엔드 애플리케이션입니다.

**배포 아키텍처:**
- **Container Registry**: AWS ECR
- **Orchestration**: AWS EKS (Kubernetes)
- **CI/CD**: Jenkins (Parameterized Build)
- **Database**: PostgreSQL (Kubernetes StatefulSet)
- **Ingress**: NGINX Ingress Controller

---

## 사전 요구사항

### 1. 필수 도구 설치

```bash
# AWS CLI
aws --version

# kubectl
kubectl version --client

# Docker (이미지 빌드용)
docker --version
```

### 2. AWS 자격증명 설정

```bash
# AWS 자격증명 확인
aws sts get-caller-identity

# EKS 클러스터 kubeconfig 업데이트
aws eks update-kubeconfig --region ap-northeast-2 --name goormthon-cluster
```

### 3. Kubernetes 네임스페이스 확인

```bash
# 네임스페이스 존재 확인
kubectl get namespace goormthon-5

# 없으면 생성
kubectl create namespace goormthon-5

# 네임스페이스 고정
kubectl config set-context --current --namespace=goormthon-5
```

---

## Jenkins를 통한 배포 (권장)

### 📌 Jenkins 파라미터 설명

Jenkins에서 **"Build with Parameters"**를 클릭하면 다음 파라미터를 설정할 수 있습니다:

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `IMAGE_TAG` | String | `latest` | 배포할 Docker 이미지 태그 (예: `v1.0.0`, `dev-123`) |
| `NAMESPACE` | Choice | `goormthon-5` | 배포할 Kubernetes 네임스페이스 |
| `REPLICAS` | Choice | `2` | Pod 레플리카 수 (1~5) |
| `UPDATE_CONFIG` | Boolean | `false` | ConfigMap과 Secret 업데이트 여부 |
| `ENABLE_ROLLBACK` | Boolean | `true` | 배포 실패 시 자동 롤백 활성화 |
| `DEPLOY_MESSAGE` | Text | - | 배포 메시지 (선택사항) |

### 🚀 배포 단계

#### 1. Jenkins 접속

```
http://your-jenkins-url/job/wadeulwadeul-heroes-backend/
```

#### 2. "Build with Parameters" 클릭

#### 3. 파라미터 설정 예시

**개발 환경 배포:**
```
IMAGE_TAG: dev-latest
NAMESPACE: goormthon-5
REPLICAS: 2
UPDATE_CONFIG: false
ENABLE_ROLLBACK: true
DEPLOY_MESSAGE: "개발 환경 테스트 배포"
```

**프로덕션 배포:**
```
IMAGE_TAG: v1.0.0
NAMESPACE: goormthon-5
REPLICAS: 3
UPDATE_CONFIG: false
ENABLE_ROLLBACK: true
DEPLOY_MESSAGE: "프로덕션 v1.0.0 배포"
```

#### 4. "Build" 클릭

#### 5. 배포 진행 상황 모니터링

Jenkins 콘솔 로그에서 다음 단계를 확인할 수 있습니다:

1. **Preparation**: 배포 파라미터 확인
2. **Configure AWS & Kubectl**: AWS 및 kubectl 설정
3. **Verify Image**: ECR에서 이미지 존재 확인
4. **Update ConfigMap & Secret**: (선택) 설정 업데이트
5. **Deploy to Kubernetes**: Kubernetes 배포
6. **Wait for Rollout**: 배포 완료 대기
7. **Verify Deployment**: 배포 상태 확인
8. **Health Check**: 애플리케이션 헬스 체크

---

## 수동 배포

Jenkins를 사용하지 않고 수동으로 배포할 수도 있습니다.

### 1. Docker 이미지 빌드 & 푸시

```bash
# 이미지 빌드 및 ECR 푸시
./scripts/build-and-push.sh v1.0.0

# 또는 latest 태그로
./scripts/build-and-push.sh
```

### 2. ConfigMap & Secret 배포 (최초 1회)

```bash
# ConfigMap 생성
kubectl apply -f k8s/backend/config/configmap.yaml

# Secret 생성
kubectl apply -f k8s/backend/config/secret.yaml
```

### 3. Backend 배포

```bash
# 기본 배포 (latest 태그, 2 replicas)
./scripts/deploy-backend.sh

# 특정 태그와 replicas로 배포
./scripts/deploy-backend.sh --tag v1.0.0 --replicas 3 --namespace goormthon-5

# 또는 환경변수로
IMAGE_TAG=v1.0.0 REPLICAS=3 ./scripts/deploy-backend.sh
```

### 4. Ingress 배포 (최초 1회)

```bash
kubectl apply -f k8s/backend/ingress.yaml
```

---

## 배포 확인

### 1. 스크립트를 통한 확인

```bash
./scripts/check-status.sh
```

### 2. 수동 확인

```bash
# Deployment 확인
kubectl get deployment backend-deployment

# Pod 확인
kubectl get pods -l app=backend

# Service 확인
kubectl get svc backend-service

# Ingress 확인
kubectl get ingress backend-ingress

# Pod 로그 확인
kubectl logs -l app=backend --tail=50

# 실시간 로그 확인
kubectl logs -l app=backend -f
```

### 3. 헬스 체크

```bash
# Port-forward를 통한 로컬 테스트
kubectl port-forward svc/backend-service 8080:80

# 다른 터미널에서
curl http://localhost:8080/health/ping
curl http://localhost:8080/
```

### 4. Ingress를 통한 외부 접근

```bash
# Ingress URL 확인
kubectl get ingress backend-ingress

# 헬스 체크
curl http://goormthon-5.goorm.training/api/health/ping

# API 테스트
curl http://goormthon-5.goorm.training/api/
```

---

## 롤백

### Jenkins를 통한 롤백

배포 실패 시 `ENABLE_ROLLBACK=true`로 설정되어 있으면 자동으로 롤백됩니다.

### 수동 롤백

#### 1. 이전 버전으로 롤백

```bash
./scripts/rollback-backend.sh

# 또는 kubectl 직접 사용
kubectl rollout undo deployment/backend-deployment
```

#### 2. 특정 버전으로 롤백

```bash
# 배포 히스토리 확인
kubectl rollout history deployment/backend-deployment

# 특정 revision으로 롤백
./scripts/rollback-backend.sh 3

# 또는 kubectl 직접 사용
kubectl rollout undo deployment/backend-deployment --to-revision=3
```

#### 3. 롤백 상태 확인

```bash
kubectl rollout status deployment/backend-deployment
kubectl get pods -l app=backend
```

---

## 트러블슈팅

### 1. Pod가 시작되지 않음

```bash
# Pod 상태 확인
kubectl get pods -l app=backend

# Pod 상세 정보 확인
kubectl describe pod <pod-name>

# Pod 로그 확인
kubectl logs <pod-name>

# 이전 컨테이너 로그 확인 (재시작된 경우)
kubectl logs <pod-name> --previous
```

**일반적인 원인:**
- 이미지 Pull 실패: ECR 권한 확인
- ConfigMap/Secret 없음: `kubectl get configmap,secret` 확인
- 리소스 부족: 노드 리소스 확인
- Health Check 실패: 애플리케이션 로그 확인

### 2. Service에 연결할 수 없음

```bash
# Service 확인
kubectl get svc backend-service

# Endpoints 확인
kubectl get endpoints backend-service

# Service 상세 정보
kubectl describe svc backend-service
```

### 3. Ingress 연결 실패

```bash
# Ingress 확인
kubectl get ingress backend-ingress

# Ingress 상세 정보
kubectl describe ingress backend-ingress

# NGINX Ingress Controller 로그
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
```

### 4. ConfigMap/Secret 업데이트가 반영되지 않음

ConfigMap이나 Secret을 업데이트한 후에는 Pod를 재시작해야 합니다:

```bash
kubectl rollout restart deployment/backend-deployment
```

### 5. 이미지 Pull 실패

```bash
# ECR 로그인 확인
aws ecr get-login-password --region ap-northeast-2 | \
    docker login --username AWS --password-stdin \
    837126493345.dkr.ecr.ap-northeast-2.amazonaws.com

# ECR에 이미지가 있는지 확인
aws ecr describe-images \
    --repository-name goormthon-5 \
    --region ap-northeast-2
```

### 6. 데이터베이스 연결 실패

```bash
# PostgreSQL Pod 확인
kubectl get pods -l app=postgres

# 연결 테스트
kubectl run -it --rm debug --image=postgres:16 --restart=Never -- \
    psql -h postgres.goormthon-5.svc.cluster.local -U postgres -d wadeulwadeul_db
```

---

## 유용한 명령어 모음

### 배포 관련

```bash
# 현재 이미지 확인
kubectl get deployment backend-deployment -o jsonpath='{.spec.template.spec.containers[0].image}'

# Replicas 수 변경
kubectl scale deployment/backend-deployment --replicas=3

# 이미지만 업데이트
kubectl set image deployment/backend-deployment \
    backend=837126493345.dkr.ecr.ap-northeast-2.amazonaws.com/goormthon-5:v1.0.0

# 환경변수 확인
kubectl exec -it <pod-name> -- env | grep -E 'APP_|DB_'
```

### 모니터링

```bash
# 리소스 사용량 확인
kubectl top nodes
kubectl top pods -l app=backend

# 이벤트 실시간 모니터링
kubectl get events -w

# Pod 상태 실시간 모니터링
kubectl get pods -l app=backend -w
```

### 디버깅

```bash
# Pod 안에서 명령 실행
kubectl exec -it <pod-name> -- /bin/sh

# 디버그 Pod 생성
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- sh

# 네트워크 테스트
kubectl run -it --rm netdebug --image=nicolaka/netshoot --restart=Never -- bash
```

---

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. **로그 확인**: `./scripts/check-status.sh`
2. **이벤트 확인**: `kubectl get events --sort-by='.lastTimestamp'`
3. **히스토리 확인**: `kubectl rollout history deployment/backend-deployment`

추가 지원이 필요하면 DevOps 팀에 문의하세요.
