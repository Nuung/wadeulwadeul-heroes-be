# Security Guidelines

## AWS Credentials Management

### ⚠️ CRITICAL: Never Commit Credentials

**NEVER** commit the following to version control:
- AWS Access Keys
- AWS Secret Access Keys
- IAM User Passwords
- Database credentials
- API keys or tokens
- Any `.env` files containing real credentials

### Secure Credential Storage

#### Option 1: Environment Variables (Recommended)
```bash
# Set environment variables (Linux/macOS)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"

# Set environment variables (Windows PowerShell)
$env:AWS_ACCESS_KEY_ID="your-access-key"
$env:AWS_SECRET_ACCESS_KEY="your-secret-key"
```

#### Option 2: AWS CLI Configuration
```bash
aws configure
# This stores credentials in ~/.aws/credentials (not in the project)
```

#### Option 3: Use .env file locally (NOT committed)
```bash
# Copy the example file
cp .env.example .env

# Edit with your credentials
vim .env

# Load in scripts
source .env  # or use dotenv libraries
```

### Credential Rotation

If you accidentally expose credentials:

1. **Immediately deactivate** the exposed Access Key in AWS IAM Console
2. **Generate new credentials** in AWS IAM
3. **Update** your local configuration with new credentials
4. **Review** CloudTrail logs for any unauthorized access
5. **Report** the incident if you suspect compromise

### AWS IAM Best Practices

1. **Use IAM roles** when running in AWS (EKS pods, EC2 instances)
2. **Enable MFA** for IAM users
3. **Follow least privilege** principle for permissions
4. **Regularly rotate** access keys (every 90 days)
5. **Use temporary credentials** when possible
6. **Never use root account** credentials

### Kubernetes Secrets

For sensitive data in Kubernetes, use Secrets instead of ConfigMaps:

```bash
# Create a secret from literal values
kubectl create secret generic db-credentials \
  --from-literal=username=myuser \
  --from-literal=password=mypassword \
  -n goormthon-5

# Create a secret from a file
kubectl create secret generic app-secrets \
  --from-file=./secrets.json \
  -n goormthon-5
```

Then reference in your deployment:
```yaml
env:
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: db-credentials
      key: password
```

### ECR Image Scanning

Enable ECR image scanning for vulnerabilities:
```bash
aws ecr put-image-scanning-configuration \
    --repository-name goormthon-5 \
    --image-scanning-configuration scanOnPush=true \
    --region ap-northeast-2
```

### Security Checklist

- [ ] AWS credentials are stored securely (not in code)
- [ ] `.env` is in `.gitignore`
- [ ] Using least-privilege IAM policies
- [ ] MFA enabled for AWS account
- [ ] Regular credential rotation scheduled
- [ ] ECR image scanning enabled
- [ ] Kubernetes secrets used for sensitive data
- [ ] HTTPS/TLS enabled for production
- [ ] Security groups properly configured
- [ ] CloudTrail logging enabled

## Reporting Security Issues

If you discover a security vulnerability, please email:
- **Do not** create a public GitHub issue
- Contact: [your-security-email@example.com]
- Provide details of the vulnerability
- Allow reasonable time for response before public disclosure

## Additional Resources

- [AWS Security Best Practices](https://docs.aws.amazon.com/security/)
- [Kubernetes Security](https://kubernetes.io/docs/concepts/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
