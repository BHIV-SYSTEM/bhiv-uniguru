import json
import os
import logging
import re
from pathlib import Path
from typing import List, Dict, Any
from .kosha_validator import KoshaEntry

logger = logging.getLogger(__name__)

class KoshaLoader:
    def __init__(self, data_sources: List[str]):
        """
        Initialize with a list of file paths or directories containing Kosha JSON entries.
        """
        self.data_sources = data_sources
        self.entries: List[KoshaEntry] = []

    def load_all(self) -> List[KoshaEntry]:
        self.entries = []
        for source in self.data_sources:
            if os.path.isfile(source) and source.endswith(".json"):
                self._load_file(source)
            elif os.path.isdir(source):
                for filename in sorted(os.listdir(source)):
                    path = os.path.join(source, filename)
                    if filename.endswith(".json"):
                        self._load_file(path)
                    elif filename.endswith(".md"):
                        self._load_markdown(path)
        logger.info(f"Loaded {len(self.entries)} valid Kosha entries.")
        return self.entries

    def _load_markdown(self, filepath: str) -> None:
        """Load an explicitly configured authoritative Markdown source as one record."""
        try:
            path = Path(filepath)
            content = path.read_text(encoding="utf-8")
            content = re.sub(r"\n{3,}", "\n\n", content).strip()
            if len(content) < 10:
                return
            tag = re.sub(r"[^a-z0-9]+", " ", path.stem.casefold()).strip()
            self.entries.append(KoshaEntry(
                knowledge_id=f"KOSHA_sanskrit_{path.stem.casefold()}",
                domain="sanskrit queries",
                content=content,
                source=f"Authoritative Sanskrit knowledge: {path.as_posix()}",
                confidence=0.9,
                timestamp="2026-01-01T00:00:00Z",
                tags=[tag, *tag.split()],
                clean_content=content,
            ))
        except Exception as exc:
            logger.warning("Failed to load Markdown source %s: %s", filepath, exc)

    def _load_file(self, filepath: str):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if isinstance(data, dict):
                # If wrapped in a dictionary, assume it's a single entry or a specific key
                if "entries" in data:
                    data_list = data["entries"]
                else:
                    data_list = [data]
            elif isinstance(data, list):
                data_list = data
            else:
                return
                
            for raw_entry in data_list:
                try:
                    entry = KoshaEntry(**raw_entry)
                    self.entries.append(entry)
                except Exception as e:
                    logger.warning(f"Rejecting entry: Schema validation failed. {e}")
        except Exception as e:
            logger.error(f"Failed to read file {filepath}: {e}")
