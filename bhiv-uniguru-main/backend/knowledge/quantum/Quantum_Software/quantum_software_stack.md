Title: Quantum Software Stack
Source(s): 
• Qiskit documentation (IBM Quantum)
• Cirq documentation (Google Quantum AI)
• PennyLane documentation (Xanadu)
• Häner et al. (2018) Software methodology for compiling quantum programs.

Authors: Curated summary
Year: 2026 (ingestion)
Domain: Quantum Software / Tooling
Ingestion date: 2026-02-06

Definitions
- Quantum SDK: Software development kit providing abstractions to build, transpile, and run quantum circuits.
- Compiler/transpiler: Transforms logical circuits into hardware-native instructions respecting connectivity and gate sets.
- Simulator: Classical emulation of quantum circuits for testing and benchmarking.

Key Points
- Stack layers: Algorithms → Circuit design → Compilation/transpilation → Pulse/control → Hardware.
- Tooling considerations: Noise-aware compilation, error mitigation, profiling, and benchmarking.
- Hybrid workflows: Classical optimizers interacting with parameterized quantum circuits.

Concept explanations
- Transpilation: Mapping logical gates to native gate set and qubit topology with resource-aware optimizations.
- Error mitigation: Techniques (zero-noise extrapolation, probabilistic error cancellation) to improve results on noisy hardware.

Light equation context
- Circuit fidelity estimation: Model combining gate error rates and decoherence to predict output quality.

Citations
- SDK and compiler literature; peer-reviewed papers on compilation and error mitigation.
