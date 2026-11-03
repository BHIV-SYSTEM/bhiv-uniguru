---
title: Modern Physics, Quantum Mechanics, and Relativity
domain: physics
subject: Modern Physics & Quantum Mechanics
authority_score: 0.99
source_name: CERN & IBM Quantum Educational Platform
source_url: https://quantum.cloud.ibm.com/
license: Open Educational Access
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Modern Physics, Quantum Mechanics, and Relativity

## 1. Quantum Mechanics Core Principles
Quantum mechanics governs the behavior of matter and radiation at atomic and subatomic scales:
- **Planck-Einstein Relation**: Energy of a photon is quantized:
  $$E = h \nu = \hbar \omega \quad (h \approx 6.626 \times 10^{-34} \text{ J}\cdot\text{s})$$
- **de Broglie Wave-Particle Duality**: Any particle with momentum $p$ has an associated de Broglie wavelength:
  $$\lambda = \frac{h}{p} = \frac{h}{m v}$$
- **Heisenberg's Uncertainty Principle**: Conjugate variables like position $x$ and momentum $p$ cannot simultaneously be measured with arbitrary precision:
  $$\Delta x \cdot \Delta p \ge \frac{\hbar}{2}$$
- **Schrödinger Equation (Time-Dependent)**:
  $$i \hbar \frac{\partial}{\partial t} |\psi(t)\rangle = \hat{H} |\psi(t)\rangle$$
  where $\hat{H}$ is the Hamiltonian (total energy) operator.

## 2. Einstein's Special and General Relativity
- **Postulates of Special Relativity**:
  1. The laws of physics are invariant across all inertial frames of reference.
  2. The speed of light in vacuum $c$ is constant and independent of the motion of the source or observer.
- **Lorentz Transformation Factor**:
  $$\gamma = \frac{1}{\sqrt{1 - \frac{v^2}{c^2}}}$$
- **Time Dilation**: Moving clocks run slower: $\Delta t = \gamma \Delta t_0$.
- **Length Contraction**: Moving objects contract along the direction of motion: $L = \frac{L_0}{\gamma}$.
- **Mass-Energy Equivalence**:
  $$E = mc^2 \quad \text{or for moving particles: } E^2 = (pc)^2 + (m_0 c^2)^2$$
- **General Relativity**: Gravitation is not an invisible force, but a curvature of four-dimensional spacetime caused by mass-energy density, governed by **Einstein's Field Equations**:
  $$G_{\mu\nu} + \Lambda g_{\mu\nu} = \frac{8\pi G}{c^4} T_{\mu\nu}$$

## 3. Nuclear Physics and Semiconductors
- **Radioactive Decay Law**:
  $$N(t) = N_0 e^{-\lambda t}, \quad T_{1/2} = \frac{\ln(2)}{\lambda} \approx \frac{0.693}{\lambda}$$
- **Nuclear Binding Energy**: The mass defect $\Delta m = [Z m_p + (A - Z)m_n] - M_{\text{nucleus}}$ yields binding energy:
  $$BE = \Delta m \cdot c^2$$
- **Semiconductor Physics**:
  - **Intrinsic Semiconductors**: Pure crystals (Silicon, Germanium) where electron concentration equals hole concentration ($n_i = p_i$).
  - **Extrinsic Semiconductors**: Formed by doping:
    - **N-type**: Doped with pentavalent donors (Phosphorus, Arsenic) -> Majority carriers are electrons.
    - **P-type**: Doped with trivalent acceptors (Boron, Gallium) -> Majority carriers are holes.
  - **P-N Junction**: Forms a depletion region and built-in potential barrier ($\sim 0.7\text{ V}$ for Si). Under forward bias, the barrier decreases, allowing exponential current flow ($I = I_0(e^{qV/k_B T} - 1)$).
