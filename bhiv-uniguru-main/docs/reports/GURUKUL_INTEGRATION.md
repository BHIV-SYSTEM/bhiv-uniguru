# GURUKUL_LIVE_INTEGRATION_REPORT

## Objective
Connect UniGuru as the speaking layer for Gurukul system.

## Implementation Details
- **Adapter Location**: `uniguru/integrations/gurukul/adapter.py`
- **Bridge Endpoint**: `POST /integrations/gurukul/chat`
- **Input Transformation**: Gurukul student query -> `GurukulQueryRequest` -> `RuleEngine`
- **Output Transformation**: Engine result -> `GurukulIntegrationAdapter` -> Verified JSON response.

## Request Flow Proof
- **Query Input**: "Explain nyaya logic"
- **Metadata**: `student_id: stu-101`, `class_id: logic-1`, `session_id: g1`
- **Engine Trace**: `RetrievalRule` triggered. Confidence 0.67.
- **Verification Status**: `VERIFIED`

## Example Verified Response
- **Output**: `Based on verified source: nyaya_logic.md`
- **Content**: 
  - Author: Gurukul Traditional School
  - Source: nyaya_logic.md
  - Logic: Defines four valid sources of knowledge (Pramanas).

## Refusal Testing
- **Query**: "What is the capital of France?"
- **Integration Outcome**: `Verification status: UNVERIFIED. I cannot verify this information from current knowledge.`
- **Result**: REFUSED by the Sovereign Enforcement layer.
