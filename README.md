# Wadeulwadeul Heroes Backend

FastAPI backend application for wadeulwadeul-heroes project.

## Tech Stack

- **Python**: 3.13
- **Framework**: FastAPI
- **Package Manager**: uv
- **Server**: Uvicorn
- **Database**: PostgreSQL 16
- **ORM**: SQLAlchemy 2.0 (Async)
- **Linter/Formatter**: Ruff

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py       # Health check endpoints
│   │       ├── heroes.py       # Heroes CRUD endpoints
│   │       └── users.py        # Users CRUD endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Application configuration
│   │   ├── database.py         # Database session management
│   │   └── auth.py             # Authentication middleware & dependencies
│   └── models/
│       ├── __init__.py
│       ├── hero.py             # Hero database model
│       └── user.py             # User database model
├── database/
│   ├── README.md               # Database deployment guide
│   └── postgres/
│       ├── base/               # Base PostgreSQL manifests
│       └── overlays/           # Production overlays
├── k8s/
│   ├── DEPLOYMENT.md           # 배포 가이드 (Jenkins & 수동)
│   ├── JENKINS.md              # Jenkins 설정 가이드
│   └── backend/
│       ├── namespace.yaml      # Namespace definition
│       ├── backend.yaml        # Deployment & Service
│       ├── ingress.yaml        # Ingress configuration
│       ├── kustomization.yaml  # Kustomize manifest
│       └── config/
│           ├── configmap.yaml  # ConfigMap for environment variables
│           └── secret.yaml     # Secret for sensitive data
├── Dockerfile
├── .dockerignore
├── Jenkinsfile                # Jenkins CI/CD pipeline
├── pyproject.toml
└── README.md
```

## Getting Started

### Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- Python 3.13+
- Docker (for containerized deployment)

### Local Development

1. Install dependencies:
```bash
uv sync
```

2. Run the application:
```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI Schema: `http://localhost:8000/openapi.json`

**Production:**
- Swagger UI: `http://goormthon-5.goorm.training/api/docs`
- ReDoc: `http://goormthon-5.goorm.training/api/redoc`

API documentation is enabled by default in all environments. You can disable it by setting `ENABLE_DOCS=false` in your environment variables.

**Important:** For production deployment behind reverse proxy (Ingress), set `ROOT_PATH=/api` to ensure correct path routing for API docs and OpenAPI schema.

### Authentication (Hackathon Mode)

This project uses a simple header-based authentication for hackathon purposes:

**Header:** `wadeulwadeul-user`
**Value:** User's email address

The middleware automatically loads the user from the database based on the email provided in the header.

**Usage Example:**
```bash
# Create a user first
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'

# Access authenticated endpoint
curl http://localhost:8000/api/v1/users/me \
  -H "wadeulwadeul-user: john@example.com"
```

**For Developers:**
- Use `get_current_user` dependency for required authentication (returns 401 if not authenticated)
- Use `get_current_user_optional` dependency for optional authentication (returns None if not authenticated)

```python
from app.core.auth import get_current_user

@router.get("/protected")
async def protected_endpoint(user: User = Depends(get_current_user)):
    return {"message": f"Hello, {user.name}!"}
```

### Available Endpoints

**Health:**
- `GET /` - Root endpoint
- `GET /health/ping` - Health check endpoint

**Heroes API:**
- `GET /api/v1/heroes` - List all heroes
- `GET /api/v1/heroes/{id}` - Get hero by ID
- `POST /api/v1/heroes` - Create new hero
- `DELETE /api/v1/heroes/{id}` - Delete hero

**Users API:**
- `GET /api/v1/users/me` - Get current authenticated user (requires auth)
- `GET /api/v1/users` - List all users
- `GET /api/v1/users/{id}` - Get user by ID
- `POST /api/v1/users` - Create new user
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user

## PostgreSQL Database

### Local Development with PostgreSQL

For local development, you can use Docker to run PostgreSQL:

```bash
# Run PostgreSQL container
docker run -d \
  --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres123 \
  -e POSTGRES_DB=wadeulwadeul_db \
  -p 5432:5432 \
  postgres:16-alpine

# Run initialization script (optional)
docker exec -i postgres psql -U postgres -d wadeulwadeul_db < database/postgres/base/init.sql

# Update .env file
cat > .env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres123
DB_NAME=wadeulwadeul_db
EOF

# Run migrations (if using Alembic)
# uv run alembic upgrade head

# Start the application
uv run uvicorn app.main:app --reload
```

For detailed PostgreSQL setup and management, see [database/README.md](database/README.md)

## Docker

### Build the image:
```bash
docker build -t wadeulwadeul-heroes-be .
```

### Run the container:
```bash
docker run -p 8000:8000 wadeulwadeul-heroes-be
```

### Health Check

The Docker container includes a health check that pings `/health/ping` every 30 seconds.

## Kubernetes Deployment (AWS EKS)

This project includes complete Kubernetes manifests for deploying to AWS EKS with Jenkins CI/CD.

### 🚀 Deployment Methods

#### Option 1: Jenkins (권장)

**Jenkins를 통한 파라미터 기반 수동 배포:**

1. Jenkins에서 **"Build with Parameters"** 클릭
2. 배포 파라미터 설정:
   - `IMAGE_TAG`: 배포할 이미지 태그 (예: `v1.0.0`, `latest`)
   - `NAMESPACE`: 배포할 네임스페이스 (기본: `goormthon-5`)
   - `REPLICAS`: Pod 레플리카 수 (1~5)
   - `UPDATE_CONFIG`: ConfigMap/Secret 업데이트 여부
   - `ENABLE_ROLLBACK`: 자동 롤백 활성화 여부
3. **"Build"** 클릭하여 배포 시작

자세한 내용은 [k8s/DEPLOYMENT.md](k8s/DEPLOYMENT.md)를 참고하세요.

#### Option 2: 수동 배포

1. **Configure AWS credentials:**
   ```bash
   # AWS CLI 설정
   aws configure

   # EKS 클러스터 kubeconfig 업데이트
   aws eks update-kubeconfig --region ap-northeast-2 --name goormthon-cluster
   ```

2. **Build and push Docker image to ECR:**
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

3. **Deploy to EKS:**
   ```bash
   # Create namespace (if not exists)
   kubectl create namespace goormthon-5

   # Deploy using Kustomize
   kubectl apply -k k8s/backend/

   # Check deployment status
   kubectl rollout status deployment/backend-deployment -n goormthon-5
   ```

### Deployment Details

- **Namespace**: `goormthon-5`
- **ECR Registry**: `837126493345.dkr.ecr.ap-northeast-2.amazonaws.com`
- **Image Name**: `goormthon-5`
- **Ingress**: `http://goormthon-5.goorm.training/api/`
- **CI/CD**: Jenkins (Parameterized Build)

### Useful Kubectl Commands

```bash
# 전체 상태 확인
kubectl get all -n goormthon-5

# Pod 로그 확인
kubectl logs -f -l app=backend -n goormthon-5

# 배포 히스토리
kubectl rollout history deployment/backend-deployment -n goormthon-5

# Replicas 수 변경
kubectl scale deployment/backend-deployment --replicas=3 -n goormthon-5
```

For detailed deployment instructions, see [k8s/DEPLOYMENT.md](k8s/DEPLOYMENT.md)

## Development

### Code Quality

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

Check code with linter:
```bash
uv run ruff check app/
```

Auto-fix linting issues:
```bash
uv run ruff check app/ --fix
```

Format code:
```bash
uv run ruff format app/
```

Run both linting and formatting:
```bash
uv run ruff check app/ --fix && uv run ruff format app/
```

### Adding new routes

1. Create a new route file in `app/api/routes/`
2. Define your router and endpoints
3. Include the router in `app/main.py`

### Environment Variables

Create a `.env` file in the root directory:
```env
# Application Configuration
APP_NAME=Wadeulwadeul Heroes API
APP_VERSION=0.1.0
DEBUG=false

# API Documentation (enabled by default)
ENABLE_DOCS=true
DOCS_URL=/docs
REDOC_URL=/redoc
OPENAPI_URL=/openapi.json
ROOT_PATH=  # Empty for local, "/api" for production behind Ingress

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres123
DB_NAME=wadeulwadeul_db
```

## References

### Application Framework
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [uv Docker Guide](https://docs.astral.sh/uv/guides/integration/docker/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

### Kubernetes & AWS
- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/latest/userguide/)
- [kubectl Documentation](https://kubernetes.io/docs/reference/kubectl/)
- [eksctl Documentation](https://eksctl.io/)
- [Kustomize Documentation](https://kubectl.docs.kubernetes.io/guides/introduction/kustomize/)
- [Amazon ECR Documentation](https://docs.aws.amazon.com/ecr/)
- [GitHub Reference Repository](https://github.com/goorm-dev/9oormthon-k8s/tree/master/k8s/backend)
