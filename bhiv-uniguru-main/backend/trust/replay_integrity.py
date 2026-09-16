import hashlib
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class ReplayCheckpoint:
    checkpoint_id: str
    semantic_hash: str
    timestamp: float
    trace_chain: List[str]
    parent_checkpoint_id: Optional[str]

class ReplayIntegrityLayer:
    def __init__(self):
        self.checkpoints: Dict[str, ReplayCheckpoint] = {}
        self.head_checkpoint_id: Optional[str] = None
        self.genesis_checkpoint_id: Optional[str] = None

    def _generate_hash(self, payload: Any) -> str:
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()

    def create_checkpoint(self, semantic_state: Dict[str, Any], trace_events: List[str]) -> ReplayCheckpoint:
        semantic_hash = self._generate_hash(semantic_state)
        checkpoint_id = self._generate_hash({
            "semantic_hash": semantic_hash,
            "parent": self.head_checkpoint_id,
            "timestamp": time.time()
        })
        
        checkpoint = ReplayCheckpoint(
            checkpoint_id=checkpoint_id,
            semantic_hash=semantic_hash,
            timestamp=time.time(),
            trace_chain=trace_events.copy(),
            parent_checkpoint_id=self.head_checkpoint_id
        )
        
        self.checkpoints[checkpoint_id] = checkpoint
        self.head_checkpoint_id = checkpoint_id
        
        if not self.genesis_checkpoint_id:
            self.genesis_checkpoint_id = checkpoint_id
            
        return checkpoint

    def verify_replay_continuity(self, target_checkpoint_id: str) -> bool:
        if target_checkpoint_id not in self.checkpoints:
            return False
            
        current = self.checkpoints[target_checkpoint_id]
        while current.parent_checkpoint_id:
            if current.parent_checkpoint_id not in self.checkpoints:
                return False
            current = self.checkpoints[current.parent_checkpoint_id]
            
        return current.checkpoint_id == self.genesis_checkpoint_id

    def verify_semantic_authenticity(self, checkpoint_id: str, provided_state: Dict[str, Any]) -> bool:
        if checkpoint_id not in self.checkpoints:
            return False
        expected_hash = self.checkpoints[checkpoint_id].semantic_hash
        actual_hash = self._generate_hash(provided_state)
        return expected_hash == actual_hash

    def get_trace_chain(self, checkpoint_id: str) -> List[str]:
        if checkpoint_id not in self.checkpoints:
            return []
        return self.checkpoints[checkpoint_id].trace_chain
