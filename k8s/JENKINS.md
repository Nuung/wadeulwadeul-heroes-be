# Jenkins Setup Guide

## Jenkins 프로젝트 설정

### 1. 새 Jenkins Job 생성

1. Jenkins 대시보드에서 **"New Item"** 클릭
2. 프로젝트 이름 입력: `wadeulwadeul-heroes-backend`
3. **"Pipeline"** 선택
4. **"OK"** 클릭

### 2. Pipeline 설정

#### General

- **Description**: `Wadeulwadeul Heroes Backend - Kubernetes Deployment`
- **✓ This project is parameterized** 체크 (Jenkinsfile에서 자동 처리됨)

#### Build Triggers (선택사항)

수동 배포를 원하므로 체크하지 않습니다. 자동 배포를 원할 경우:

- **✓ Poll SCM**: 주기적으로 Git 변경사항 확인
  ```
  H/15 * * * *  # 15분마다 확인
  ```

- **✓ GitHub hook trigger for GITScm polling**: GitHub Webhook 사용

#### Pipeline

**Definition**: `Pipeline script from SCM`

- **SCM**: `Git`
- **Repository URL**: `https://github.com/your-org/wadeulwadeul-heroes-be.git`
- **Credentials**: GitHub credentials 선택
- **Branch Specifier**: `*/main` (또는 원하는 브랜치)
- **Script Path**: `Jenkinsfile`

### 3. Jenkins Credentials 설정

Jenkins에서 AWS 자격증명을 설정해야 합니다.

#### AWS Credentials 추가

1. **Jenkins 관리** → **Manage Credentials** → **System** → **Global credentials**
2. **Add Credentials** 클릭
3. 다음 정보 입력:
   - **Kind**: `AWS Credentials`
   - **ID**: `aws-credentials` (Jenkinsfile에서 사용하는 ID)
   - **Description**: `AWS Credentials for EKS Deployment`
   - **Access Key ID**: 당신의 AWS Access Key
   - **Secret Access Key**: 당신의 AWS Secret Key
4. **OK** 클릭

#### GitHub Credentials 추가 (Private Repository인 경우)

1. **Add Credentials** 클릭
2. 다음 정보 입력:
   - **Kind**: `Username with password`
   - **Scope**: `Global`
   - **Username**: GitHub 사용자명
   - **Password**: GitHub Personal Access Token
   - **ID**: `github-credentials`
   - **Description**: `GitHub Credentials`
3. **OK** 클릭

### 4. 필수 Jenkins Plugins

다음 플러그인들이 설치되어 있어야 합니다:

- **Pipeline**: 기본 Pipeline 기능
- **Git**: Git SCM 연동
- **AWS Steps**: AWS 관련 작업
- **Kubernetes CLI**: kubectl 명령 실행
- **Pipeline: AWS Steps**: AWS 자격증명 관리

#### 플러그인 설치 방법

1. **Jenkins 관리** → **Manage Plugins**
2. **Available** 탭에서 필요한 플러그인 검색
3. 체크박스 선택 후 **Install without restart**

### 5. Jenkins Agent 설정

Jenkins Agent에 필요한 도구들이 설치되어 있어야 합니다:

```bash
# kubectl 설치
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# AWS CLI 설치
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 설치 확인
kubectl version --client
aws --version
```

## 배포 실행하기

### 1. Build with Parameters

1. Jenkins 프로젝트 페이지에서 **"Build with Parameters"** 클릭
2. 배포 파라미터 설정:

```
IMAGE_TAG: latest
NAMESPACE: goormthon-5
REPLICAS: 2
UPDATE_CONFIG: false
ENABLE_ROLLBACK: true
DEPLOY_MESSAGE: "Initial deployment"
```

3. **"Build"** 클릭

### 2. 배포 진행 모니터링

1. **Build History**에서 빌드 번호 클릭 (예: `#1`)
2. **Console Output** 클릭하여 실시간 로그 확인

### 3. 배포 단계

Jenkinsfile은 다음 단계를 실행합니다:

1. **Preparation**: 배포 파라미터 확인
2. **Configure AWS & Kubectl**: AWS 및 kubectl 설정
3. **Verify Image**: ECR에서 Docker 이미지 확인
4. **Update ConfigMap & Secret**: (선택) 설정 업데이트
5. **Deploy to Kubernetes**: Deployment 업데이트
6. **Wait for Rollout**: 배포 완료 대기
7. **Verify Deployment**: 배포 상태 확인
8. **Health Check**: 애플리케이션 헬스 체크

## 배포 시나리오

### 시나리오 1: 새 버전 배포

```
IMAGE_TAG: v1.1.0
NAMESPACE: goormthon-5
REPLICAS: 3
UPDATE_CONFIG: false
ENABLE_ROLLBACK: true
DEPLOY_MESSAGE: "Feature: Added new hero abilities"
```

### 시나리오 2: 긴급 핫픽스

```
IMAGE_TAG: hotfix-v1.0.1
NAMESPACE: goormthon-5
REPLICAS: 2
UPDATE_CONFIG: false
ENABLE_ROLLBACK: true
DEPLOY_MESSAGE: "Hotfix: Critical bug fix"
```

### 시나리오 3: 설정 변경 및 배포

```
IMAGE_TAG: latest
NAMESPACE: goormthon-5
REPLICAS: 2
UPDATE_CONFIG: true  # ConfigMap/Secret 업데이트
ENABLE_ROLLBACK: true
DEPLOY_MESSAGE: "Configuration update"
```

### 시나리오 4: 스케일 아웃

```
IMAGE_TAG: latest
NAMESPACE: goormthon-5
REPLICAS: 5  # 증가
UPDATE_CONFIG: false
ENABLE_ROLLBACK: true
DEPLOY_MESSAGE: "Scale out for high traffic"
```

## 알림 설정 (선택사항)

### Slack 알림

Jenkinsfile의 `post` 섹션에 Slack 알림을 추가할 수 있습니다:

```groovy
post {
    success {
        slackSend(
            color: 'good',
            message: "✓ Deployment Successful\nNamespace: ${params.NAMESPACE}\nImage: ${params.IMAGE_TAG}\nBuild: #${BUILD_NUMBER}",
            channel: '#deployments'
        )
    }
    failure {
        slackSend(
            color: 'danger',
            message: "✗ Deployment Failed\nNamespace: ${params.NAMESPACE}\nImage: ${params.IMAGE_TAG}\nBuild: #${BUILD_NUMBER}",
            channel: '#deployments'
        )
    }
}
```

### 이메일 알림

```groovy
post {
    always {
        emailext(
            subject: "${currentBuild.result}: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: """
                Build: ${env.BUILD_URL}
                Namespace: ${params.NAMESPACE}
                Image: ${params.IMAGE_TAG}
                Replicas: ${params.REPLICAS}
            """,
            to: 'devops-team@example.com'
        )
    }
}
```

## 트러블슈팅

### 1. AWS Credentials 오류

```
Error: Unable to locate credentials
```

**해결방법:**
- Jenkins Credentials에서 AWS 자격증명이 올바르게 설정되었는지 확인
- Credential ID가 `aws-credentials`인지 확인
- IAM 권한 확인 (EKS, ECR 접근 권한 필요)

### 2. kubectl 명령 실패

```
Error: kubectl: command not found
```

**해결방법:**
- Jenkins Agent에 kubectl이 설치되어 있는지 확인
- PATH 환경변수 확인

### 3. ECR 이미지를 찾을 수 없음

```
Error: Unable to find image in ECR
```

**해결방법:**
- ECR에 해당 이미지 태그가 존재하는지 확인
- ECR 리포지토리 이름 확인
- AWS 리전 확인

### 4. Health Check 실패

```
Warning: Health check failed
```

**해결방법:**
- Pod가 정상적으로 실행 중인지 확인
- `/health/ping` 엔드포인트가 응답하는지 확인
- ConfigMap과 Secret이 올바르게 설정되었는지 확인

## 추가 개선 사항

### 1. Multi-Environment 지원

여러 환경(dev, staging, prod)을 지원하려면:

```groovy
parameters {
    choice(
        name: 'ENVIRONMENT',
        choices: ['dev', 'staging', 'prod'],
        description: '배포 환경'
    )
}

environment {
    NAMESPACE = "${params.ENVIRONMENT}-namespace"
}
```

### 2. Approval Stage 추가

프로덕션 배포 전 승인 단계:

```groovy
stage('Approval') {
    when {
        expression { params.NAMESPACE == 'prod' }
    }
    steps {
        input message: 'Deploy to production?', ok: 'Deploy'
    }
}
```

### 3. Automated Testing

배포 전 자동 테스트:

```groovy
stage('Run Tests') {
    steps {
        sh '''
            uv run pytest tests/ -v
        '''
    }
}
```

## 참고 자료

- [Jenkins Pipeline Documentation](https://www.jenkins.io/doc/book/pipeline/)
- [Jenkins Kubernetes Plugin](https://plugins.jenkins.io/kubernetes/)
- [AWS CLI in Jenkins](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html)
