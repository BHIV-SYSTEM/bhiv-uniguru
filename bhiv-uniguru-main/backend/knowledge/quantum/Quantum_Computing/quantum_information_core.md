Title: Quantum Information Core
Source(s): Source(s):
• Nielsen & Chuang (2010)
• Preskill Lecture Notes – Quantum Computation (Caltech)
• Bennett et al. (1993) Teleporting an unknown quantum state.
• Shor (1995) Scheme for reducing decoherence in quantum memory.

Authors: Curated summary
Year: 2026 (ingestion)
Domain: Quantum Information Theory
Ingestion date: 2026-02-06

Definitions
- Von Neumann entropy: $S(\rho)=-\mathrm{Tr}(\rho \log \rho)$ measuring quantum uncertainty.
- Mutual information: $I(A:B)=S(\rho_A)+S(\rho_B)-S(\rho_{AB})$.
- Holevo bound: Limits accessible classical information from quantum states.
- No-cloning theorem: Unknown quantum states cannot be copied exactly.

Key Points
- Entropy and information measures generalize classical definitions to quantum ensembles.
- Quantum channels: Completely positive trace-preserving (CPTP) maps model noise and communication.
- Entanglement measures: Concurrence, entanglement entropy, and operational tasks (teleportation, dense coding).

Concept explanations
- Quantum communication: Uses entanglement and quantum channels for tasks like teleportation and QKD.
- Error correction: Quantum error-correcting codes protect logical qubits via redundancy and syndrome measurement.

Light equation context
- Channel action: $\rho\mapsto\sum_k E_k\rho E_k^{\dagger}$ with $\sum_k E_k^{\dagger}E_k=I$ for CPTP maps.
Quantum Teleportation
Quantum teleportation enables transfer of an unknown quantum state using entanglement and classical communication.
Protocol components:
• Shared Bell pair
• Bell-basis measurement
• Classical communication of 2 bits
• Conditional Pauli corrections

Quantum Error Correction
Quantum error correction protects logical qubits from decoherence.
Core principles:
• Redundancy via encoding
• Syndrome measurement without collapsing logical state
• Fault-tolerant operations

Examples:
• Shor code
• Steane code
• Surface code


Citations
- Nielsen & Chuang (2010); Preskill lecture notes (quantum information sections); peer-reviewed sources on specific topics.

