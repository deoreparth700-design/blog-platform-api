# Deployment Guide — Blog Platform API

This guide provides step-by-step instructions for deploying the **Blog Platform API** to **Render** as a deployment-ready Python Web Service.

---

## Architecture Overview

- **Web Service Framework**: FastAPI (ASGI)
- **ASGI Server**: Uvicorn bound to `0.0.0.0:$PORT`
- **Hosting Platform**: Render (Web Service / Blueprint)
- **Primary Database**: Neon Serverless PostgreSQL
- **Caching Layer**: Upstash Serverless Redis (REST API)
- **Authentication**: Stateless HMAC-SHA256 JWT tokens

> [!IMPORTANT]
> - `.env` is strictly for local development and is git-ignored.
> - **Never commit secrets** (JWT secrets, PostgreSQL connection strings, Redis tokens) into source control.
> - Neon remains the authoritative source of truth database.
> - Upstash Redis operates as an optional, graceful cache-aside layer.

---

## 1. Prerequisites

Before deploying, ensure you have:
1. A [GitHub](https://github.com) account containing this repository.
2. A [Render](https://render.com) account.
3. A running [Neon PostgreSQL](https://neon.tech) database instance with tables initialized (`scripts/init_db.py`).
4. An [Upstash Redis](https://upstash.com) database with REST API credentials.
5. A strong secret key string for JWT verification (`JWT_ACCESS_SECRET`).

---

## 2. Deployment via Render Blueprint (Recommended)

This repository includes a pre-configured [`render.yaml`](render.yaml) specification:

```yaml
services:
  - type: web
    name: blog-platform-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn src.app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: JWT_ACCESS_SECRET
        sync: false
      - key: UPSTASH_REDIS_REST_URL
        sync: false
      - key: UPSTASH_REDIS_REST_TOKEN
        sync: false
```

### Steps:
1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** &rarr; **Blueprint**.
3. Select and connect your `blog-platform-api` repository.
4. Render will parse `render.yaml` and prompt you to input values for the four unsynced environment variables:
   - `DATABASE_URL`: Your full Neon PostgreSQL connection string (including `sslmode=require`).
   - `JWT_ACCESS_SECRET`: A secure 32+ character random secret string.
   - `UPSTASH_REDIS_REST_URL`: Upstash REST endpoint URL (e.g. `https://xxx.upstash.io`).
   - `UPSTASH_REDIS_REST_TOKEN`: Upstash REST authentication token.
5. Click **Apply** to deploy the service.

---

## 3. Manual Deployment Setup on Render

If you prefer deploying manually without Blueprint:
1. In the Render Dashboard, click **New +** &rarr; **Web Service**.
2. Connect your Git repository.
3. Configure the service settings:
   - **Name**: `blog-platform-api`
   - **Region**: Select the region closest to your Neon PostgreSQL and Upstash databases (e.g., `Oregon (US West)` or `Frankfurt (EU Central)`).
   - **Branch**: `master` (or `main`)
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.app:app --host 0.0.0.0 --port $PORT`
4. In the **Environment Variables** section, add the four required variables:
   - `DATABASE_URL`
   - `JWT_ACCESS_SECRET`
   - `UPSTASH_REDIS_REST_URL`
   - `UPSTASH_REDIS_REST_TOKEN`
5. Click **Create Web Service**.

---

## 4. Post-Deployment Verification

Once Render displays **Service is live**, perform verification using curl, HTTPie, or your browser.

Replace `https://your-service.onrender.com` with your assigned Render URL.

### 4.1 Health Check
Verify application uptime and routing:
```bash
curl -i https://your-service.onrender.com/health
```
**Expected Response (200 OK)**:
```json
{
  "status": "ok",
  "message": "Blog Platform API is running"
}
```

### 4.2 Interactive API Documentation (Swagger)
Open in your browser:
```text
https://your-service.onrender.com/docs
```
Confirm all routes (`/api/posts/`, `/api/posts/{id}`, `/api/posts/{id}/comments`, `/api/posts/{id}/likes`, etc.) are visible and interactive.

### 4.3 Public Endpoint & Cache-Aside Verification
Make a request to the paginated posts endpoint:
```bash
curl -i https://your-service.onrender.com/api/posts/?page=1&limit=10
```
- **First request**: Check headers for `X-Cache: MISS`.
- **Immediate repeat request**: Check headers for `X-Cache: HIT`.

### 4.4 Authenticated Endpoint Verification
Test an authenticated route using a valid Bearer token signed with the configured `JWT_ACCESS_SECRET`:
```bash
curl -i -H "Authorization: Bearer <YOUR_JWT_TOKEN>" https://your-service.onrender.com/api/auth-test
```
**Expected Response (200 OK)**:
```json
{
  "authenticated": true,
  "userId": "<user-uuid>"
}
```

---

## 5. Application Lifecycle & Hygiene

- **Graceful Shutdown**: The application implements a FastAPI `lifespan` handler that safely releases database connection pool handles (`close_pool()`) and cleans up the Redis client reference on container SIGTERM/SIGINT.
- **Fail-Open Redis Resilience**: If Upstash Redis experiences transient connection delays or quota exhaustion, CacheService logs the issue and falls back to PostgreSQL without interrupting user traffic.
