# BHIV Routing Policy

## Scope
This policy defines conversation routing decisions for UniGuru as the BHIV knowledge gateway.

## Policy Matrix

| Query Type | Route Target | Implementation/Behavior |
| :--- | :--- | :--- |
| `KNOWLEDGE_QUERY` | `ROUTE_UNIGURU` | Deterministic reasoning; KB/Web verification. |
| `SYSTEM_QUERY` | `ROUTE_SYSTEM` | Access denied; blocked by routing policy. |
| `WORKFLOW_QUERY` | `ROUTE_WORKFLOW` | Delegated to BHIV Workflow Engine. |
| `TOOL_QUERY` | `ROUTE_WORKFLOW` | Delegated to Tool Execution Gateway. |
| `GENERAL_LLM_QUERY` | `ROUTE_LLM` | Delegated to open-chat LLM layer. |

1. Knowledge questions
- Query type: `KNOWLEDGE_QUERY`
- Route: `ROUTE_UNIGURU`
- Behavior: Deterministic reasoning and verification.

2. System commands
- Query type: `SYSTEM_QUERY`
- Route: `ROUTE_SYSTEM`
- Behavior: Blocked by policy, no execution path.

3. Workflow actions
- Query type: `WORKFLOW_QUERY`
- Route: `ROUTE_WORKFLOW`
- Behavior: Delegated to workflow engine integration path.

4. Tool invocation requests
- Query type: `TOOL_QUERY`
- Route: `ROUTE_WORKFLOW`
- Behavior: Delegated to tool/workflow execution gateway.

5. Open chat / non-knowledge conversation
- Query type: `GENERAL_LLM_QUERY`
- Route: `ROUTE_LLM`
- Behavior: Delegated to LLM response channel with disclaimer semantics.

## Fallback Rules
1. Verification fallback
- Condition: UniGuru returns `UNVERIFIED`.
- Action: Optional fallback to `ROUTE_LLM` with warning message.
- Control: `UNIGURU_ROUTER_UNVERIFIED_FALLBACK` (default `true`).

2. Latency fallback
- Condition: UniGuru response latency exceeds threshold.
- Action: Open circuit breaker and temporarily route to LLM.
- Controls:
  - `UNIGURU_ROUTER_LATENCY_THRESHOLD_MS`
  - `UNIGURU_ROUTER_CIRCUIT_OPEN_SECONDS`

## Queue Control
- Control: `UNIGURU_ROUTER_QUEUE_LIMIT`
- Action: serve safe fallback answer when queue limit is reached.

## Integration Notes
- Sankalp (Intelligence Layer): consumes router route metadata.
- Raj Prajapati (Enforcement Engine): receives canonical execution contract.
- Nilesh (Backend Systems): uses API-level delegation routes.
- Chandragupta (Frontend): renders routed response semantics and warnings.
