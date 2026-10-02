# Live Proof Video Script

Date baseline: February 27, 2026  
Workspace: `C:\Users\Yass0\OneDrive\Desktop\TASK14`

## 1) Show production repo is separate and cloned

```powershell
git -C .\Complete-Uniguru remote -v
```

Expected: `origin https://github.com/sharmavijay45/Complete-Uniguru.git`

## 2) Run full live integration demo

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_live_demo.ps1
```

This will:
1. Start production UniGuru backend (`localhost:8000`)
2. Start Bridge (`localhost:8001`)
3. Validate health endpoints
4. Send KB-first query through Bridge
5. Send forwarding/fallback query through Bridge
6. Simulate seal tampering and verify detection
7. Save proof artifacts

## 3) Show generated proof files

```powershell
Get-Content .\demo_logs\live_demo_proof.json
Get-Content .\demo_logs\production.log -Tail 30
Get-Content .\demo_logs\bridge.log -Tail 30
```

## 4) Show mandatory reports

```powershell
Get-Content .\INTEGRATION_PROOF.md
Get-Content .\ENFORCEMENT_SIGNATURE_REPORT.md
Get-Content .\KNOWLEDGE_BASE_EXPANSION_REPORT.md
Get-Content .\WEB_RETRIEVAL_REPORT.md
Get-Content .\FINAL_SYSTEM_VALIDATION.md
```

## 5) Show automated tests

```powershell
python -m pytest -q tests
```

Expected: all tests pass.
