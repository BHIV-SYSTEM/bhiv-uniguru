# UNIFIED SYSTEM MAP: UniGuru v2

## 1. Frontend Layer (React/Vite)
- **Framework**: Vite + React
- **Styling**: Tailwind CSS
- **Authentication**: Firebase / Supabase Integration
- **Key Routes**: `/chatpage`, Dashboard, User Profiles
- **Communication**: Interacts heavily with `localhost:8000/new_rag` and `localhost:8000/ask`

## 2. Core API Orchestration (FastAPI)
- **EntryPoint**: `backend/service/api.py` (Uvicorn `0.0.0.0:8000`)
- **Key Modules**:
  - `LiveUniGuruService`: Central deterministic rules engine handling standard requests.
  - `/new_rag` Endpoint: Bound exclusively to the Deterministic Kosha engine, supporting semantic domain fallbacks to Groq LLM.
- **Security**: Endpoint protected with `HTTPBearer` taking an explicit custom token (uniguru_secret_123) for access.

## 3. Kosha Integration System (RAG Replacement)
- **Module Path**: `backend/kosha/`
- **Logic**: Purely deterministic tag and keyword matching. NO embedded hallucination. 
- **Domain Authentication**: Auto-detects mapped domains (Agriculture, Urban, Water, Infrastructure).
- **Data Source**: Permanently linked to `backend/data/kosha/` scanning for any structured `.json` payloads.

## 4. LLM Generation Layer (Groq)
- **Fallback Orchestration**: When Kosha signals fail, the system dynamically routes back to `llama-3.3-70b-versatile`.
- **Environment Driven**: Connects seamlessly via `GROQ_API_KEY` mapping.
