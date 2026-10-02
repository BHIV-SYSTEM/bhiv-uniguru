# UniGuru Live Integration Architecture

```mermaid
flowchart LR
    A[Frontend Chat] --> B[NGINX :443]
    G[Gurukul Backend] --> B
    B --> C[Node Backend :8080<br/>/api/v1/chat/query<br/>/api/v1/gurukul/query]
    C --> D[UniGuru API :8000<br/>POST /ask]
    D --> E[Auth + Caller Validation]
    E --> F[Conversation Router]
    F --> R[Deterministic Rule Engine]
    F --> H[Safety / Governance]
    F --> I[Bucket Telemetry]
    D --> J[Core Alignment]
```

## Request Contracts

### Product Chat to UniGuru
```json
{
  "query": "What is a qubit?",
  "context": {
    "caller": "bhiv-assistant"
  }
}
```

### Gurukul to UniGuru
```json
{
  "query": "Explain Pythagoras theorem",
  "context": {
    "caller": "gurukul-platform",
    "student_id": "S-102"
  }
}
```

## Runtime Ports

- `nginx`: `80`, `443`
- `node-backend`: `8080` (internal)
- `uniguru-api`: `8000` (internal)
