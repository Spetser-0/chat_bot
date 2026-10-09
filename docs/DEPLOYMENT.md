# Spetser AI - Deployment Guide

**Last Updated**: 2026-10-09  
**Status**: Phase 12 — Docker & CI implemented (see Quick Start below)

---

## Overview

This guide covers deploying Spetser AI to production using Docker containers, with infrastructure recommendations for different scales.

**Implemented artifacts (Phase 12):**

| Path | Purpose |
|------|---------|
| `backend/Dockerfile` | Multi-stage Python 3.11 slim → uvicorn, non-root, healthcheck |
| `backend/.dockerignore` | Keeps secrets/tests out of the image |
| `frontend/Dockerfile` | Multi-stage Node build → nginx SPA |
| `frontend/nginx.conf` | SPA fallback + `/api/` reverse proxy (SSE-safe) |
| `frontend/.dockerignore` | Keeps node_modules out of the build context |
| `docker-compose.yml` | postgres + redis + backend + frontend |
| `.env.example` | Compose-level secrets (POSTGRES_*, APP_*) |
| `.github/workflows/ci.yml` | pytest, frontend lint/test/build, compose config, docker build |

---

## Quick Start (local full stack)

```bash
# 1. Root env (Postgres password for compose)
cp .env.example .env
# Edit .env → set POSTGRES_PASSWORD

# 2. Backend secrets (required by Settings)
cp backend/.env.example backend/.env
# Edit backend/.env → APP_SECRET_KEY, SESSION_SECRET_KEY,
# LLM_MASTER_ENCRYPTION_KEY (Fernet), payment keys as needed

# 3. Start everything (runs alembic upgrade head automatically)
docker compose up --build

# 4. Open
# Frontend: http://localhost:8080
# API:      http://localhost:8000/api/v1/health/ready
# Docs:     http://localhost:8000/api/docs  (disabled when APP_ENV=production)
```

**Ports (bound to localhost by default for data services):**

| Service | Host port |
|---------|-----------|
| frontend (nginx) | 8080 |
| backend (API) | 127.0.0.1:8000 |
| postgres | 127.0.0.1:5432 |
| redis | 127.0.0.1:6379 |

---

## Prerequisites

### Required Services

1. **PostgreSQL Database** (Supabase or self-hosted)
2. **Redis** (for rate limiting, caching, sessions)
3. **Domain & SSL Certificate** (Let's Encrypt recommended)
4. **Server** (VPS, cloud VM, or container platform)

### Minimum Server Requirements

**Small Scale** (< 1000 users):
- 2 CPU cores
- 4 GB RAM
- 40 GB SSD
- Ubuntu 22.04 LTS or similar

**Medium Scale** (1000-10000 users):
- 4 CPU cores
- 8 GB RAM
- 100 GB SSD

**Large Scale** (10000+ users):
- Consider horizontal scaling with load balancer
- Database read replicas
- Redis cluster

---

## Docker Deployment

### 1. Dockerfile (Backend)

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health/ready')"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2. Dockerfile (Frontend)

```dockerfile
# frontend/Dockerfile

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 3. docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: spetser-backend
    restart: unless-stopped
    env_file:
      - ./backend/.env
    ports:
      - "8000:8000"
    depends_on:
      - redis
    networks:
      - spetser-network
    volumes:
      - ./backend/logs:/app/logs

  frontend:
    build: ./frontend
    container_name: spetser-frontend
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
    networks:
      - spetser-network
    volumes:
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro

  redis:
    image: redis:7-alpine
    container_name: spetser-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - spetser-network
    command: redis-server --appendonly yes

networks:
  spetser-network:
    driver: bridge

volumes:
  redis-data:
```

---

## Environment Configuration

### Production .env (Backend)

```bash
# Environment
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<generate-with-openssl-rand-hex-32>
APP_ALLOWED_ORIGINS=https://spetser.ai

# Database (Supabase)
DATABASE_URL=postgresql+asyncpg://user:password@db.supabase.co:5432/postgres
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>

# Session
SESSION_SECRET_KEY=<generate-with-openssl-rand-hex-32>
SESSION_MAX_AGE_SECONDS=86400

# Redis
REDIS_URL=redis://redis:6379/0

# AI Providers
ANTHROPIC_API_KEY=<your-key>
GOOGLE_GEMINI_API_KEY=<your-key>
LLM_MASTER_ENCRYPTION_KEY=<generate-with-fernet-key>

# Payments
CRYPTO_PAYMENT_PROVIDER=nowpayments
CRYPTO_PAYMENT_API_KEY=<your-key>
CRYPTO_PAYMENT_WEBHOOK_SECRET=<your-secret>

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Rate Limits
RATE_LIMIT_REQUESTS_PER_MINUTE=60
AUTH_RATE_LIMIT_PER_MINUTE=5
```

### Production .env (Frontend)

```bash
VITE_API_BASE_URL=https://api.spetser.ai
```

---

## Nginx Configuration

```nginx
# frontend/nginx.conf

upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name spetser.ai www.spetser.ai;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name spetser.ai www.spetser.ai;
    
    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Frontend static files
    root /usr/share/nginx/html;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout for AI streaming
        proxy_read_timeout 300s;
    }
    
    # WebSocket support (if needed)
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Static file caching
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## SSL Certificate Setup

### Using Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d spetser.ai -d www.spetser.ai

# Auto-renewal (cron)
sudo crontab -e
# Add: 0 3 * * * certbot renew --quiet
```

---

## Database Migrations

```bash
# Run migrations before deploying new version
cd backend
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

---

## Deployment Steps

### Initial Deployment

```bash
# 1. Clone repository
git clone https://github.com/yourorg/spetser-ai.git
cd spetser-ai

# 2. Configure environment
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit .env files with production values

# 3. Run database migrations
cd backend
alembic upgrade head
cd ..

# 4. Build and start containers
docker-compose up -d --build

# 5. Verify health
curl https://spetser.ai/api/v1/health/ready
```

### Update Deployment

```bash
# 1. Pull latest code
git pull origin main

# 2. Run migrations
cd backend
alembic upgrade head
cd ..

# 3. Rebuild and restart
docker-compose up -d --build

# 4. Monitor logs
docker-compose logs -f backend
```

---

## Monitoring & Logging

### Centralized Logging

```yaml
# docker-compose.yml addition

services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Health Checks

```bash
# Backend health
curl https://api.spetser.ai/api/v1/health/live
curl https://api.spetser.ai/api/v1/health/ready

# Frontend health
curl https://spetser.ai
```

### Monitoring Tools

- **Logs**: Use journalctl, docker logs, or centralized logging (ELK stack)
- **Metrics**: Prometheus + Grafana (future)
- **Uptime**: UptimeRobot or similar
- **Errors**: Sentry (future)

---

## Backup Strategy

### Database Backups

```bash
# Daily backup cron
0 2 * * * pg_dump $DATABASE_URL | gzip > /backups/spetser_$(date +\%Y\%m\%d).sql.gz

# Keep last 30 days
0 3 * * * find /backups -name "spetser_*.sql.gz" -mtime +30 -delete
```

### Redis Backups

Redis automatically persists with `appendonly yes` in docker-compose.

---

## Scaling Strategies

### Horizontal Scaling

```yaml
# docker-compose.yml with scaling

services:
  backend:
    deploy:
      replicas: 3
  
  nginx-lb:
    image: nginx:alpine
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
      - "443:443"
```

### Load Balancer Config

```nginx
upstream backend_cluster {
    least_conn;
    server backend-1:8000;
    server backend-2:8000;
    server backend-3:8000;
}
```

---

## Security Checklist

- [ ] All secrets in environment variables (not code)
- [ ] HTTPS enabled with valid certificate
- [ ] Database uses SSL connection
- [ ] Redis password protected (if exposed)
- [ ] Firewall configured (only ports 80, 443, 22 open)
- [ ] SSH key-only authentication
- [ ] Regular security updates (`apt update && apt upgrade`)
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Admin panel IP allowlisted (optional)

---

## CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml

name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
        working-directory: ./backend
      - run: pytest
        working-directory: ./backend

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/spetser-ai
            git pull origin main
            cd backend && alembic upgrade head && cd ..
            docker-compose up -d --build
```

---

## Troubleshooting

### Backend Not Starting

```bash
# Check logs
docker logs spetser-backend

# Common issues:
# - Database connection failed: Check DATABASE_URL
# - Import errors: Rebuild image
# - Port conflict: Change port mapping
```

### Frontend Not Loading

```bash
# Check nginx logs
docker logs spetser-frontend

# Common issues:
# - 502 Bad Gateway: Backend not running
# - SSL errors: Check certificate paths
# - CORS errors: Check APP_ALLOWED_ORIGINS
```

### Database Connection Issues

```bash
# Test connection
docker exec spetser-backend python -c "from app.db.session import engine; import asyncio; asyncio.run(engine.connect())"
```

---

## Cost Estimates

### Infrastructure (Monthly)

- **VPS** (4 CPU, 8GB RAM): $20-40
- **Supabase** (Postgres): $0-25 (free tier available)
- **Redis** (self-hosted): $0
- **Domain**: $10/year
- **SSL Certificate**: Free (Let's Encrypt)

### AI Provider Costs

Variable based on usage. Monitor closely and set budget alerts.

---

**End of Deployment Guide**
