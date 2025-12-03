# Kubernetes Deployment Guide for AWS EKS

This guide provides step-by-step instructions for deploying the Wadeulwadeul Heroes backend to AWS EKS.

## Prerequisites

### Required Tools

1. **AWS CLI** (v2.x or later)
   - Installation: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
   - Verify: `aws --version`

2. **kubectl** (v1.26+)
   - Installation: https://kubernetes.io/docs/tasks/tools/
   - Verify: `kubectl version --client`

3. **Docker** (v20.10+)
   - Installation: https://docs.docker.com/get-docker/
   - Verify: `docker --version`

4. **eksctl** (optional, for cluster creation)
   - Installation: https://eksctl.io/installation/
   - Verify: `eksctl version`

### AWS Credentials

You need the following AWS credentials:
- AWS Access Key ID
- AWS Secret Access Key
- IAM permissions for EKS, ECR, and related services

## Project Structure

```
k8s/
├── README.md
└── backend/
    ├── namespace.yaml          # Namespace definition
    ├── backend.yaml            # Deployment & Service
    ├── ingress.yaml            # Ingress configuration
    ├── kustomization.yaml      # Kustomize manifest
    └── config/
        └── backend-config.json # Application configuration
```

## Step-by-Step Deployment

### Step 1: Configure AWS Credentials

**Option A: Using environment variables**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"

# Run setup script
./scripts/setup-aws.sh
```

**Option B: Manual configuration**
```bash
aws configure
# Enter your Access Key ID, Secret Access Key, and region (ap-northeast-2)
```

Verify configuration:
```bash
aws sts get-caller-identity
```

### Step 2: Connect to EKS Cluster

Update your kubeconfig to connect to the EKS cluster:
```bash
aws eks update-kubeconfig --region ap-northeast-2 --name goormthon-cluster
```

Verify cluster connection:
```bash
kubectl cluster-info
kubectl get nodes
```

### Step 3: Configure Application Settings

Edit the configuration file:
```bash
vim k8s/backend/config/backend-config.json
```

Update with your application settings (database credentials, API keys, etc.)

### Step 4: Build and Push Docker Image

Build the Docker image and push to Amazon ECR:
```bash
# Make script executable
chmod +x scripts/build-and-push.sh

# Build and push (uses 'latest' tag by default)
./scripts/build-and-push.sh

# Or specify a custom tag
./scripts/build-and-push.sh v1.0.0
```

**Manual steps:**
```bash
# Build image
docker build -t goormthon-5:latest .

# Tag for ECR
docker tag goormthon-5:latest 837126493345.dkr.ecr.ap-northeast-2.amazonaws.com/goormthon-5:latest

# Login to ECR
aws ecr get-login-password --region ap-northeast-2 | \
    docker login --username AWS --password-stdin 837126493345.dkr.ecr.ap-northeast-2.amazonaws.com

# Push image
docker push 837126493345.dkr.ecr.ap-northeast-2.amazonaws.com/goormthon-5:latest
```

### Step 5: Deploy to Kubernetes

Deploy using the provided script:
```bash
# Make script executable
chmod +x scripts/deploy-to-eks.sh

# Deploy
./scripts/deploy-to-eks.sh
```

**Manual deployment:**
```bash
# Create namespace
kubectl apply -f k8s/backend/namespace.yaml

# Deploy using Kustomize
kubectl apply -k k8s/backend/

# Check deployment status
kubectl rollout status deployment/backend-deployment -n goormthon-5
```

### Step 6: Verify Deployment

Check all resources:
```bash
kubectl get all -n goormthon-5
```

Check pods:
```bash
kubectl get pods -n goormthon-5
```

Check ingress:
```bash
kubectl get ingress -n goormthon-5
```

View logs:
```bash
kubectl logs -f deployment/backend-deployment -n goormthon-5
```

### Step 7: Access Your Application

Your application will be accessible at:
```
http://goormthon-5.goorm.training/api/
```

Test the health endpoint:
```bash
curl http://goormthon-5.goorm.training/api/health/ping
```

## Updating the Application

### Update Application Code

1. Make code changes
2. Build and push new Docker image with a new tag:
   ```bash
   ./scripts/build-and-push.sh v1.0.1
   ```
3. Update the image tag in `k8s/backend/backend.yaml`
4. Redeploy:
   ```bash
   kubectl apply -k k8s/backend/
   ```

### Update Configuration

1. Edit `k8s/backend/config/backend-config.json`
2. Run the update script:
   ```bash
   chmod +x scripts/update-config.sh
   ./scripts/update-config.sh
   ```

**Manual update:**
```bash
# Apply changes
kubectl apply -k k8s/backend/

# Restart deployment to pick up new config
kubectl rollout restart deployment/backend-deployment -n goormthon-5
```

## Scaling the Application

Manually scale replicas:
```bash
kubectl scale deployment/backend-deployment --replicas=3 -n goormthon-5
```

Or edit `k8s/backend/backend.yaml` and update the `replicas` field, then:
```bash
kubectl apply -k k8s/backend/
```

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n goormthon-5
kubectl describe pod <pod-name> -n goormthon-5
```

### View Logs
```bash
# Current logs
kubectl logs deployment/backend-deployment -n goormthon-5

# Follow logs
kubectl logs -f deployment/backend-deployment -n goormthon-5

# Previous container logs (if pod crashed)
kubectl logs <pod-name> -n goormthon-5 --previous
```

### Debug Pod
```bash
# Execute shell in pod
kubectl exec -it <pod-name> -n goormthon-5 -- /bin/sh

# Port forward for local testing
kubectl port-forward deployment/backend-deployment 8000:8000 -n goormthon-5
```

### Common Issues

**1. ImagePullBackOff Error**
- Ensure you're logged into ECR: `aws ecr get-login-password ...`
- Verify the image exists in ECR
- Check IAM permissions for ECR access

**2. CrashLoopBackOff Error**
- Check logs: `kubectl logs <pod-name> -n goormthon-5`
- Verify application configuration
- Check health check endpoints

**3. Ingress Not Working**
- Verify Ingress controller is installed in the cluster
- Check Ingress resource: `kubectl describe ingress backend-ingress -n goormthon-5`
- Verify DNS is pointing to the Ingress controller's load balancer

## Resource Management

### View Resource Usage
```bash
kubectl top pods -n goormthon-5
kubectl top nodes
```

### Update Resource Limits
Edit `k8s/backend/backend.yaml` and modify the `resources` section:
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "200m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

Then apply:
```bash
kubectl apply -k k8s/backend/
```

## Cleanup

Delete all resources:
```bash
kubectl delete -k k8s/backend/
kubectl delete namespace goormthon-5
```

## Important Notes

1. **Port Configuration**: The backend application MUST run on port 8000 (as configured in the Dockerfile)
2. **Health Checks**: Ensure `/health/ping` endpoint is accessible for liveness and readiness probes
3. **ConfigMap Changes**: Always restart the deployment after updating ConfigMap
4. **Security**: Never commit AWS credentials to version control
5. **ECR Repository**: Ensure the ECR repository `goormthon-5` exists before pushing images

## References

- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/latest/userguide/)
- [kubectl Documentation](https://kubernetes.io/docs/reference/kubectl/)
- [Kustomize Documentation](https://kubectl.docs.kubernetes.io/guides/introduction/kustomize/)
- [Amazon ECR Documentation](https://docs.aws.amazon.com/ecr/)
- [GitHub Reference Repository](https://github.com/goorm-dev/9oormthon-k8s/tree/master/k8s/backend)
