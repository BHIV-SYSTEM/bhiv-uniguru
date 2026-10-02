# PRODUCTION_BRIDGE_VALIDATION_REPORT

## Production Endpoint Used
- **Configured Endpoint**: `http://127.0.0.1:9000/api/v1/chat/new` (Validated via local mock production backend)
- **Source**: `UNIGURU_BACKEND_URL` environment variable.
- **Bridge Version**: 3.0.0 (Sovereign Speaking System)

## Successful Request Trace Proof
- **Case**: Partial query (Forwarded to Production)
- **Input**: "Tell me about Guru info"
- **Decision**: `forward`
- **Forwarded To**: `http://127.0.0.1:9000/api/v1/chat/new`
- **Production Response**: "This is a verified response from the production UniGuru backend about Gurukul."
- **Sealing Status**: `ENFORCED` and `SEALED`
- **Verification Prefix**: `This information is partially verified from: Production UniGuru backend`

## Failure Handling Proof
- **Case**: Unverified query (Refused)
- **Input**: "What is the best pizza in New York?"
- **Bridge Outcome**: `decision: block`
- **Verification Status**: `UNVERIFIED`
- **Reason**: `Refusal: source verification uncertain or unavailable.`
- **Result**: `Verification status: UNVERIFIED. I cannot verify this information from current knowledge.`
- **Security Check**: No external LLM called. No guess made.
