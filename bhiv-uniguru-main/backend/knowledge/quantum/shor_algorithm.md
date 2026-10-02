Title: Quantum Algorithms Overview
Source(s): 
• Shor, P. W. (1994) Algorithms for quantum computation: discrete logarithms and factoring.
• Grover, L. K. (1996) A fast quantum mechanical algorithm for database search.
• Nielsen & Chuang (2010) Quantum Computation and Quantum Information.
• Farhi et al. (2014) A Quantum Approximate Optimization Algorithm (arXiv:1411.4028).
• Peruzzo et al. (2014) A variational eigenvalue solver on a quantum processor.

Authors: Curated summary
Year: 2026 (ingestion)
Domain: Quantum Algorithms
Ingestion date: 2026-02-06

Definitions
- Quantum algorithm: Algorithm exploiting quantum mechanical phenomena (superposition, interference, entanglement) to solve computational problems.
- Oracle: Abstract subroutine used in many algorithmic formulations (e.g., Grover's search).

Key Points
- Quantum speedups: Proven exponential (Shor) and quadratic (Grover) advantages for specific problems.
- Algorithm classes: Factoring and period-finding, unstructured search, simulation, optimization (VQE, QAOA).
- Resource considerations: Qubit count, gate depth, error rates, and classical-quantum hybrid steps.

Concept explanations
- Shor's algorithm: Period-finding with quantum Fourier transform yields integer factoring speedup (cite Shor 1994).
- Grover's search: Amplitude amplification producing $O(\sqrt{N})$ queries for unstructured search.
- Quantum simulation: Using quantum systems to simulate quantum chemistry and materials; basis for many near-term use cases.
- Variational algorithms: Hybrid quantum-classical optimization using parameterized circuits (VQE, QAOA) for noisy hardware.

Light equation context
- Grover iteration amplitude scaling: After $k$ iterations, success amplitude scales approximately as $\sin((2k+1)\theta)$ where $\sin(\theta)=1/\sqrt{N}$.
- Quantum Fourier Transform (QFT): Linear transform mapping computational basis to frequency domain; implemented with $O(n^2)$ gates in textbook circuits.

Title: Quantum Algorithms Overview
Source(s): 
• Shor, P. W. (1994) Algorithms for quantum computation: discrete logarithms and factoring.
• Grover, L. K. (1996) A fast quantum mechanical algorithm for database search.
• Nielsen & Chuang (2010) Quantum Computation and Quantum Information.
• Farhi et al. (2014) A Quantum Approximate Optimization Algorithm (arXiv:1411.4028).
• Peruzzo et al. (2014) A variational eigenvalue solver on a quantum processor.

Citations
• Shor (1994) – Factoring algorithm.
• Grover (1996) – Quantum search.
• Farhi et al. (2014) – QAOA.
• Peruzzo et al. (2014) – VQE.
• Nielsen & Chuang (2010) – Circuit model and QFT.

