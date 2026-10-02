import json
import os
import logging
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
                for filename in os.listdir(source):
                    if filename.endswith(".json"):
                        self._load_file(os.path.join(source, filename))
        logger.info(f"Loaded {len(self.entries)} valid Kosha entries.")
        return self.entries

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
