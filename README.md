# UniGuru v2 - Unified Kosha Architectures

UniGuru v2 is a decoupled, deterministic RAG system utilizing FastAPI (Backend) and React/Vite (Frontend). It features a strictly domain-authenticated, deterministic Kosha retrieval pipeline (`/new_rag`) avoiding LLM hallucination during context fetching, while smartly falling back to a fine-tuned Groq LLM model when no hard data exists.

---

## 🤖 Fine-Tuned Marathi LLM (Qwen 2.5 7B Instruct)

We have fine-tuned Qwen 2.5 7B Instruct on **117,265 remediated Marathi Indic-SQuAD pairs** with strict response-only loss masking and calibrated abstention targets.

* **Hugging Face Hub**: [csshivamverma54/qwen2.5-7b-marathi-indic-squad](https://huggingface.co/csshivamverma54/qwen2.5-7b-marathi-indic-squad)
* **Complete Model Guide**: See [MODEL_GUIDE.md](MODEL_GUIDE.md) for quickstart Python code, local CLI inference, prompt formatting, and benchmark evaluations.
* **Key Capability**: Eliminates hallucinations on unanswerable queries by strictly outputting `"दिलेल्या संदर्भामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."` whenever information is absent from the context.

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

### MongoDB persistence
The backend stores accounts, login sessions, and chat history in MongoDB. Copy
`backend/.env.example` to `backend/.env`, then set `MONGODB_URI` to the rotated
MongoDB Atlas connection string and `MONGODB_DATABASE` to the database name
(defaults to `uniguru`). Keep the URI only in the ignored backend `.env` file or
your deployment's secret store; never put it in a frontend `VITE_` variable.

On first use, existing SQLite users, sessions, and chats are imported
idempotently into MongoDB. The original SQLite files are left untouched as
backups. Check backend logs for connection or migration errors.

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

---

## 🚀 Cloning and Running the Full Three-Server Architecture

UniGuru operates with a decoupled 3-tier local architecture:
1. **Local LLM Microservice** (Port `8001`): Serves the fine-tuned Qwen 2.5 7B Marathi model with GPU/CPU acceleration.
2. **FastAPI Backend Server** (Port `8000`): Handles chat sessions, session-scoped document RAG (PDF, DOCX, TXT, MD), semantic routing, and truth verification.
3. **React / Vite Frontend** (Port `5173`): Interactive chat UI with Indic guru profiles, attachment support, and grounded provenance sidebars.

### 📋 Prerequisites
- **Git**
- **Python**: 3.10, 3.11, or 3.12 (Python 3.11 recommended for PyTorch CUDA 12.1 & Unsloth)
- **Node.js**: v18+ & **npm**
- **GPU (Optional but recommended)**: NVIDIA GPU with CUDA for sub-second LLM inference (supports CPU fallback)

---

### 1. Clone the Repository
```bash
git clone https://github.com/BHIV-SYSTEM/bhiv-uniguru.git
cd bhiv-uniguru
```

---

### 2. Python Environment Setup (Backend & LLM)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pypdf python-multipart python-docx
```

---

### 3. Frontend Setup
```bash
cd frontend
npm install
cd ..
```

---

### 4. Running the Three Servers

You can launch all three servers in one command or run them in separate terminal windows:

#### Option A: One-Click Full-Stack Launcher (Windows)
Double-click `start_fullstack.bat` or run:
```powershell
.\start_fullstack.ps1
```
This automatically boots all 3 servers in dedicated windows and opens `http://localhost:5173`.

---

#### Option B: Separate Terminals (Cross-Platform)

##### Terminal 1: Local Fine-Tuned LLM Microservice (Port 8001)
```bash
# Windows:
run_llm_service.bat
# Or manually:
python inference/serve_local_llm.py --model models/adapters/qwen2.5-7b-indic-squad-mr-remediated --port 8001
```
> **Note**: If you haven't downloaded the fine-tuned weights yet, you can pull them from Hugging Face:
> ```bash
> python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='shivam159/qwen2.5-7b-marathi-indic-squad', local_dir='models/adapters/qwen2.5-7b-indic-squad-mr-remediated')"
> ```

##### Terminal 2: FastAPI Backend Server (Port 8000)
```bash
# Windows:
run_backend.bat
# Or manually (PowerShell):
$env:PYTHONPATH=".;backend"
$env:UNIGURU_HOST="127.0.0.1"
$env:UNIGURU_PORT="8000"
$env:UNIGURU_API_AUTH_REQUIRED="false"
$env:UNIGURU_DEMO_AUTH_ENABLED="true"
$env:UNIGURU_ALLOWED_CALLERS="*"
$env:UNIGURU_LLM_URL="http://127.0.0.1:8001/generate"
python -m uvicorn service.api:app --host 127.0.0.1 --port 8000 --reload
```

##### Terminal 3: React / Vite Frontend (Port 5173)
```bash
# Windows:
run_frontend.bat
# Or manually:
cd frontend
npm run dev
```

---

### 5. Accessing the Application
Once all 3 servers are running:
- Open your browser to **http://localhost:5173**
- Navigate to `/chatpage`
- Choose a Guru persona (e.g. *UniGuru Assistant* or *Essay Coach*)
- Ask questions in **English**, **Marathi**, or upload textbooks/documents (`.txt`, `.docx`, `.pdf`, `.md`) for grounded Q&A and instant summarization!

