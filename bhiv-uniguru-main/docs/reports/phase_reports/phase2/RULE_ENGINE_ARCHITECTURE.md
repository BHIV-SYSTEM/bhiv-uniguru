# RULE_ENGINE_ARCHITECTURE.md

## Purpose

This document defines the architecture of the **Deterministic Rule Engine (RLM v1)** used by Unified UniGuru.

This engine is the core reasoning layer that decides whether a request should be:

- BLOCKED
- ANSWERED deterministically
- FORWARDED to the legacy generative system

This architecture replaces ad-hoc keyword checks with a **formal deterministic reasoning pipeline**.

---

## 1. Design Goals

The Rule Engine must be:

- Deterministic
- Stateless
- Traceable
- Extensible
- Middleware-ready

Same input → Same rule path → Same decision.

---

## 2. Core Abstractions

### 2.1 Base Rule Interface

All rules inherit from a shared abstract base class.

```python
class BaseRule(ABC):
    @abstractmethod
    def evaluate(self, context: RuleContext) -> RuleResult:
        pass
Rules must:

Be pure functions

Be stateless

Never call external services

Never mutate the request

2.2 RuleContext (Immutable State)

The RuleContext flows through the pipeline and contains the request plus execution metadata.

@dataclass(frozen=True)
class RuleContext:
    request_id: str
    content: str
    timestamp: float
    metadata: Dict[str, Any]
    trace_log: List[RuleTrace]


Important properties:

Original request is immutable

Trace log is append-only

Context is shared across rules

2.3 RuleResult (Decision Object)

Every rule returns a standardized decision object.

class RuleAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    ANSWER = "answer"
    FORWARD = "forward"

@dataclass
class RuleResult:
    action: RuleAction
    reason: str
    response_content: Optional[str] = None


This ensures all rules speak the same language.

3. Rule Engine Execution Pipeline

The RuleEngine orchestrates rule execution.

Execution Steps

Create RuleContext

Execute rules in fixed priority order

Log rule result

Stop when a terminal decision is reached

Decision Logic
Rule Result	Engine Behavior
ALLOW	Continue to next rule
BLOCK	Stop → return rejection
ANSWER	Stop → return deterministic answer
FORWARD	Stop → delegate to legacy system
Fallback Rule

If all rules return ALLOW → default decision = FORWARD.

This guarantees a final decision for every request.

4. Deterministic State Machine

The Rule Engine functions as a finite state machine.

State flow:

InputReceived → RuleEvaluation → DecisionReached

Decision states:

Rejected

DirectAnswer

ForwardToLegacy

There is no undefined state.

5. Rule Categories (RLM v1)

Rules are grouped into classes:

Category	Purpose
UnsafeRule	Prevent harmful/prohibited requests
AuthorityRule	Prevent system override attempts
AmbiguityRule	Detect unclear intent
EmotionalRule	Detect emotional distress
DelegationRule	Prevent performing user work

These categories define the reasoning model.

6. Governance Interception Hooks

The engine includes mandatory hooks:

Pre-Execution Hook

Input validation

Payload limits

Schema enforcement

Post-Decision Hook

Ensure decision contract integrity

Prevent accidental forwarding after BLOCK

Audit Hook

Write trace log before responding

These hooks prevent bypass of the rule engine.

7. Traceability Model

Every request produces a full execution trace.

Example:

{
  "request_id": "uuid",
  "rules_executed": [
    { "rule": "UnsafeRule", "action": "ALLOW" },
    { "rule": "AuthorityRule", "action": "BLOCK" }
  ],
  "final_decision": "BLOCK"
}


This enables full observability.

8. Extensibility Model

New rules can be added by:

Creating a new BaseRule subclass

Adding it to the rule order list

No existing rule modification required.

9. Summary

The RLM Rule Engine is a deterministic decision pipeline that ensures:

Governance → Reasoning → Decision → Forwarding

This engine forms the core of the Unified UniGuru architecture.