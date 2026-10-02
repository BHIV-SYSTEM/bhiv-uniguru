# UniGuru v2 - Unified Kosha Architectures

UniGuru v2 is a decoupled, deterministic RAG system utilizing FastAPI (Backend) and React/Vite (Frontend). It features a strictly domain-authenticated, deterministic Kosha retrieval pipeline (`/new_rag`) avoiding LLM hallucination during context fetching, while smartly falling back to a fine-tuned Groq LLM model when no hard data exists.

---

## 🚀 How to Run the Full Stack

You will need to open **two** separate terminal windows to run both the frontend and backend servers simultaneously.

### 1. Run the Backend Server (FastAPI)
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Activate the virtual environment:
   - Windows: `.\venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
3. Run the backend service:
   ```bash
   python main.py
   ```
*(This starts your backend API locally on `http://0.0.0.0:8000`)*

### 2. Run the Frontend Server (Vite/React)
1. Open a second terminal window and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies (if you haven't recently):
   ```bash
   npm install
   ```
3. Start the Vite server:
   ```bash
   npm run dev
   ```
*(This starts the user interface locally, usually at `http://localhost:5173`. Open this URL in your web browser.)*

---

## 🧠 Using the `/new_rag` Endpoint

The new RAG system (`/new_rag`) uses our **Kosha** architecture. It automatically pulls from `backend/data/kosha/*.json` payloads.

You can query the RAG system directly using a `POST` request to `http://localhost:8000/new_rag`.

### Example Query Request
The system will **automatically detect the domain** from the query context (e.g., Agriculture, Urban, Infrastructure, Water / Rivers) if you do not strictly provide one!

```json
{
  "query": "reduce water consumption via drip irrigation"
}
```

*Optional Explicit Domain Routing:*
```json
{
  "query": "reduce water consumption via drip irrigation",
  "domain": "Agriculture"
}
```

### Example Query Response
If the system organically locates contextual data within Kosha, it returns a deterministic matched `signal`:

```json
{
  "query": "reduce water consumption via drip irrigation",
  "domain": "Agriculture",
  "answer": "Based on verified Kosha records, Drip irrigation reduces water consumption by up to 60% compared to traditional flood irrigation techniques in arid regions.",
  "confidence": 0.92,
  "signals": [
    {
      "signal_id": "sig_cb32f91a100",
      "signal_type": "KOSHA_VERIFIED",
      "content": "Drip irrigation reduces water consumption by up to 60% compared to traditional flood irrigation techniques in arid regions.",
      "confidence": 0.92,
      "source": "Water Conservation Handbook",
      "trace": {
        "knowledge_id": "K_AGRI_002",
        "retrieval_method": "deterministic_keyword_tag_match",
        "mapped_domain": "Agriculture"
      }
    }
  ],
  "status": "success"
}
```

### Automatic LLM Fallback
If the Kosha engine fails to find any deterministic context for a query (e.g., `"how fast does light travel?"`), it will dynamically trigger a fallback to the external LLM (`llama-3.3-70b-versatile` via Groq) to intelligently attempt to answer the user query out-of-bounds:

```json
{
  "query": "how fast does light travel?",
  "domain": null,
  "answer": "Light travels at approximately 299,792 kilometers per second in a vacuum.",
  "confidence": 0.0,
  "signals": [],
  "status": "success"
}
```

---

## 📁 Data Management
All JSON entry files you want queried must adhere to the Pydantic Kosha Schema (requiring `knowledge_id`, `domain`, `content`, `tags`, etc.). Just dump your data files inside `backend/data/kosha/` and the FastApi server loads them continuously.
