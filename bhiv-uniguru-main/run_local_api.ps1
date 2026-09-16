$env:PYTHONPATH = ".;backend"
$env:UNIGURU_HOST = "127.0.0.1"
$env:UNIGURU_PORT = "8010"
$env:EXTERNAL_API_SECRET_KEY = "uniguru_secret_123"
$env:UNIGURU_API_AUTH_REQUIRED = "false"
$env:UNIGURU_ALLOWED_CALLERS = "*"

python -m uvicorn service.api:app --host 127.0.0.1 --port 8010
