# PRODUCTION_RUNBOOK

## Service Management

### Start Service
```bash
docker compose up -d
```

### Stop Service
```bash
docker compose down
```

### Restart Service (with rebuild)
```bash
docker compose up -d --build --force-recreate
```

## Monitoring & Logs

### View Logs
```bash
# Nginx access logs
docker compose logs -f nginx

# UniGuru application logs
docker compose logs -f uniguru-service
```

### Check Health
```bash
curl https://uni-guru.in/health
```

## Maintenance

### Certificate Renewal
The certbot container runs a renewal check every 12 hours. Manually renew:
```bash
./deploy/certbot/renew.sh
```

### Rotating API Tokens
1. Update `UNIGURU_API_TOKEN` in `.env.production`.
2. Add old token to `UNIGURU_API_TOKENS` (comma separated) to prevent service disruption.
3. Reload service: `docker compose up -d`

## Troubleshooting

### Error 401 Unauthorized
- Verify `Authorization: Bearer <token>` header.
- Ensure token matches either primary or rotation tokens in env.

### Error 403 Forbidden
- Verify `context.caller` or `X-Caller-Name` is one of: `bhiv-assistant`, `gurukul-platform`, `internal-testing`.

### High Latency
- Check upstream worker load: `docker stats uniguru-service`.
- Verify Nginx rate limits are not being hit.
