$env:PYTHONPATH = ".;backend"
$env:UNIGURU_HOST = "127.0.0.1"
$env:UNIGURU_PORT = if ($env:UNIGURU_PORT) { $env:UNIGURU_PORT } else { "8000" }
$env:EXTERNAL_API_SECRET_KEY = "uniguru_secret_123"
$env:UNIGURU_API_AUTH_REQUIRED = "false"
$env:UNIGURU_DEMO_AUTH_ENABLED = "true"
$env:UNIGURU_ALLOWED_CALLERS = "*"

python -m uvicorn service.api:app --host 127.0.0.1 --port $env:UNIGURU_PORT
