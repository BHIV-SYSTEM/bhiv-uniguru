# UniGuru Sovereign Deployment Blueprint: VM Deployment Guide

This guide details the step-by-step procedure to provision, configure, optimize, and deploy the production-ready **UniGuru** system on a dedicated VM or VPS behind a central host-level Nginx reverse proxy.

---

## 1. Target Environment & Specifications

The deployment stack is designed to run on a dedicated VM instance with the following target specifications:
*   **Operating System:** Ubuntu 22.04 LTS (or Debian 12)
*   **CPU:** 2x Dedicated vCPUs (minimum)
*   **RAM:** 4GB RAM (minimum)
*   **Storage:** 40GB SSD
*   **Network:** 1x Private/Public IP Address with DNS mapping to the VM host.

---

## 2. VM Directory Structure

All application templates, configuration files, and persistent volumes are anchored under `~/UNIGURU` or `/opt/uniguru/` to maintain clean separation from other host services.

Initialize the directory tree:
```bash
# Create target subdirectories
mkdir -p ~/UNIGURU/docs
mkdir -p ~/UNIGURU/configs
```

### Layout Mapping:
*   `~/UNIGURU/` — Root directory containing `docker-compose.production.yml` and the `.env` configuration.
*   `~/UNIGURU/docs/` — Stores persistent Release History (`RELEASE_HISTORY.md`).
*   `/var/lib/uniguru/` — Holds the local metrics state and FAISS/RAG sqlite data (`chunks.db`).

---

## 3. Host OS Optimization & Hardening

To support high socket connection limits and minimize disk I/O bottlenecks:

```bash
# 1. Update and upgrade host packages
sudo apt-get update && sudo apt-get upgrade -y

# 2. Optimize swappiness (Reduce disk IO bottlenecks for SQLite/FAISS caching)
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# 3. Increase maximum open file descriptors (Allows high websocket and HTTP concurrency)
sudo sysctl fs.file-max=2097152
echo 'fs.file-max=2097152' | sudo tee -a /etc/sysctl.conf

# 4. Apply sysctl changes immediately
sudo sysctl -p

# 5. Apply limits to /etc/security/limits.conf
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf
```

---

## 4. Install Docker & Compose Plugin

If the host VM does not have Docker and Compose installed, set it up:

```bash
# 1. Install dependencies
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# 2. Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 3. Setup repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. Add user to docker group (removes sudo requirement for docker commands)
sudo usermod -aG docker $USER
```
*Note: Run `newgrp docker` or log out and log back in to apply group changes.*

---

## 5. Host-Level Nginx Reverse Proxy Setup

Since the VM is already running a central Nginx instance (used by Niyantran), you can merge the following virtual host configuration into the host's `/etc/nginx/sites-available/` Nginx configuration file for the domain `uni-guru.in`:

```nginx
# Upstream definitions matching VM host ports
upstream uniguru_api {
    server 127.0.0.1:8000;
    keepalive 64;
}

upstream uniguru_bridge {
    server 127.0.0.1:8002;
    keepalive 64;
}

upstream uniguru_frontend {
    server 127.0.0.1:3005;
    keepalive 64;
}

# Rate limit request zone
limit_req_zone $binary_remote_addr zone=uniguru_api_limit:10m rate=30r/s;

# HTTPS secure ingress gateway
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name uni-guru.in www.uni-guru.in;

    ssl_certificate /etc/letsencrypt/live/uni-guru.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/uni-guru.in/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Python Bridge Endpoint: exact match /chat
    location = /chat {
        proxy_pass http://uniguru_bridge;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API Endpoints
    location ~ ^/(ask|voice|health|ready|metrics|monitoring|user|chat|guru|feature) {
        limit_req zone=uniguru_api_limit burst=50 nodelay;
        proxy_pass http://uniguru_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
    }

    # React Frontend fallback (served by Node serve)
    location / {
        proxy_pass http://uniguru_frontend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 6. Launching the Production Stack

### 6A. Automated Path (Recommended)
Commit and push to the `main` branch to trigger the GitHub Actions workflow (`.github/workflows/cicd.yml`). The workflow will automatically:
1. Validate compose templates.
2. Build multi-stage Docker images (`bhiv/uniguru-api`, `bhiv/uniguru-bridge`, `bhiv/uniguru-frontend`).
3. Deploy images to the remote VM over SSH.
4. Verify endpoints on ports `8000` (api), `8002` (bridge), and `3005` (frontend).
5. Record release state or roll back automatically if services fail health checks.

### 6B. Manual Path (Optional)
If you need to deploy the stack manually on the VM:
```bash
cd ~/UNIGURU

# 1. Substitute the image tag in the compose file
sed "s|IMG_TAG|latest|g" docker-compose.production.template.yml > docker-compose.production.yml

# 2. Start the services
docker compose -f docker-compose.production.yml up -d

# 3. Check statuses
docker compose -f docker-compose.production.yml ps
```

---

## 7. Verification Plan & Runtime Tests

Verify the health parameters of all running service containers:

```bash
# 1. Check container run statuses
docker compose -f docker-compose.production.yml ps

# 2. Test FastAPI Backend (Port 8000)
curl -sf http://localhost:8000/health

# 3. Test Bridge Server (Port 8002)
curl -sf http://localhost:8002/health

# 4. Test Frontend Server (Port 3005)
curl -sI http://localhost:3005
```
