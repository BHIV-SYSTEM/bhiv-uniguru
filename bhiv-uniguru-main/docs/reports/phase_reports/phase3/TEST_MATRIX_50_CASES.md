# Retrieval Engine V2: Test Matrix (50 Cases)

## 1. Objective
Verify the deterministic accuracy, recursive depth, and hierarchical fallback of the Retrieval Engine V2 without using embeddings.

## 2. Test Tiers

### A. Direct Keyword Match (Tier 1: Foundations)
| Case | Query | Expected File(s) |
| :--- | :--- | :--- |
| 1 | "Tell me about qubits" | `qubit.md` |
| 2 | "Explain superposition" | `superposition.md` |
| 3 | "What is entanglement?" | `entanglement.md` |
| 4 | "Density matrix explained" | `density_matrix.md` |
| 5 | "Shor's algorithm" | `shor_algorithm.md` |

### B. Recursive Subdirectory Match (Tier 2: Domain)
| Case | Query | Expected File(s) |
| :--- | :--- | :--- |
| 6 | "Quantum hardware overview" | `Quantum_Hardware/quantum_hardware_overview.md` |
| 7 | "Quantum OS details" | `Quantum_Software/quantum_os_and_firmware.md` |
| 8 | "Quantum error correction" | `Quantum_Software/quantum_error_correction.md` |
| 9 | "Quantum algorithms list" | `Quantum_Algorithms/quantum_algorithms_overview.md` |
| 10 | "Quantum chemistry basics" | `Quantum_Chemistry/quantum_chemistry_foundations.md` |

### C. Multi-Keyword Scoring
| Case | Query | Expected Selection Logic |
| :--- | :--- | :--- |
| 11 | "Qubits and superposition" | Both `qubit.md` and `superposition.md` |
| 12 | "Shor and Grover algorithms" | `shor_algorithm.md` and `grover_algorithm.md` |
| 13 | "Quantum computing hardware" | `Quantum_Computing/...` and `Quantum_Hardware/...` |

### D. Hierarchical Fallback
| Case | Query | Expected Result |
| :--- | :--- | :--- |
| 14 | "How does it work?" | No match (Forward to RLM Ambiguity) |
| 15 | "Quantum fundamentals" | `README.md` or `KB_INDEX.md` |

### E. Token Normalization (Adversarial)
| Case | Query | Expected Result |
| :--- | :--- | :--- |
| 16 | "QUBIT!!!!" | `qubit.md` (Punctuation/Case ignored) |
| 17 | "The qubit" | `qubit.md` (Stopword 'The' ignored) |
| 18 | "   Super-position   " | `superposition.md` (Normalization) |

*... (remaining 32 cases to be implemented in the rlm_harness extension) ...*

## 3. Validation Rules
1.  **Selection Equality**: Every run must select the exact same file paths.
2.  **Order Equality**: Selection order must match the score ranking.
3.  **No Hallucinations**: Only files present in the audit index can be returned.
4.  **No Semantic Leaks**: If a word isn't in the filename/index, it shouldn't be "guessed".
