# UniGuru Production Deployment & Architecture Guide

## 1. System Topology & How Render Works

### Why the 7B Model Cannot Run Directly on Render
Render's standard web services run inside lightweight CPU containers (typically 512 MB – 2 GB RAM with shared CPU, no GPU). 
- A 7-billion parameter LLM like **Qwen 2.5 7B** requires **~5.5 GB VRAM** in 4-bit quantization and **~14 GB VRAM** in 16-bit.
- Loading PyTorch with CUDA model weights inside Render's CPU container will immediately trigger an **OOM (Out Of Memory)** kill.
- Therefore, the production Dockerfile (`Dockerfile`) is explicitly built with `torch==2.11.0+cpu` for fast, lightweight orchestration without heavy GPU dependencies.

### How the Model Runs in Production
UniGuru uses a **Decoupled Microservice Architecture**:
```
┌──────────────────────────────────────┐
│  Frontend (React / Vite)             │  Hosted on Vercel
│  https://uni-guru.vercel.app         │
└──────────────────┬───────────────────┘
                   │ HTTPS API calls
                   ▼
┌──────────────────────────────────────┐
│  Backend Orchestrator (FastAPI)      │  Hosted on Render (Web Service)
│  https://complete-uniguru.onrender   │  - Handles Auth, Sessions, Routing
└──────────┬───────────────────┬───────┘  - Deterministic Kosha & FAISS Knowledge Base
           │                   │
           │ (Internal RAG)    │ (External LLM Inference via UNIGURU_LLM_URL)
           ▼                   ▼
┌────────────────────┐   ┌──────────────────────────────────────────────┐
│  Local Knowledge   │   │  Dedicated GPU Inference Host                │
│  - 114 MD files    │   │  - Hugging Face Dedicated Endpoint           │
│  - FAISS index     │   │  - RunPod / Modal / Lambda Labs GPU Instance │
│  - Kosha Database  │   │  - Serves: csshivamverma54/                  │
└────────────────────┘   │            qwen2.5-7b-marathi-indic-squad     │
                         └──────────────────────────────────────────────┘
```

Whenever the backend router decides a query needs LLM generation (either for open conversation or grounded synthesis), it makes an asynchronous HTTP `POST` request to `UNIGURU_LLM_URL`.

---

## 2. General-Purpose vs. Marathi Fine-Tuning

### Base Model Intellect is Fully Preserved
- The base model is **Qwen 2.5 7B**, one of the top-performing open weights models globally for general reasoning, coding, math, English, and multilingual dialogue.
- Fine-tuning was executed with **LoRA (Low-Rank Adaptation)** targeting only attention and MLP projection matrices (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`).
- Because LoRA modifies low-rank adapter weights without destroying base model parameters, the model retains its broad, general-purpose reasoning across English and multiple languages.

### Dynamic Routing Modes in UniGuru
1. **Marathi RAG / Grounded Queries**:
   When context from textbooks or the knowledge base is present, the model strictly extracts facts and abstains with `"दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."` if unanswerable.
2. **General Knowledge / Open Chit-Chat (English & Multilingual)**:
   When no passage context is supplied, the inference server formats queries with the general assistant prompt:
   ```text
   ### System:
   You are UniGuru, a helpful conversational AI assistant. Answer the user's actual question directly.
   
   ### Question:
   {query}
   
   ### Answer:
   ```
   The model responds using its full base general-purpose knowledge.
3. **Optional Dual-Model Production Routing**:
   UniGuru also natively supports cloud LLM fallbacks (e.g., Groq `llama-3.1-8b-instant` via `GROQ_API_KEY`) for rapid general conversation while routing Indic queries to the fine-tuned Marathi adapter.

---

## 3. Production Deployment Options for the Model

### Option A: Hugging Face Dedicated Inference Endpoints (Easiest Cloud Setup)
1. Go to your uploaded Hugging Face repository:
   👉 **`https://huggingface.co/csshivamverma54/qwen2.5-7b-marathi-indic-squad`**
2. Click **Deploy** -> **Inference Endpoints (dedicated)**.
3. Select an **NVIDIA T4** (or **A10G**) instance.
4. Once deployed, copy your endpoint URL (e.g. `https://xyz.us-east-1.aws.endpoints.huggingface.cloud`).
5. In Render's Dashboard -> Environment Variables:
   - `UNIGURU_LLM_URL = https://xyz.us-east-1.aws.endpoints.huggingface.cloud`
   - `UNIGURU_LLM_API_KEY = <your-huggingface-token>`

### Option B: Cloud GPU Instance (RunPod / Modal / Vast.ai)
1. Spin up a low-cost GPU instance ($0.20 – $0.30/hr) with an RTX 3090, RTX 4090, or A4000.
2. Clone repo and run the microservice:
   ```bash
   python inference/serve_local_llm.py \
     --model csshivamverma54/qwen2.5-7b-marathi-indic-squad \
     --port 8001 \
     --host 0.0.0.0
   ```
3. Expose the port via a reverse proxy (Nginx or RunPod TCP proxy) and configure `UNIGURU_LLM_URL` in Render.

### Option C: Hybrid / Local GPU Tunnel (Zero Extra Cost)
1. Keep the model running locally on your RTX 3060:
   ```powershell
   .\run_llm_service.bat
   ```
2. Start a secure tunnel (e.g., Cloudflare Tunnel):
   ```bash
   cloudflared tunnel --url http://127.0.0.1:8001
   ```
3. Copy the public tunnel HTTPS URL (e.g. `https://xxxx.trycloudflare.com/generate`).
4. Paste it as `UNIGURU_LLM_URL` in Render. Render on the web will talk directly to your local GPU.

---

## 4. Production Environment Checklist

| Variable | Recommended Value | Purpose |
| :--- | :--- | :--- |
| `UNIGURU_ENVIRONMENT` | `production` | Enables production security and error masking |
| `UNIGURU_DEMO_AUTH_ENABLED` | `false` | Enforces authenticated API callers |
| `UNIGURU_API_AUTH_REQUIRED` | `true` | Validates bearer tokens on endpoints |
| `UNIGURU_ALLOWED_CALLERS` | `bhiv-assistant,gurukul-platform,uniguru-frontend` | Restricts API access |
| `UNIGURU_LLM_URL` | `<Your-GPU-Endpoint>/generate` | Points Render to the model host |
| `UNIGURU_LLM_MODEL` | `qwen2.5-7b-marathi-indic-squad` | Model identification tag |
| `UNIGURU_LLM_TIMEOUT_SECONDS` | `45` | Protects router from hanging if GPU stalls |
| `UNIGURU_CORS_ORIGINS` | `https://uni-guru.vercel.app` | Restricts cross-origin requests to production UI |
| `MONGODB_URI` | `mongodb+srv://...` | Persistent chat sessions and user storage |

