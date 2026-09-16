import hashlib
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
try:
    from .replay_integrity import ReplayIntegrityLayer
except ImportError:
    from replay_integrity import ReplayIntegrityLayer

@dataclass
class TrustContract:
    contract_id: str
    consumer_identity: str
    required_trust_level: float
    enforce_replay_safety: bool

@dataclass
class DownstreamExecutionProof:
    proof_id: str
    contract_id: str
    payload_hash: str
    integrity_header: str
    timestamp: float
    replay_checkpoint_id: Optional[str]

class DownstreamTrustGateway:
    def __init__(self, replay_layer: ReplayIntegrityLayer):
        self.replay_layer = replay_layer
        self.contracts: Dict[str, TrustContract] = {}
        self.execution_proofs: Dict[str, DownstreamExecutionProof] = {}

    def register_contract(self, consumer_identity: str, required_trust_level: float, enforce_replay_safety: bool = True) -> TrustContract:
        contract_id = hashlib.sha256(f"contract_{consumer_identity}_{time.time()}".encode()).hexdigest()
        contract = TrustContract(
            contract_id=contract_id,
            consumer_identity=consumer_identity,
            required_trust_level=required_trust_level,
            enforce_replay_safety=enforce_replay_safety
        )
        self.contracts[contract_id] = contract
        return contract

    def _generate_integrity_header(self, contract_id: str, payload_hash: str, checkpoint_id: Optional[str]) -> str:
        header_content = f"{contract_id}::{payload_hash}::{checkpoint_id}::TRUST_VERIFIED"
        return hashlib.sha256(header_content.encode()).hexdigest()

    def propagate_semantic_payload(self, contract_id: str, semantic_payload: Dict[str, Any], trust_level: float, replay_checkpoint_id: Optional[str] = None) -> DownstreamExecutionProof:
        if contract_id not in self.contracts:
            raise ValueError("Trust Contract not found.")
            
        contract = self.contracts[contract_id]
        
        # 1. Trust Propagation Validation
        if trust_level < contract.required_trust_level:
            raise ValueError(f"Trust Propagation Failure: Semantic trust level {trust_level} is below required {contract.required_trust_level}.")
            
        # 2. Replay-Safe Downstream Execution Validation
        if contract.enforce_replay_safety:
            if not replay_checkpoint_id:
                raise ValueError("Replay Safety Enforcement Failure: Replay checkpoint ID is required.")
            if not self.replay_layer.verify_replay_continuity(replay_checkpoint_id):
                raise ValueError("Replay Safety Enforcement Failure: Invalid replay continuity.")
            if not self.replay_layer.verify_semantic_authenticity(replay_checkpoint_id, semantic_payload):
                raise ValueError("Replay Safety Enforcement Failure: Semantic payload does not match replay checkpoint authenticity.")

        # 3. Semantic Payload Verification & Integrity Headers
        payload_hash = self.replay_layer._generate_hash(semantic_payload)
        integrity_header = self._generate_integrity_header(contract_id, payload_hash, replay_checkpoint_id)
        
        proof_id = hashlib.sha256(f"proof_{time.time()}_{integrity_header}".encode()).hexdigest()
        
        proof = DownstreamExecutionProof(
            proof_id=proof_id,
            contract_id=contract_id,
            payload_hash=payload_hash,
            integrity_header=integrity_header,
            timestamp=time.time(),
            replay_checkpoint_id=replay_checkpoint_id
        )
        
        self.execution_proofs[proof_id] = proof
        return proof

    def verify_downstream_proof(self, proof_id: str) -> bool:
        if proof_id not in self.execution_proofs:
            return False
        proof = self.execution_proofs[proof_id]
        expected_header = self._generate_integrity_header(proof.contract_id, proof.payload_hash, proof.replay_checkpoint_id)
        return expected_header == proof.integrity_header
