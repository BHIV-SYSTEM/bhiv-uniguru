# UniGuru Backend Run Report

## Canonical startup command

From the repository root, the backend should be started with:

```powershell
python backend/main.py
```

The repository launcher script at [run/run_backend.sh](run/run_backend.sh) uses the same entrypoint and exports the project paths needed for import resolution.

## What I verified

- The backend now starts successfully from the repository root.
- The health and readiness endpoints respond successfully over HTTP.
- The Swagger docs endpoint returns HTTP 200.
- Relevant regression tests for the import-path fix and Sanskrit decoder integration pass.

## Root cause and fix

The startup failure was caused by Python import-path precedence between the repository root and the backend package root.

### Fixes applied
- Updated [backend/main.py](backend/main.py) to configure the Python path so the backend entrypoint resolves imports consistently.
- Updated [run/run_backend.sh](run/run_backend.sh) to export the repository root before the backend root in `PYTHONPATH`.
- Added a compatibility shim in [retrieval/__init__.py](retrieval/__init__.py) so the repo-level retrieval package exposes the backend retrieval modules expected by the service stack.
- Added regression coverage in [backend/tests/test_import_path_precedence.py](backend/tests/test_import_path_precedence.py).

## Modified files
- [backend/main.py](backend/main.py)
- [run/run_backend.sh](run/run_backend.sh)
- [retrieval/__init__.py](retrieval/__init__.py)
- [backend/tests/test_import_path_precedence.py](backend/tests/test_import_path_precedence.py)

## Startup evidence

Command used:

```powershell
python backend/main.py
```

Observed startup behavior:

```text
INFO:     Started server process [xxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Endpoint verification

### Health

```json
{"status":"ok","service":"uniguru-live-reasoning","version":"1.1.0"}
```

### Readiness

```json
{"status":"ready","service":"uniguru-live-reasoning","checks":{"system_running":true,"kb_loaded":true,"router_active":true,"llm_status":"available"}}
```

### Docs

```text
HTTP/1.1 200 OK
```

## Test evidence

Ran:

```powershell
python -m pytest backend/tests/test_sanskrit_decoder.py backend/tests/test_import_path_precedence.py -q
```

Observed result:

```text
........
```

That corresponds to 8 passing tests for the relevant regression and integration coverage.
