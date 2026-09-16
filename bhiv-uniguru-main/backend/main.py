from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent


def _configure_python_path() -> None:
    resolved_backend = BACKEND_DIR.resolve()
    resolved_root = ROOT_DIR.resolve()
    ordered_entries = [str(resolved_root), str(resolved_backend)]

    for entry in sys.path:
        if not entry:
            continue
        resolved_entry = Path(entry).resolve() if Path(entry).exists() else Path(entry)
        if resolved_entry in {resolved_backend, resolved_root}:
            continue
        ordered_entries.append(entry)

    sys.path[:] = ordered_entries


_configure_python_path()


def main() -> None:
    # Load .env file from backend directory
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment from: {env_path}")

    # Mount the ecosystem/sanskrit runtime API under /v2
    from service.api import app
    from service.uniguru_runtime_api import app as runtime_app
    app.mount("/v2", runtime_app)

    host = os.getenv("UNIGURU_HOST", "0.0.0.0")
    port = int(os.getenv("UNIGURU_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, workers=1)


if __name__ == "__main__":
    main()
