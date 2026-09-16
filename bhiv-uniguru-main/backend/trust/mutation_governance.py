import hashlib
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class MutationAuditLog:
    mutation_id: str
    target_entity: str
    previous_state_hash: str
    new_state_hash: str
    authorization_signature: str
    timestamp: float
    lineage_parent_id: Optional[str]

class MutationGovernanceEngine:
    def __init__(self):
        self.mutation_logs: Dict[str, MutationAuditLog] = {}
        self.lineage_heads: Dict[str, str] = {} # target_entity -> last_mutation_id
        
    def _hash_state(self, state: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
        
    def _generate_signature(self, entity: str, prev_hash: str, new_hash: str) -> str:
        # In a real system, this would involve cryptographic signing with a private key.
        # For now, we simulate an authorized signature deterministically.
        payload = f"{entity}::{prev_hash}::{new_hash}::AUTHORIZED_GOVERNANCE"
        return hashlib.sha256(payload.encode()).hexdigest()

    def request_mutation(self, entity: str, previous_state: Dict[str, Any], new_state: Dict[str, Any]) -> MutationAuditLog:
        prev_hash = self._hash_state(previous_state)
        new_hash = self._hash_state(new_state)
        
        # Lineage continuity enforcement
        if entity in self.lineage_heads:
            last_mutation = self.mutation_logs[self.lineage_heads[entity]]
            if last_mutation.new_state_hash != prev_hash:
                raise ValueError("Unauthorized mutation detected: Lineage discontinuity. Previous state does not match last known state.")
                
        auth_sig = self._generate_signature(entity, prev_hash, new_hash)
        mutation_id = hashlib.sha256(f"{entity}_{time.time()}_{new_hash}".encode()).hexdigest()
        
        log = MutationAuditLog(
            mutation_id=mutation_id,
            target_entity=entity,
            previous_state_hash=prev_hash,
            new_state_hash=new_hash,
            authorization_signature=auth_sig,
            timestamp=time.time(),
            lineage_parent_id=self.lineage_heads.get(entity)
        )
        
        self.mutation_logs[mutation_id] = log
        self.lineage_heads[entity] = mutation_id
        
        return log

    def verify_mutation_authorization(self, mutation_id: str) -> bool:
        if mutation_id not in self.mutation_logs:
            return False
        log = self.mutation_logs[mutation_id]
        expected_sig = self._generate_signature(log.target_entity, log.previous_state_hash, log.new_state_hash)
        return log.authorization_signature == expected_sig

    def get_mutation_lineage(self, entity: str) -> List[MutationAuditLog]:
        lineage = []
        if entity not in self.lineage_heads:
            return lineage
            
        current_id = self.lineage_heads[entity]
        while current_id:
            log = self.mutation_logs[current_id]
            lineage.append(log)
            current_id = log.lineage_parent_id
            
        return lineage[::-1] # return oldest to newest
