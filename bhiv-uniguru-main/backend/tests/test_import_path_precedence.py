from __future__ import annotations

import importlib
import sys
from pathlib import Path


def test_repo_root_retrieval_package_is_importable_before_backend_shadowing():
    repo_root = Path(__file__).resolve().parents[2]
    backend_root = repo_root / "backend"

    import backend.main as backend_main

    backend_main._configure_python_path()

    sys.modules.pop("retrieval", None)
    sys.modules.pop("retrieval.retrieval_engine", None)
    sys.modules.pop("retrieval.retriever", None)

    engine_module = importlib.import_module("retrieval.retrieval_engine")
    retriever_module = importlib.import_module("retrieval.retriever")

    assert engine_module.__file__ is not None
    assert retriever_module.__file__ is not None
    assert Path(engine_module.__file__).resolve().is_relative_to(repo_root.resolve())
    assert not Path(engine_module.__file__).resolve().is_relative_to(backend_root.resolve())
    assert Path(retriever_module.__file__).resolve().is_relative_to(backend_root.resolve())
