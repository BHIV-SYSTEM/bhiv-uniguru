from pathlib import Path

_BACKEND_RETRIEVAL_DIR = Path(__file__).resolve().parent.parent / "backend" / "retrieval"
if str(_BACKEND_RETRIEVAL_DIR) not in __path__:
    __path__.append(str(_BACKEND_RETRIEVAL_DIR))

from .masterdb_retriever import generate_retrieval_artifact, retrieve_from_masterdb

__all__ = ["generate_retrieval_artifact", "retrieve_from_masterdb"]
