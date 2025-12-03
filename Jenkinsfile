pipeline {
    agent any

    parameters {
        string(
            name: 'IMAGE_TAG',
            defaultValue: 'latest',
            description: '배포할 Docker 이미지 태그 (예: latest, v1.0.0, dev-123)'
        )
        choice(
            name: 'NAMESPACE',
            choices: ['goormthon-5', 'goormthon-dev', 'goormthon-staging'],
            description: '배포할 Kubernetes 네임스페이스'
        )
        choice(
            name: 'REPLICAS',
            choices: ['1', '2', '3', '4', '5'],
            description: 'Pod 레플리카 수'
        )
        booleanParam(
            name: 'UPDATE_CONFIG',
            defaultValue: false,
            description: 'ConfigMap과 Secret 업데이트 여부'
        )
        booleanParam(
            name: 'ENABLE_ROLLBACK',
            defaultValue: true,
            description: '배포 실패 시 자동 롤백 활성화'
        )
        text(
            name: 'DEPLOY_MESSAGE',
            defaultValue: '',
            description: '배포 메시지 (선택사항)'
        )
    }

    environment {
        AWS_REGION = 'ap-northeast-2'
        ECR_REGISTRY = '837126493345.dkr.ecr.ap-northeast-2.amazonaws.com'
        IMAGE_NAME = 'goormthon-5'
        EKS_CLUSTER = 'goormthon-cluster'
        AWS_CREDENTIAL_ID = 'aws-credentials'
    }

    stages {
        stage('Preparation') {
            steps {
                script {
                    echo "=========================================="
                    echo "Wadeulwadeul Heroes Backend Deployment"
                    echo "=========================================="
                    echo "Image Tag: ${params.IMAGE_TAG}"
                    echo "Namespace: ${params.NAMESPACE}"
                    echo "Replicas: ${params.REPLICAS}"
                    echo "Update Config: ${params.UPDATE_CONFIG}"
                    echo "Enable Rollback: ${params.ENABLE_ROLLBACK}"
                    if (params.DEPLOY_MESSAGE) {
                        echo "Deploy Message: ${params.DEPLOY_MESSAGE}"
                    }
                    echo "=========================================="
                }
            }
        }

        stage('Configure AWS & Kubectl') {
            steps {
                script {
                    withCredentials([aws(credentialsId: env.AWS_CREDENTIAL_ID)]) {
                        echo "Configuring kubectl for EKS..."
                        sh """
                            aws eks update-kubeconfig \
                                --region ${env.AWS_REGION} \
                                --name ${env.EKS_CLUSTER}

                            kubectl config set-context --current --namespace=${params.NAMESPACE}

                            echo "Current context:"
                            kubectl config current-context
                        """
                    }
                }
            }
        }

        stage('Verify Image') {
            steps {
                script {
                    withCredentials([aws(credentialsId: env.AWS_CREDENTIAL_ID)]) {
                        echo "Verifying Docker image exists in ECR..."
                        sh """
                            aws ecr describe-images \
                                --region ${env.AWS_REGION} \
                                --repository-name ${env.IMAGE_NAME} \
                                --image-ids imageTag=${params.IMAGE_TAG}
                        """
                    }
                }
            }
        }

        stage('Update ConfigMap & Secret') {
            when {
                expression { params.UPDATE_CONFIG == true }
            }
            steps {
                script {
                    echo "Updating ConfigMap and Secret..."
                    sh """
                        kubectl apply -f k8s/backend/config/configmap.yaml
                        kubectl apply -f k8s/backend/config/secret.yaml

                        echo "ConfigMap and Secret updated successfully"
                    """
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                script {
                    echo "Starting deployment..."

                    // 이미지 태그 업데이트
                    sh """
                        # Deployment 이미지 업데이트
                        kubectl set image deployment/backend-deployment \
                            backend=${env.ECR_REGISTRY}/${env.IMAGE_NAME}:${params.IMAGE_TAG} \
                            -n ${params.NAMESPACE}

                        # Replicas 수 업데이트
                        kubectl scale deployment/backend-deployment \
                            --replicas=${params.REPLICAS} \
                            -n ${params.NAMESPACE}

                        # Change cause 어노테이션 업데이트
                        kubectl annotate deployment/backend-deployment \
                            kubernetes.io/change-cause="Jenkins deployment - Image: ${params.IMAGE_TAG}, Replicas: ${params.REPLICAS}, Build: ${BUILD_NUMBER}" \
                            -n ${params.NAMESPACE} \
                            --overwrite
                    """

                    echo "Deployment updated successfully"
                }
            }
        }

        stage('Wait for Rollout') {
            steps {
                script {
                    echo "Waiting for deployment to complete..."

                    def rolloutStatus = sh(
                        script: """
                            kubectl rollout status deployment/backend-deployment \
                                -n ${params.NAMESPACE} \
                                --timeout=5m
                        """,
                        returnStatus: true
                    )

                    if (rolloutStatus != 0) {
                        error("Deployment rollout failed!")
                    }

                    echo "Deployment completed successfully"
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                script {
                    echo "Verifying deployment..."
                    sh """
                        echo "=== Deployment Status ==="
                        kubectl get deployment backend-deployment -n ${params.NAMESPACE}

                        echo ""
                        echo "=== Pod Status ==="
                        kubectl get pods -l app=backend -n ${params.NAMESPACE}

                        echo ""
                        echo "=== Service Status ==="
                        kubectl get svc backend-service -n ${params.NAMESPACE}

                        echo ""
                        echo "=== Recent Events ==="
                        kubectl get events -n ${params.NAMESPACE} --sort-by='.lastTimestamp' | tail -10
                    """
                }
            }
        }

        stage('Health Check') {
            steps {
                script {
                    echo "Performing health check..."

                    def healthCheck = sh(
                        script: """
                            # Port-forward를 백그라운드로 실행
                            kubectl port-forward -n ${params.NAMESPACE} \
                                svc/backend-service 8080:80 &
                            PF_PID=\$!

                            # Port-forward가 준비될 때까지 대기
                            sleep 5

                            # Health check
                            curl -f http://localhost:8080/health/ping || exit 1

                            # Port-forward 종료
                            kill \$PF_PID
                        """,
                        returnStatus: true
                    )

                    if (healthCheck == 0) {
                        echo "Health check passed ✓"
                    } else {
                        echo "Warning: Health check failed, but deployment was successful"
                    }
                }
            }
        }
    }

    post {
        success {
            script {
                echo """
                ==========================================
                ✓ Deployment Successful!
                ==========================================
                Namespace: ${params.NAMESPACE}
                Image: ${env.ECR_REGISTRY}/${env.IMAGE_NAME}:${params.IMAGE_TAG}
                Replicas: ${params.REPLICAS}
                Build: #${BUILD_NUMBER}
                ==========================================
                """

                // Slack 알림 등을 여기에 추가 가능
                // slackSend(...)
            }
        }

        failure {
            script {
                echo """
                ==========================================
                ✗ Deployment Failed!
                ==========================================
                Namespace: ${params.NAMESPACE}
                Image: ${params.IMAGE_TAG}
                Build: #${BUILD_NUMBER}
                ==========================================
                """

                if (params.ENABLE_ROLLBACK) {
                    echo "Attempting automatic rollback..."
                    sh """
                        kubectl rollout undo deployment/backend-deployment \
                            -n ${params.NAMESPACE}

                        kubectl rollout status deployment/backend-deployment \
                            -n ${params.NAMESPACE} \
                            --timeout=3m
                    """
                    echo "Rollback completed"
                }

                // Slack 알림 등을 여기에 추가 가능
                // slackSend(color: 'danger', ...)
            }
        }

        always {
            script {
                echo "Deployment process completed"

                // 배포 히스토리 확인
                sh """
                    echo "=== Deployment History ==="
                    kubectl rollout history deployment/backend-deployment \
                        -n ${params.NAMESPACE}
                """
            }
        }
    }
}
