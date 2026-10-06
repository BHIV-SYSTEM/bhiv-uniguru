# UniGuru Deployment Readiness Checklist

Leave an item unchecked until its named verification source has produced evidence for the target deployment.

## PRE-DEPLOYMENT

- [ ] MDU credential rotated/revoked by provider — provider-required
- [ ] Replacement MDU secret supplied externally if required — operator-required; provider-required if live MDU is enabled
- [ ] Supabase production credentials available — operator-required
- [ ] API authentication secrets available — operator-required
- [ ] CORS origin configured — repository-verifiable; operator must confirm the deployed frontend origin
- [ ] production demo auth disabled — repository-verifiable; operator must confirm deployed value
- [ ] persistent disk/storage configured — repository-verifiable; live-infrastructure-required to confirm
- [ ] Production LLM endpoint supplied; Compose and Render must not silently use local/demo defaults — operator-required
- [ ] Docker build context excludes local environment/secret files — repository-verifiable

## DEPLOYMENT

- [ ] Render deployment created — live-infrastructure-required
- [ ] build succeeds — live-infrastructure-required
- [ ] startup succeeds — live-infrastructure-required
- [ ] health passes — live-infrastructure-required
- [ ] readiness passes — live-infrastructure-required
- [ ] frontend loads — live-infrastructure-required
- [ ] API reachable — live-infrastructure-required
- [ ] Runtime API is mounted under `/v2` in the deployed container — repository-verifiable and live-infrastructure-required

## LIVE ACCEPTANCE

- [ ] valid login — live-infrastructure-required
- [ ] invalid login denied — live-infrastructure-required
- [ ] real query — live-infrastructure-required
- [ ] persisted chat — live-infrastructure-required
- [ ] restart persistence — live-infrastructure-required
- [ ] cross-user isolation — live-infrastructure-required
- [ ] failure/retry tests — live-infrastructure-required
- [ ] representative data — operator approval and live-infrastructure-required
- [ ] Customer B deployment — Customer B live-infrastructure-required
- [ ] evidence recording — live-infrastructure-required
- [ ] Peer 1 witness — peer-witness-required
- [ ] Peer 2 witness — peer-witness-required
