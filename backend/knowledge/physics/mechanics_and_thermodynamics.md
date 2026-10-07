---
title: Classical Mechanics, Newton's Laws, and Thermodynamics
domain: physics
subject: Mechanics & Thermodynamics
authority_score: 0.99
source_name: NCERT Physics & NIST Physical Reference Data
source_url: https://www.nist.gov/pml
license: Public Domain / Educational
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Classical Mechanics, Newton's Laws, and Thermodynamics

## 1. Newton's Three Laws of Motion
1. **Newton's First Law (Law of Inertia)**:
   An object remains in a state of rest or of uniform motion along a straight line unless acted upon by an external net force:
   $$\sum \mathbf{F} = \mathbf{0} \implies \frac{d\mathbf{v}}{dt} = \mathbf{0}$$

2. **Newton's Second Law (Fundamental Law of Dynamics)**:
   The rate of change of linear momentum of a body is directly proportional to the applied force and takes place in the direction of the force:
   $$\mathbf{F}_{\text{net}} = \frac{d\mathbf{p}}{dt} = \frac{d(m\mathbf{v})}{dt} = m\mathbf{a} \quad (\text{for constant mass } m)$$

3. **Newton's Third Law (Action-Reaction Principle)**:
   Whenever one object exerts a force on a second object, the second object exerts an equal and oppositely directed force on the first object:
   $$\mathbf{F}_{AB} = -\mathbf{F}_{BA}$$
   *Crucial Detail*: Action and reaction forces act on **two different bodies**, so they never cancel each other out internally.

## 2. Work, Energy, and Conservation Laws
- **Work**: The line integral of force over displacement:
  $$W = \int_{r_1}^{r_2} \mathbf{F} \cdot d\mathbf{r} = F \cdot d \cos(\theta)$$
- **Work-Energy Theorem**: The net work done on a particle equals the change in its kinetic energy:
  $$W_{\text{net}} = \Delta KE = \frac{1}{2}m v_f^2 - \frac{1}{2}m v_i^2$$
- **Conservation of Mechanical Energy**: In an isolated system with conservative forces:
  $$E_{\text{total}} = KE + PE = \text{constant}$$
- **Gravitational Potential Energy**: Near Earth's surface: $PE = mgh$; universally: $U(r) = -\frac{G M m}{r}$.

## 3. Laws of Thermodynamics
1. **Zeroth Law**: If bodies A and B are each in thermal equilibrium with a third body C, then A and B are in thermal equilibrium with each other. This establishes the physical definition of **Temperature**.
2. **First Law (Conservation of Energy)**:
   $$\Delta U = Q - W$$
   where $\Delta U$ is the change in internal energy, $Q$ is heat added to the system, and $W$ is work done by the system.
3. **Second Law (Entropy & Direction of Processes)**:
   In any spontaneous thermodynamic process, the total entropy of an isolated system always increases over time:
   $$\Delta S_{\text{universe}} \ge 0$$
   - **Kelvin-Planck Statement**: It is impossible to construct a heat engine operating in a cycle that absorbs heat from a single reservoir and produces an equivalent amount of work without rejecting heat.
   - **Clausius Statement**: Heat cannot spontaneously flow from a colder body to a hotter body without external work.
4. **Third Law**: As the temperature of a pure crystalline substance approaches absolute zero ($T \to 0\text{ K}$), the entropy of the system approaches a constant minimum ($S \to 0$).
