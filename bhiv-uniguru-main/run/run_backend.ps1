$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not $env:PYTHONPATH) {
  $env:PYTHONPATH = "$RootDir\backend"
} else {
  $env:PYTHONPATH = "$RootDir\backend;$env:PYTHONPATH"
}
if (-not $env:UNIGURU_HOST) { $env:UNIGURU_HOST = "127.0.0.1" }
if (-not $env:UNIGURU_PORT) { $env:UNIGURU_PORT = "8000" }
if (-not $env:UNIGURU_API_AUTH_REQUIRED) { $env:UNIGURU_API_AUTH_REQUIRED = "false" }
if (-not $env:UNIGURU_LLM_URL) { $env:UNIGURU_LLM_URL = "internal://demo-llm" }

python "$RootDir\backend\main.py"
