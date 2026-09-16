# Node + Python Interaction Instructions

The system is fully decoupled into standard microservice architecture. 

### Starting the Backend (FastAPI / Uvicorn)
1. Open terminal in `uniguru_v2/backend/`
2. `.\venv\Scripts\activate`
3. `python main.py`
4. Result: API begins listening on port 8000 handling Kosha searches natively under HTTPBearer protection.

### Starting the Frontend (Vite / React)
1. Open a second terminal context in `uniguru_v2/frontend/`
2. `npm install` (Ensures package-lock parity)
3. `npm run dev`
4. Result: User UI spins up on port 5173/5174, preconnected to APIs.

*Both layers function symbiotically. The Python backend operates strictly via API routing definitions, and the Node UI dynamically wraps the returned datasets inside the application DOM.*
