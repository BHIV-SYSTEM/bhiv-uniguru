$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not $env:NODE_BACKEND_PORT) { $env:NODE_BACKEND_PORT = "8080" }
if (-not $env:UNIGURU_ASK_URL) { $env:UNIGURU_ASK_URL = "http://127.0.0.1:8000/ask" }

Set-Location "$RootDir\node-backend"
npm start
