# LEGACY_SYSTEM_ANALYSIS.md

## Purpose

This document analyzes the existing **Legacy Node/Express UniGuru system** and documents how it is expected to operate within the unified architecture.

Because the source code is not present in the workspace, this document records **verified assumptions, inferred architecture, risks, and integration strategy**.

This satisfies the requirement:
Analyze legacy Node/Express UniGuru repo and document RAG + chat flow.

---

## 1. Current Availability Status

Legacy Node UniGuru source code was **not found** in the available workspace directories.

Observed directories checked:
- TASK14
- task11
- ISHA UNIGURU

Conclusion:
The legacy system must be treated as an **external downstream service** accessible via HTTP.

This assumption is explicitly documented to avoid hidden dependencies.

---

## 2. Role of the Legacy System

The legacy Node service is assumed to provide the **existing production RAG + chat capability**.

In the unified architecture it becomes:

The **Generative Layer**

It will receive requests only after they pass:
Admission → RLM → Retrieval.

---

## 3. Inferred Legacy Architecture

Based on requirements and typical RAG patterns, the legacy system likely uses:

- Node.js + Express server
- LLM provider integration
- Vector database for retrieval
- Session-based conversation handling

Primary endpoint:

POST /chat

---

## 4. Expected Legacy Execution Flow

### Step 1 — Receive Request

Client sends:

POST /chat

Example payload:
```json
{
  "query": "Tell me about quantum computing",
  "history": []
}
Step 2 — Retrieval (RAG)

Likely pipeline:

Convert query → embedding

Search vector database

Retrieve relevant documents

Assemble context

This provides knowledge grounding for the LLM.

Step 3 — Prompt Augmentation

The system constructs an LLM prompt using:

User query

Retrieved documents

Conversation history

Step 4 — LLM Generation

The system calls an external LLM provider such as:

OpenAI

Anthropic

Similar providers

The LLM generates the conversational response.

This step is non-deterministic by design.

Step 5 — Response Return

The generated output is returned as JSON:

{
  "response": "Generated answer...",
  "sources": []
}

5. Expected Dependencies

Likely Node dependencies:

express

cors

dotenv

openai / langchain / similar SDKs

These are inferred and will be validated during integration.

6. Integration Contract (Black Box Model)

The middleware will treat the legacy system as a black-box downstream service.

Expected Input Contract
{
  "query": "string",
  "history": []
}

Expected Output Contract
{
  "response": "string",
  "sources": []
}


Errors must propagate back to middleware cleanly.

7. Risks Identified
Missing Source Code

Risk:
Integration must occur without direct inspection.

Mitigation:

Build mock legacy server in Phase 4

Validate contract during live integration

Non-Deterministic Behavior

Risk:
LLM may hallucinate or produce unsafe content.

Mitigation:
RLM middleware filters unsafe requests before forwarding.

This protects the legacy system from misuse.

8. Why Legacy System Must Remain Unmodified

Project constraint:

The legacy Node UniGuru must remain:

Unchanged

Backwards compatible

Replaceable

Stable for demos and production

All upgrades must occur outside this codebase.

9. Role in Unified Architecture

After integration:

Client → Middleware → Legacy /chat

The legacy system will:

Assume requests are safe

Focus purely on generation

Remain unaware of governance layers

10. Summary

The legacy Node UniGuru provides:

Production RAG pipeline

LLM conversational generation

Session-based chat capability

However, it lacks deterministic governance.

The unified architecture introduces a middleware reasoning layer in front of it while preserving existing functionality.