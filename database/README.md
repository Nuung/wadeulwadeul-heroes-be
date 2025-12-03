# PostgreSQL Database Setup for AWS EKS

Complete guide for deploying PostgreSQL on AWS EKS using StatefulSets.

## Overview

This PostgreSQL deployment uses:
- **StatefulSet** for stable pod identity and persistent storage
- **Headless Service** for direct pod communication
- **PersistentVolumeClaim** with AWS EBS (gp2) for data persistence
- **ConfigMaps** for configuration files and initialization scripts
- **Secrets** for credential management

## Directory Structure

```
database/postgres/
├── base/
│   ├── init.sql              # Database initialization script
│   ├── kustomization.yaml    # Base Kustomize configuration
│   ├── pg_hba.conf          # Client authentication config
│   ├── postgresql.conf       # PostgreSQL server config
│   ├── secret.yaml          # Database credentials
│   ├── service.yaml         # Headless service
│   └── statefulset.yaml     # StatefulSet definition
└── overlays/
    └── kustomization.yaml    # Production overlay
```

## Prerequisites

1. **EKS Cluster** with kubectl configured
2. **Storage Class** `gp2` (AWS EBS) available in the cluster
3. **Namespace** `goormthon-5` created
4. **AWS CLI** configured with appropriate permissions

## Quick Start

### 1. Deploy PostgreSQL

```bash
# Deploy using the script
./scripts/deploy-postgres.sh

# Or deploy manually
kubectl apply -k database/postgres/overlays/
```

### 2. Verify Deployment

```bash
# Check StatefulSet status
kubectl get statefulset postgres -n goormthon-5

# Check Pod status
kubectl get pods -n goormthon-5 -l app=postgres

# Check PersistentVolumeClaim
kubectl get pvc -n goormthon-5 -l app=postgres

# Check Service
kubectl get svc postgres -n goormthon-5
```

### 3. Test Connection

```bash
# Run test script
./scripts/test-postgres.sh

# Or test manually
kubectl exec -it postgres-0 -n goormthon-5 -- psql -U postgres -d wadeulwadeul_db -c "\l"
```

## Configuration

### Database Credentials

Edit `database/postgres/base/secret.yaml`:
```yaml
stringData:
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: your-secure-password
  POSTGRES_DB: wadeulwadeul_db
```

**Important:** For production, use proper secret management (AWS Secrets Manager, HashiCorp Vault, etc.)

### Resource Limits

Edit `database/postgres/overlays/kustomization.yaml` to adjust resources:
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

### Storage Size

Edit `database/postgres/base/statefulset.yaml`:
```yaml
volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      resources:
        requests:
          storage: 20Gi  # Adjust as needed
```

### PostgreSQL Configuration

- **postgresql.conf**: Server configuration (connections, memory, WAL, logging)
- **pg_hba.conf**: Client authentication rules

## Database Initialization

The `init.sql` script runs **only once** when the database is first created:

- Creates extensions (uuid-ossp, pgcrypto)
- Creates schemas (app, audit)
- Creates tables (heroes, audit logs)
- Inserts sample data
- Creates functions and triggers

**Note:** If PVC data already exists, `init.sql` will NOT run again.

## Connecting to PostgreSQL

### From Within the Cluster

Applications in the same namespace can connect using:
```
Host: postgres.goormthon-5.svc.cluster.local
Port: 5432
Database: wadeulwadeul_db
User: postgres
Password: postgres123
```

Connection string:
```
postgresql://postgres:postgres123@postgres.goormthon-5.svc.cluster.local:5432/wadeulwadeul_db
```

### From Local Machine (Port Forward)

```bash
# Forward port 5432
kubectl port-forward svc/postgres 5432:5432 -n goormthon-5

# Connect with psql
psql -h localhost -U postgres -d wadeulwadeul_db

# Or with connection string
psql postgresql://postgres:postgres123@localhost:5432/wadeulwadeul_db
```

### From Pod Shell

```bash
# Access PostgreSQL shell
kubectl exec -it postgres-0 -n goormthon-5 -- bash

# Then connect
psql -U postgres -d wadeulwadeul_db
```

## Common Operations

### View Database Information

```bash
# List databases
kubectl exec -it postgres-0 -n goormthon-5 -- psql -U postgres -c "\l"

# List schemas
kubectl exec -it postgres-0 -n goormthon-5 -- psql -U postgres -d wadeulwadeul_db -c "\dn"

# List tables
kubectl exec -it postgres-0 -n goormthon-5 -- psql -U postgres -d wadeulwadeul_db -c "\dt app.*"

# Describe a table
kubectl exec -it postgres-0 -n goormthon-5 -- psql -U postgres -d wadeulwadeul_db -c "\d app.heroes"
```

### Query Data

```bash
# Select all heroes
kubectl exec -it postgres-0 -n goormthon-5 -- psql -U postgres -d wadeulwadeul_db -c "SELECT * FROM app.heroes;"

# Count records
kubectl exec -it postgres-0 -n goormthon-5 -- psql -U postgres -d wadeulwadeul_db -c "SELECT COUNT(*) FROM app.heroes;"
```

### View Logs

```bash
# Stream logs
kubectl logs -f postgres-0 -n goormthon-5

# View last 100 lines
kubectl logs --tail=100 postgres-0 -n goormthon-5
```

### Restart PostgreSQL

```bash
# Restart the StatefulSet
kubectl rollout restart statefulset/postgres -n goormthon-5

# Or delete the pod (will be recreated)
kubectl delete pod postgres-0 -n goormthon-5
```

## Backup and Restore

### Create Backup

```bash
# Backup to file
kubectl exec postgres-0 -n goormthon-5 -- pg_dump -U postgres wadeulwadeul_db > backup.sql

# Backup with timestamp
kubectl exec postgres-0 -n goormthon-5 -- pg_dump -U postgres wadeulwadeul_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup specific schema
kubectl exec postgres-0 -n goormthon-5 -- pg_dump -U postgres -n app wadeulwadeul_db > app_schema_backup.sql
```

### Restore from Backup

```bash
# Restore from file
kubectl exec -i postgres-0 -n goormthon-5 -- psql -U postgres wadeulwadeul_db < backup.sql

# Restore specific schema
kubectl exec -i postgres-0 -n goormthon-5 -- psql -U postgres wadeulwadeul_db < app_schema_backup.sql
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod events
kubectl describe pod postgres-0 -n goormthon-5

# Check StatefulSet events
kubectl describe statefulset postgres -n goormthon-5

# Check PVC status
kubectl get pvc -n goormthon-5
```

### Connection Issues

```bash
# Test from another pod
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -n goormthon-5 -- \
  psql -h postgres.goormthon-5.svc.cluster.local -U postgres -d wadeulwadeul_db

# Check service
kubectl get svc postgres -n goormthon-5
kubectl get endpoints postgres -n goormthon-5
```

### Storage Issues

```bash
# Check PVC status
kubectl get pvc -n goormthon-5 -l app=postgres

# Check PV
kubectl get pv

# Describe PVC for details
kubectl describe pvc postgres-data-postgres-0 -n goormthon-5
```

### Data Persistence Verification

```bash
# Create test data
kubectl exec -it postgres-0 -n goormthon-5 -- psql -U postgres -d wadeulwadeul_db -c \
  "INSERT INTO app.heroes (name, description, level) VALUES ('Test Hero', 'Persistence test', 99);"

# Delete the pod
kubectl delete pod postgres-0 -n goormthon-5

# Wait for pod to recreate and check data
kubectl wait --for=condition=ready pod/postgres-0 -n goormthon-5 --timeout=2m
kubectl exec -it postgres-0 -n goormthon-5 -- psql -U postgres -d wadeulwadeul_db -c \
  "SELECT * FROM app.heroes WHERE name='Test Hero';"
```

## Performance Monitoring

### Database Statistics

```bash
# Current connections
kubectl exec -it postgres-0 -n goormthon-5 -- psql -U postgres -d wadeulwadeul_db -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Table sizes
kubectl exec -it postgres-0 -n goormthon-5 -- psql -U postgres -d wadeulwadeul_db -c \
  "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   WHERE schemaname = 'app'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Database size
kubectl exec -it postgres-0 -n goormthon-5 -- psql -U postgres -c \
  "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) AS size
   FROM pg_database;"
```

### Resource Usage

```bash
# Pod resource usage
kubectl top pod postgres-0 -n goormthon-5

# Storage usage
kubectl exec -it postgres-0 -n goormthon-5 -- df -h /var/lib/postgresql/data
```

## Scaling Considerations

This setup uses a **single replica** StatefulSet. For production high availability:

1. **Read Replicas**: Configure PostgreSQL streaming replication
2. **Load Balancing**: Use pgpool-II or HAProxy
3. **Backup Strategy**: Regular automated backups to S3
4. **Monitoring**: Prometheus + Grafana for metrics
5. **Multi-AZ**: Distribute replicas across availability zones

## Security Best Practices

1. **Change Default Password**: Update credentials in Secret before deploying
2. **Network Policies**: Restrict access to PostgreSQL pods
3. **TLS/SSL**: Enable SSL for encrypted connections
4. **Regular Updates**: Keep PostgreSQL version up to date
5. **Audit Logging**: Enable and monitor audit logs
6. **Backup Encryption**: Encrypt backups at rest
7. **Secret Management**: Use AWS Secrets Manager or Vault

## Cleanup

To remove PostgreSQL deployment:

```bash
# Delete StatefulSet and Service (keeps PVC)
kubectl delete -k database/postgres/overlays/

# Delete PVC (WARNING: This deletes all data!)
kubectl delete pvc postgres-data-postgres-0 -n goormthon-5
```

## References

- [PostgreSQL Official Documentation](https://www.postgresql.org/docs/)
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [AWS EBS CSI Driver](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [GitHub Reference Repository](https://github.com/goorm-dev/9oormthon-k8s/tree/master/database/postgres)
