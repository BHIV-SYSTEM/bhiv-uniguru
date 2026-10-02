import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from .replay_integrity import ReplayIntegrityLayer
    from .mutation_governance import MutationGovernanceEngine
    from .rollback_authenticity import RollbackAuthenticityLayer
    from .contradiction_security import ContradictionGovernanceLayer
    from .downstream_trust import DownstreamTrustGateway
except Exception:
    from replay_integrity import ReplayIntegrityLayer
    from mutation_governance import MutationGovernanceEngine
    from rollback_authenticity import RollbackAuthenticityLayer
    from contradiction_security import ContradictionGovernanceLayer
    from downstream_trust import DownstreamTrustGateway

def run_tests():
    print("=== INITIALIZING SEMANTIC TRUST LAYER ===")
    replay_layer = ReplayIntegrityLayer()
    mutation_engine = MutationGovernanceEngine()
    rollback_layer = RollbackAuthenticityLayer(replay_layer)
    contradiction_layer = ContradictionGovernanceLayer()
    downstream_gateway = DownstreamTrustGateway(replay_layer)

    # 1. Replay Integrity Testing
    print("\n[PHASE 1] Replay Integrity Layer Testing")
    state_1 = {"concept": "Quantum Gravity", "confidence": 0.85}
    checkpoint_1 = replay_layer.create_checkpoint(state_1, ["ingest_paper_1"])
    state_2 = {"concept": "Quantum Gravity", "confidence": 0.92, "connections": ["String Theory"]}
    checkpoint_2 = replay_layer.create_checkpoint(state_2, ["ingest_paper_2"])

    is_continuous = replay_layer.verify_replay_continuity(checkpoint_2.checkpoint_id)
    is_authentic = replay_layer.verify_semantic_authenticity(checkpoint_2.checkpoint_id, state_2)
    print(f"Replay Continuity Valid: {is_continuous}")
    print(f"Semantic Authenticity Valid: {is_authentic}")

    # 2. Mutation Governance Testing
    print("\n[PHASE 2] Semantic Mutation Governance Hardening Testing")
    try:
        mutation_1 = mutation_engine.request_mutation("Quantum Gravity", state_1, state_2)
        print(f"Mutation 1 Authorized. Signature: {mutation_1.authorization_signature}")
        
        # Test Lineage Discontinuity (Unauthorized mutation attempt)
        bad_state = {"concept": "Quantum Gravity", "confidence": 0.10}
        mutation_engine.request_mutation("Quantum Gravity", state_1, bad_state) # Should fail, previous was state_2
    except Exception as e:
        print(f"Caught Expected Unauthorized Mutation: {e}")

    # 3. Rollback Authenticity Testing
    print("\n[PHASE 3] Rollback Authenticity + State Recovery Security Testing")
    try:
        # Valid Rollback to state_1
        rollback_proof = rollback_layer.execute_rollback(checkpoint_1.checkpoint_id, state_1)
        print(f"Valid Rollback Proof Generated. ID: {rollback_proof.rollback_id}")
        
        # Tampered Rollback attempt
        rollback_layer.execute_rollback(checkpoint_1.checkpoint_id, state_2) # Should fail
    except Exception as e:
        print(f"Caught Expected State Recovery Trust Failure: {e}")

    # 4. Contradiction Governance Testing
    print("\n[PHASE 4] Contradiction Governance Security Testing")
    conflict_1 = {"concept": "Light", "property": "Wave"}
    conflict_2 = {"concept": "Light", "property": "Particle"}
    trace = contradiction_layer.log_contradiction("Light", [conflict_1, conflict_2], "HUMAN_REVIEW")
    print(f"Contradiction Logged. Tamper Seal: {trace.tamper_seal}")
    
    resolved_state = {"concept": "Light", "property": "Wave-Particle Duality"}
    resolved_trace = contradiction_layer.resolve_contradiction(trace.trace_id, resolved_state)
    print(f"Contradiction Resolved. New Tamper Seal: {resolved_trace.tamper_seal}")
    
    # Tampering test: Manually alter trace and verify
    tampered_trace_id = trace.trace_id
    contradiction_layer.audit_traces[tampered_trace_id].escalation_pathway = "AI_AUTO_RESOLVE"
    is_tampered = not contradiction_layer.verify_contradiction_tampering(tampered_trace_id)
    print(f"Contradiction Tampering Detected: {is_tampered}")

    # 5. Downstream Semantic Trust Testing
    print("\n[PHASE 5] Downstream Semantic Trust Enforcement Testing")
    contract = downstream_gateway.register_contract("AnalyticsEngine", required_trust_level=0.90)
    
    try:
        # Successful propagation
        proof = downstream_gateway.propagate_semantic_payload(contract.contract_id, state_2, 0.95, checkpoint_2.checkpoint_id)
        print(f"Downstream Propagation Successful. Proof Integrity Header: {proof.integrity_header}")
        
        # Failed propagation due to trust level
        downstream_gateway.propagate_semantic_payload(contract.contract_id, state_1, 0.85, checkpoint_1.checkpoint_id)
    except Exception as e:
        print(f"Caught Expected Downstream Trust Failure: {e}")

    print("\n=== WRITING OUTPUT LOGS AND PROOFS ===")
    with open("replay_integrity_logs.json", "w") as f:
        json.dump({k: vars(v) for k, v in replay_layer.checkpoints.items()}, f, indent=2)
    with open("mutation_verification_proofs.json", "w") as f:
        json.dump({k: vars(v) for k, v in mutation_engine.mutation_logs.items()}, f, indent=2)
    with open("rollback_authenticity_outputs.json", "w") as f:
        json.dump({k: vars(v) for k, v in rollback_layer.rollback_proofs.items()}, f, indent=2)
    with open("contradiction_audit_logs.json", "w") as f:
        json.dump({k: vars(v) for k, v in contradiction_layer.audit_traces.items()}, f, indent=2)
    with open("downstream_trust_validation_outputs.json", "w") as f:
        json.dump({k: vars(v) for k, v in downstream_gateway.execution_proofs.items()}, f, indent=2)
    print("Logs written successfully.")

if __name__ == "__main__":
    run_tests()