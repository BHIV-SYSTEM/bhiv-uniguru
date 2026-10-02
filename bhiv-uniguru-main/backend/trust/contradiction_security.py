import hashlib
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class ContradictionAuditTrace:
    trace_id: str
    semantic_entity: str
    conflicting_states: List[str] # List of hashes
    resolution_state_hash: Optional[str]
    escalation_pathway: str
    tamper_seal: str
    timestamp: float
    parent_trace_id: Optional[str]

class ContradictionGovernanceLayer:
    def __init__(self):
        self.audit_traces: Dict[str, ContradictionAuditTrace] = {}
        self.entity_trace_heads: Dict[str, str] = {}
        
    def _hash_state(self, state: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()

    def _generate_tamper_seal(self, entity: str, conflicts: List[str], resolution: Optional[str], pathway: str, parent: Optional[str]) -> str:
        payload = f"{entity}::{','.join(conflicts)}::{resolution}::{pathway}::{parent}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def log_contradiction(self, entity: str, conflicting_states: List[Dict[str, Any]], escalation_pathway: str) -> ContradictionAuditTrace:
        conflict_hashes = [self._hash_state(s) for s in conflicting_states]
        parent_id = self.entity_trace_heads.get(entity)
        
        tamper_seal = self._generate_tamper_seal(entity, conflict_hashes, None, escalation_pathway, parent_id)
        trace_id = hashlib.sha256(f"contradiction_{time.time()}_{tamper_seal}".encode()).hexdigest()
        
        trace = ContradictionAuditTrace(
            trace_id=trace_id,
            semantic_entity=entity,
            conflicting_states=conflict_hashes,
            resolution_state_hash=None,
            escalation_pathway=escalation_pathway,
            tamper_seal=tamper_seal,
            timestamp=time.time(),
            parent_trace_id=parent_id
        )
        
        self.audit_traces[trace_id] = trace
        self.entity_trace_heads[entity] = trace_id
        return trace

    def resolve_contradiction(self, trace_id: str, resolved_state: Dict[str, Any]) -> ContradictionAuditTrace:
        if trace_id not in self.audit_traces:
            raise ValueError("Contradiction trace not found.")
            
        trace = self.audit_traces[trace_id]
        if trace.resolution_state_hash is not None:
            raise ValueError("Contradiction already resolved.")
            
        resolution_hash = self._hash_state(resolved_state)
        
        # Tampering detection check before resolving
        expected_seal = self._generate_tamper_seal(trace.semantic_entity, trace.conflicting_states, None, trace.escalation_pathway, trace.parent_trace_id)
        if expected_seal != trace.tamper_seal:
            raise ValueError("Contradiction Tampering Detected: Audit trace seal is invalid.")
            
        # Update seal with resolution
        new_seal = self._generate_tamper_seal(trace.semantic_entity, trace.conflicting_states, resolution_hash, trace.escalation_pathway, trace.parent_trace_id)
        trace.resolution_state_hash = resolution_hash
        trace.tamper_seal = new_seal
        
        return trace

    def verify_contradiction_tampering(self, trace_id: str) -> bool:
        if trace_id not in self.audit_traces:
            return False
        trace = self.audit_traces[trace_id]
        expected_seal = self._generate_tamper_seal(
            trace.semantic_entity, 
            trace.conflicting_states, 
            trace.resolution_state_hash, 
            trace.escalation_pathway, 
            trace.parent_trace_id
        )
        return expected_seal == trace.tamper_seal

    def get_contradiction_lineage(self, entity: str) -> List[ContradictionAuditTrace]:
        lineage = []
        current_id = self.entity_trace_heads.get(entity)
        while current_id:
            trace = self.audit_traces[current_id]
            lineage.append(trace)
            current_id = trace.parent_trace_id
        return lineage[::-1]
