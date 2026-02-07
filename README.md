# Veritas — Hallucination-proof research

Frontend (React + Vite) and backend (Python research pipeline) for literature review with traceable quotes.

## Run the full stack

1. **Backend (API + pipeline)**  
   From the **project root** (`tartan26/`), with a virtualenv that has the backend deps. Set in `tartan_backend/.env`: `DEDALUS_API_KEY` (required for ranking and summary). For question-only research, set **CORE_API_KEY** (get one at [core.ac.uk/api-keys/register](https://core.ac.uk/api-keys/register)) to use CORE first; if unset or CORE returns no PDFs, the app falls back to **arXiv** and **Semantic Scholar**.

   ```bash
   cd /path/to/tartan26
   pip install -r requirements.txt
   # Install tartan_backend deps (pypdf, dedalus_labs, python-dotenv, etc.) in the same env
   uvicorn app:app --reload --port 8000
   ```
   (Running from `tartan_backend/` will fail with "Could not import module app" — the API lives in the root.)

2. **Frontend**  
   In another terminal:

   ```bash
   cd tartan_frontend && npm install && npm run dev
   ```

3. Open http://localhost:5173 — enter a research query, upload one or more PDFs, and submit. The app proxies `/api` to the backend and shows sources and a summary when the pipeline finishes.

## Backend-only (CLI pipeline)

From `tartan_backend/`:

```bash
python run_all.py --rq "Your research question" --papers_dir ./papers --with_ideas
```

Put PDFs in `papers/` and set `DEDALUS_API_KEY` in `.env`.
