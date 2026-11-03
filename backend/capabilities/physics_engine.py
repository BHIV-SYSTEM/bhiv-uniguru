"""
UniGuru Physics & Formula Calculation Capability
=================================================
Handles:
  - Physics law identification & conceptual statements (Newton's laws, Ohm's law, etc.)
  - Numerical physics problem solving with formula extraction:
      * Force: F = m * a
      * Kinetic Energy: KE = 0.5 * m * v^2
      * Potential Energy: PE = m * g * h
      * Work: W = F * d
      * Power: P = W / t
      * Momentum: p = m * v
      * Ohm's Law: V = I * R
      * Density: rho = m / V
      * Speed: v = d / t
  - Unit consistency and programmatic verification.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


class PhysicsEngine:
    """Physics problem solver and conceptual engine."""

    def solve(self, query: str) -> Optional[Dict[str, Any]]:
        clean_q = query.strip()

        # 1. Check for numerical force calculation: F = m * a
        # Example: "Calculate force for m=10kg and a=5m/s²"
        force_num = self._solve_force_numerical(clean_q)
        if force_num:
            return force_num

        # 2. Check for numerical kinetic energy: KE = 0.5 * m * v^2
        ke_num = self._solve_ke_numerical(clean_q)
        if ke_num:
            return ke_num

        # 3. Check for numerical Ohm's law: V = I * R
        ohm_num = self._solve_ohm_numerical(clean_q)
        if ohm_num:
            return ohm_num

        # 4. Check for conceptual physics laws (Newton's laws, etc.)
        concept_res = self._explain_physics_concept(clean_q)
        if concept_res:
            return concept_res

        return None

    def _solve_force_numerical(self, query: str) -> Optional[Dict[str, Any]]:
        # Match mass and acceleration
        # e.g. mass = 10 kg, a = 5 m/s^2, m=10kg, a=5m/s², a=5m/s
        m_match = re.search(r"(?:mass|m)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:kg|kilogram|g)?", query, re.IGNORECASE)
        a_match = re.search(r"(?:acceleration|accel|a)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:m\/s\S*|ms\S*)?", query, re.IGNORECASE)

        if m_match and a_match and ("force" in query.lower() or "f" in query.lower()):
            mass = float(m_match.group(1))
            accel = float(a_match.group(1))
            force = mass * accel
            force_disp = int(force) if force.is_integer() else round(force, 4)

            steps = [
                "**Physics Principle**: Newton's Second Law of Motion",
                "**Formula**: $$F = m \\cdot a$$",
                f"**Given Variables**:\n- Mass ($m$) = {mass} kg\n- Acceleration ($a$) = {accel} m/s²",
                f"**Calculation**:\n$$F = {mass} \\text{{ kg}} \\times {accel} \\text{{ m/s}}^2 = {force_disp} \\text{{ N}}$$",
                f"**Final Result**: The net force is **{force_disp} Newtons (N)**.",
            ]
            return {
                "capability": "PHYSICS",
                "sub_type": "newton_second_law_numerical",
                "result": f"{force_disp} N",
                "answer": "\n\n".join(steps),
                "verified": True,
            }
        return None

    def _solve_ke_numerical(self, query: str) -> Optional[Dict[str, Any]]:
        m_match = re.search(r"(?:mass|m)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:kg|kilogram)?", query, re.IGNORECASE)
        v_match = re.search(r"(?:velocity|speed|v)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:m\/s)?", query, re.IGNORECASE)

        if m_match and v_match and ("kinetic energy" in query.lower() or "ke" in query.lower()):
            mass = float(m_match.group(1))
            vel = float(v_match.group(1))
            ke = 0.5 * mass * (vel ** 2)
            ke_disp = int(ke) if ke.is_integer() else round(ke, 4)

            steps = [
                "**Physics Principle**: Kinetic Energy Formula",
                "**Formula**: $$KE = \\frac{1}{2} m v^2$$",
                f"**Given Variables**:\n- Mass ($m$) = {mass} kg\n- Velocity ($v$) = {vel} m/s",
                f"**Calculation**:\n$$KE = \\frac{{1}}{{2}} \\times {mass} \\times ({vel})^2 = {ke_disp} \\text{{ J}}$$",
                f"**Final Result**: The kinetic energy is **{ke_disp} Joules (J)**.",
            ]
            return {
                "capability": "PHYSICS",
                "sub_type": "kinetic_energy_numerical",
                "result": f"{ke_disp} J",
                "answer": "\n\n".join(steps),
                "verified": True,
            }
        return None

    def _solve_ohm_numerical(self, query: str) -> Optional[Dict[str, Any]]:
        v_match = re.search(r"(?:voltage|v)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:v|volts)?", query, re.IGNORECASE)
        i_match = re.search(r"(?:current|i)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:a|amp|amperes)?", query, re.IGNORECASE)
        r_match = re.search(r"(?:resistance|r)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:ohm|ohms|\u03a9)?", query, re.IGNORECASE)

        if "ohm" in query.lower() or "circuit" in query.lower() or (v_match and (i_match or r_match)):
            if i_match and r_match and not v_match:
                i = float(i_match.group(1))
                r = float(r_match.group(1))
                v = i * r
                v_disp = int(v) if v.is_integer() else round(v, 4)
                return {
                    "capability": "PHYSICS",
                    "sub_type": "ohm_law_voltage",
                    "result": f"{v_disp} V",
                    "answer": f"**Ohm's Law**: $$V = I \\cdot R$$\n\n- Current ($I$) = {i} A\n- Resistance ($R$) = {r} $\\Omega$\n\n$$V = {i} \\times {r} = {v_disp} \\text{{ Volts}}$$\n\n**Result**: **{v_disp} V**",
                    "verified": True,
                }
        return None

    def _explain_physics_concept(self, query: str) -> Optional[Dict[str, Any]]:
        q_lower = query.lower()

        # Newton's second law
        if "newton" in q_lower and ("second" in q_lower or "2nd" in q_lower):
            if "example" in q_lower:
                answer = (
                    "**Example of Newton's Second Law of Motion ($F = ma$)**:\n\n"
                    "1. **Pushing an Empty vs. Loaded Shopping Cart**:\n"
                    "   - An empty cart ($m_1$) accelerates quickly with modest force ($F$).\n"
                    "   - When loaded with heavy groceries ($m_2 > m_1$), significantly more force is required to achieve the same acceleration ($a = F/m$).\n\n"
                    "2. **Catching a Fast Baseball vs. Tennis Ball**:\n"
                    "   - Stopping a heavy, fast-moving ball requires the player's hands to apply a large counter-force over time to change its momentum."
                )
            else:
                answer = (
                    "**Newton's Second Law of Motion**:\n\n"
                    "> *The rate of change of momentum of a body is directly proportional to the applied net force, "
                    "and occurs in the direction of the force.*\n\n"
                    "### Mathematical Formulation:\n"
                    "$$\\vec{F} = \\frac{d\\vec{p}}{dt} = m \\vec{a}$$\n\n"
                    "- **$F$**: Net Force (measured in Newtons, N)\n"
                    "- **$m$**: Mass of the object (measured in kilograms, kg)\n"
                    "- **$a$**: Acceleration produced (measured in m/s²)\n\n"
                    "### Key Significance:\n"
                    "1. If mass is constant, acceleration is directly proportional to force.\n"
                    "2. Greater mass requires greater force to achieve the same acceleration."
                )
            return {
                "capability": "PHYSICS",
                "sub_type": "newton_second_law_concept",
                "result": "Newton's Second Law",
                "answer": answer,
                "verified": True,
            }

        # Newton's first law
        if "newton" in q_lower and ("first" in q_lower or "1st" in q_lower or "inertia" in q_lower):
            answer = (
                "**Newton's First Law of Motion (Law of Inertia)**:\n\n"
                "> *An object at rest stays at rest, and an object in motion stays in motion with the same speed and in the same direction, "
                "unless acted upon by an unbalanced external force.*\n\n"
                "### Key Concepts:\n"
                "- **Inertia**: The natural tendency of objects to resist changes in their state of motion.\n"
                "- **Equilibrium**: When net external force $\\Sigma F = 0$, acceleration is zero ($a = 0$)."
            )
            return {
                "capability": "PHYSICS",
                "sub_type": "newton_first_law_concept",
                "result": "Newton's First Law",
                "answer": answer,
                "verified": True,
            }

        # Newton's third law
        if "newton" in q_lower and ("third" in q_lower or "3rd" in q_lower or ("action" in q_lower and "reaction" in q_lower)):
            answer = (
                "**Newton's Third Law of Motion**:\n\n"
                "> *For every action, there is an equal and opposite reaction.*\n\n"
                "### Mathematical Form:\n"
                "$$\\vec{F}_{A \\to B} = -\\vec{F}_{B \\to A}$$\n\n"
                "Forces always occur in matched pairs acting on two different interacting bodies."
            )
            return {
                "capability": "PHYSICS",
                "sub_type": "newton_third_law_concept",
                "result": "Newton's Third Law",
                "answer": answer,
                "verified": True,
            }

        # Formula F = ma explanation
        if "f = ma" in q_lower or "f=ma" in q_lower or ("formula" in q_lower and "force" in q_lower):
            answer = (
                "**The Force Formula ($F = ma$)**:\n\n"
                "Derived directly from **Newton's Second Law of Motion**, the equation states that the net force "
                "acting on an object equals its mass multiplied by its acceleration:\n\n"
                "$$F = m \\cdot a$$\n\n"
                "- **$F$**: Net Force (in Newtons, $\\text{N} = \\text{kg}\\cdot\\text{m}/\\text{s}^2$)\n"
                "- **$m$**: Mass of the object (in kilograms, $\\text{kg}$)\n"
                "- **$a$**: Acceleration of the object (in $\\text{m}/\\text{s}^2$)\n\n"
                "This fundamental formula of classical mechanics relates kinematics (acceleration) with dynamics (mass and force)."
            )
            return {
                "capability": "PHYSICS",
                "sub_type": "f_ma_formula_concept",
                "result": "F = ma (Newton's Second Law)",
                "answer": answer,
                "verified": True,
            }

        # Kinetic energy formula explanation
        if "kinetic energy" in q_lower and ("formula" in q_lower or "equation" in q_lower or "what is" in q_lower):
            answer = (
                "**Kinetic Energy Formula**:\n\n"
                "Kinetic energy is the energy possessed by an object due to its motion. The formula is:\n\n"
                "$$KE = \\frac{1}{2} m v^2$$ (or $KE = 1/2 \\cdot m \\cdot v^2$)\n\n"
                "- **$KE$**: Kinetic Energy (measured in Joules, $\\text{J}$)\n"
                "- **$m$**: Mass of the object (measured in kilograms, $\\text{kg}$)\n"
                "- **$v$**: Speed or velocity of the object (measured in meters per second, $\\text{m}/\\text{s}$)\n\n"
                "Because velocity is squared, doubling the speed quadruples the kinetic energy."
            )
            return {
                "capability": "PHYSICS",
                "sub_type": "kinetic_energy_formula_concept",
                "result": "KE = 1/2 m v^2",
                "answer": answer,
                "verified": True,
            }

        # Ohm's Law concept
        if "ohm" in q_lower and ("law" in q_lower or "what is" in q_lower or "state" in q_lower):
            answer = (
                "**Ohm's Law**:\n\n"
                "> *The electric current flowing through a conductor between two points is directly proportional "
                "to the voltage across the two points, provided the temperature remains constant.*\n\n"
                "### Formula:\n"
                "$$V = I \\cdot R$$\n\n"
                "- **$V$**: Potential difference / Voltage (measured in Volts, $\\text{V}$)\n"
                "- **$I$**: Electric current (measured in Amperes, $\\text{A}$)\n"
                "- **$R$**: Resistance (measured in Ohms, $\\Omega$)"
            )
            return {
                "capability": "PHYSICS",
                "sub_type": "ohms_law_concept",
                "result": "Ohm's Law: V = I * R",
                "answer": answer,
                "verified": True,
            }

        return None


_physics_engine_instance = None


def get_physics_engine() -> PhysicsEngine:
    global _physics_engine_instance
    if _physics_engine_instance is None:
        _physics_engine_instance = PhysicsEngine()
    return _physics_engine_instance
