# Production Deployment Guide

## Overview

HealthOS API supports multiple deployment options:
- **Docker Compose** (local development)
- **AWS ECS Fargate** (recommended for production)
- **Kubernetes** (horizontal scaling)

## Quick Start: Docker Compose

### Prerequisites
- Docker & Docker Compose installed
- Environment variables in `.env` file

### Run Locally

```bash
# Create .env file with required variables
cat > .env << EOF
SECRET_KEY=your_secret_key
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_supabase_key
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
EOF

# Start all services
docker-compose up -d

# Verify services
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

**Services Started:**
- FastAPI (8000) - Main application
- Redis (6379) - Cache and Celery broker
- Ollama (11434) - LLM service
- Celery Worker - Async task processing
- Celery Beat - Scheduled tasks

### Stop Services

```bash
docker-compose down
docker-compose down -v  # Also remove volumes
```

---

## AWS ECS Fargate Deployment

### Architecture

```
┌─────────────────────────┐
│   Application Load      │
│    Balancer (ALB)       │
└───────────┬─────────────┘
            │
    ┌───────┴────────┐
    │                │
┌───▼────┐      ┌───▼────┐
│ Task 1 │      │ Task 2 │   (Auto-scaling)
│ (0.5   │      │ (0.5   │
│  vCPU) │      │  vCPU) │
└────────┘      └────────┘
    │                │
    └────────┬───────┘
             │
         ┌───▼──────────┐
         │  Redis Cache │
         │  (ElastiCache)
         └──────────────┘
```

### Prerequisites

1. **AWS Account Setup**
   ```bash
   # Configure AWS credentials
   aws configure
   
   # Required services:
   # - ECS Cluster
   # - ALB/NLB
   # - RDS (optional, for PostgreSQL)
   # - ElastiCache (Redis)
   # - ECR (Docker registry)
   # - CloudWatch Logs
   # - Secrets Manager
   ```

2. **Secrets in AWS Secrets Manager**
   ```bash
   aws secretsmanager create-secret \
     --name healthos/SECRET_KEY \
     --secret-string "your_secret_key"
   
   aws secretsmanager create-secret \
     --name healthos/SUPABASE_KEY \
     --secret-string "your_supabase_key"
   
   # Repeat for other secrets...
   ```

3. **Create ECR Repository**
   ```bash
   aws ecr create-repository --repository-name healthos
   ```

### Deployment Steps

1. **Build and Push Docker Image**
   ```bash
   # Get ECR login token
   aws ecr get-login-password --region us-east-1 | \
     docker login --username AWS --password-stdin \
     123456789.dkr.ecr.us-east-1.amazonaws.com
   
   # Build image
   docker build -t healthos:latest .
   
   # Tag for ECR
   docker tag healthos:latest \
     123456789.dkr.ecr.us-east-1.amazonaws.com/healthos:latest
   
   # Push to ECR
   docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/healthos:latest
   ```

2. **Register ECS Task Definition**
   ```bash
   aws ecs register-task-definition \
     --cli-input-json file://aws_ecs_task_definition.json
   ```

3. **Create/Update ECS Service**
   ```bash
   aws ecs create-service \
     --cluster healthos-production \
     --service-name healthos-api \
     --cli-input-json file://aws_ecs_service.json
   ```

4. **Configure Auto-Scaling**
   ```bash
   aws application-autoscaling register-scalable-target \
     --service-namespace ecs \
     --resource-id service/healthos-production/healthos-api \
     --scalable-dimension ecs:service:DesiredCount \
     --min-capacity 2 \
     --max-capacity 10
   
   aws application-autoscaling put-scaling-policy \
     --policy-name cpu-scaling \
     --service-namespace ecs \
     --resource-id service/healthos-production/healthos-api \
     --scalable-dimension ecs:service:DesiredCount \
     --policy-type TargetTrackingScaling \
     --target-tracking-scaling-policy-configuration \
       TargetValue=70,PredefinedMetricSpecification={PredefinedMetricType=ECSServiceAverageCPUUtilization}
   ```

### Verify Deployment

```bash
# Check service status
aws ecs describe-services \
  --cluster healthos-production \
  --services healthos-api

# View CloudWatch logs
aws logs tail /ecs/healthos-production --follow

# Health check
curl https://api.healthos.ai/health
curl https://api.healthos.ai/metrics
```

---

## Kubernetes Deployment

### Helm Chart Structure

```
healthos-helm/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   └── secret.yaml
```

### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace healthos

# Create secrets
kubectl create secret generic healthos-secrets \
  --from-literal=SECRET_KEY=$SECRET_KEY \
  --from-literal=SUPABASE_KEY=$SUPABASE_KEY \
  -n healthos

# Install Helm chart
helm install healthos ./healthos-helm \
  -n healthos \
  --values values.yaml

# Verify deployment
kubectl get pods -n healthos
kubectl logs -n healthos -l app=healthos-api --follow
```

---

## Monitoring & Alerts

### CloudWatch Dashboards

```bash
# View metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=healthos-api \
  --start-time 2026-03-01T00:00:00Z \
  --end-time 2026-03-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

### Sentry Error Tracking

Errors automatically sent to Sentry:
- Visit https://sentry.io/organizations/your-org/issues/
- Set up alerts for critical errors
- Review performance traces

### Health Check Endpoints

```bash
# System health
curl https://api.healthos.ai/health
# Response: 200 OK if healthy, 503 if degraded

# Performance metrics
curl https://api.healthos.ai/metrics
# Response: Request count, latency, error rates by endpoint
```

---

## Rollback & Recovery

### Rollback to Previous Version

```bash
# ECS
aws ecs update-service \
  --cluster healthos-production \
  --service healthos-api \
  --task-definition healthos-api:5  # Previous revision

# Kubernetes
kubectl rollout undo deployment/healthos-api -n healthos
```

### Database Backups

```bash
# Automated via Supabase (daily backups)
# Manual backup:
supabase db push  # Export schema
pg_dump $DATABASE_URL > backup.sql
```

---

## Cost Optimization

### ECS Fargate Cost Reduction

1. **Right-sizing**: Start with 0.5 vCPU, increase if needed
2. **Spot instances**: Use Fargate Spot for non-critical workloads (70% savings)
3. **Reserved capacity**: For predictable traffic
4. **Auto-scaling**: Scale down during off-peak hours

### Redis Cost Reduction

- Use ElastiCache with auto-failover disabled for development
- Enable compression for cache items >1KB

---

## Troubleshooting

### Service won't start

```bash
# Check CloudWatch logs
aws logs tail /ecs/healthos-production --follow

# Check task details
aws ecs describe-tasks \
  --cluster healthos-production \
  --tasks <task-arn>
```

### High latency

```bash
# Check metrics endpoint
curl https://api.healthos.ai/metrics

# Analyze by endpoint
# - Check Ollama response times
# - Check Redis connectivity
# - Check Supabase query times
```

### Out of memory

```bash
# Increase task memory in ECS task definition
# Current: 1024 MB
# Try: 2048 MB (for ~$0.50/month more)
```

---

## Production Checklist

- [ ] Secrets configured in AWS Secrets Manager
- [ ] RDS database backed up daily
- [ ] CloudWatch alarms configured
- [ ] Auto-scaling policies tested
- [ ] Load balancer health checks passing
- [ ] SSL/TLS certificates valid
- [ ] Database connection pooling enabled
- [ ] Redis persistence enabled
- [ ] Sentry error tracking active
- [ ] CloudFront CDN configured (optional)
- [ ] Disaster recovery plan tested
- [ ] On-call alerts configured
