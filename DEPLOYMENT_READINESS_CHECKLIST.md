# UniGuru Deployment Readiness Checklist

Use this checklist for each deployment. A checked box means an operator verified it for that deployment and attached dated evidence; repository configuration alone is not proof.

## Pre-deployment

- [ ] MDU credential rotated/revoked by provider (required before deployment because a credential-like value exists in Git history)
- [ ] Replacement MDU secret supplied through the external secret store if live MDU validation is required (`MDU_ENABLED=true`)
- [ ] Supabase production credentials available in the external secret store
- [ ] API authentication secrets available in the external secret store
- [ ] Docker build context excludes local environment/secret files
- [ ] Production CORS origin configured to the intended frontend URL
- [ ] Production demo authentication explicitly disabled
- [ ] Persistent disk/storage configured for `/var/lib/uniguru`
- [ ] Production LLM/dependency configuration reviewed; no loopback or demo fallback is being mistaken for a live dependency
- [ ] Secret scan completed; values are not recorded in this checklist

## Deployment

- [ ] Render deployment created
- [ ] Build succeeds
- [ ] Startup succeeds
- [ ] Runtime API is mounted under `/v2` in the deployed container
- [ ] `/health` passes
- [ ] `/ready` passes and its checks are appropriate for the intended production dependencies
- [ ] Frontend loads
- [ ] API reachable from the frontend

## Live acceptance

- [ ] Valid login
- [ ] Invalid login denied
- [ ] Real query
- [ ] Persisted chat
- [ ] Restart persistence
- [ ] Cross-user isolation
- [ ] Failure/retry tests
- [ ] Representative data
- [ ] Customer B deployment
- [ ] Evidence recording
- [ ] Peer 1 witness
- [ ] Peer 2 witness

## Current status (2026-10-06)

All boxes remain unchecked. Provider rotation/revocation, deployment credentials, Render/Supabase access, deployment evidence, browser evidence, Customer B evidence, and peer witnesses have not been supplied. Do not use this file as evidence that deployment or acceptance has occurred.
