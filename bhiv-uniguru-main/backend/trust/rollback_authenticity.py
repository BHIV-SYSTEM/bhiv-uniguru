import hashlib
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
try:
    from .replay_integrity import ReplayIntegrityLayer, ReplayCheckpoint
except ImportError:
    from replay_integrity import ReplayIntegrityLayer, ReplayCheckpoint

@dataclass
class RollbackProof:
    rollback_id: str
    target_checkpoint_id: str
    restored_state_hash: str
    authenticity_signature: str
    timestamp: float

class RollbackAuthenticityLayer:
    def __init__(self, replay_layer: ReplayIntegrityLayer):
        self.replay_layer = replay_layer
        self.rollback_proofs: Dict[str, RollbackProof] = {}

    def _generate_rollback_signature(self, target_checkpoint_id: str, state_hash: str) -> str:
        payload = f"ROLLBACK_AUTH::{target_checkpoint_id}::{state_hash}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def execute_rollback(self, target_checkpoint_id: str, semantic_state: Dict[str, Any]) -> RollbackProof:
        # 1. State Recovery Trust Enforcement
        if not self.replay_layer.verify_semantic_authenticity(target_checkpoint_id, semantic_state):
            raise ValueError("State Recovery Trust Failure: Restored semantic state does not match the target checkpoint.")

        # 2. Rollback Replay Verification (Lineage check)
        if not self.replay_layer.verify_replay_continuity(target_checkpoint_id):
            raise ValueError("Rollback Replay Verification Failure: Target checkpoint lacks replay continuity.")

        # 3. Rollback Authenticity Validation
        state_hash = self.replay_layer._generate_hash(semantic_state)
        auth_sig = self._generate_rollback_signature(target_checkpoint_id, state_hash)
        
        rollback_id = hashlib.sha256(f"rollback_{time.time()}_{target_checkpoint_id}".encode()).hexdigest()
        
        proof = RollbackProof(
            rollback_id=rollback_id,
            target_checkpoint_id=target_checkpoint_id,
            restored_state_hash=state_hash,
            authenticity_signature=auth_sig,
            timestamp=time.time()
        )
        self.rollback_proofs[rollback_id] = proof
        
        # In a real system, you'd reset the head of the replay layer here
        # self.replay_layer.head_checkpoint_id = target_checkpoint_id
        
        return proof

    def verify_rollback_authenticity(self, rollback_id: str) -> bool:
        if rollback_id not in self.rollback_proofs:
            return False
        proof = self.rollback_proofs[rollback_id]
        expected_sig = self._generate_rollback_signature(proof.target_checkpoint_id, proof.restored_state_hash)
        return expected_sig == proof.authenticity_signature
