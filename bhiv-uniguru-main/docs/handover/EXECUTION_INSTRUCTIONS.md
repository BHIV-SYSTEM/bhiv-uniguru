# Execution Instructions

## Purpose
Exact startup order for Yashika (Integration), Alay (DevOps), and Vinayak (Testing).

## Prerequisites
1. Python environment with backend dependencies.
2. Node environment for `node-backend`.
3. Repo root as current directory.

## Startup Order
1. Backend:
   - Windows: `powershell -ExecutionPolicy Bypass -File run/run_backend.ps1`
   - Linux/macOS: `bash run/run_backend.sh`
2. Node middleware:
   - Windows: `powershell -ExecutionPolicy Bypass -File run/run_node.ps1`
   - Linux/macOS: `bash run/run_node.sh`

## Health Checks
1. Python health: `GET http://127.0.0.1:8000/health`
2. Python ready: `GET http://127.0.0.1:8000/ready`
3. Node health: `GET http://127.0.0.1:8080/health`

## Runtime Validation
1. Standard 5-query check:
   - `python test/run_phase8_validation.py`
2. Failure-injection safety proof:
   - `python test/run_demo_safety_proof.py`

## Expected Artifacts
1. `demo_logs/phase8_test_outputs.json`
2. `demo_logs/demo_safety_proof.json`
3. `docs/reports/DEMO_STABILITY_PROOF.md`
