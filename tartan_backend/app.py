# tartan_backend/app.py
from __future__ import annotations

import asyncio
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from tartan_backend.core.quotes_pipeline import run_quotes_pipeline
from tartan_backend.core.paper_pipeline import run_paper_pipeline


# ----------------------------
# App
# ----------------------------
app = FastAPI(title="Tartan Backend", version="1.0")

# CORS: allow your React dev server(s). Add domains as needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------
# Job store (in-memory)
# ----------------------------
# NOTE: This is in-memory. Restarting the server loses job state.
# If you want persistence later, swap this for Redis/DB without changing endpoints.
JOBS: Dict[str, Dict[str, Any]] = {}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_job_id() -> str:
    return uuid.uuid4().hex


def _repo_root() -> str:
    # app.py is in tartan_backend/, so repo root is one level up
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, ".."))


def _runs_root() -> str:
    return os.path.join(_repo_root(), "tartan_backend", "runs")


def _job_dir(job_id: str) -> str:
    return os.path.join(_runs_root(), job_id)


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _safe_rm_tree(path: str) -> None:
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        return


def _update_job(job_id: str, **kwargs: Any) -> None:
    job = JOBS.get(job_id)
    if not job:
        return
    job.update(kwargs)
    job["updated_at"] = _utc_now_iso()


def _set_progress(job_id: str, stage: str, pct: int) -> None:
    pct = max(0, min(100, int(pct)))
    _update_job(job_id, stage=stage, progress=pct)


# ----------------------------
# Request/response models
# ----------------------------
class GenerateRequest(BaseModel):
    rq: str = Field(..., min_length=5, description="Research question (the only required input)")
    topic: Optional[str] = Field(
        None,
        description="Optional topic/title. If omitted, we’ll derive a reasonable default.",
    )

    # seek
    depth: int = Field(2, ge=0, le=8)

    # ideas
    with_ideas: bool = True
    ideas_model: str = "openai/gpt-4o-mini"

    # merge
    no_dedupe: bool = False

    # paper generation
    model: str = "anthropic/claude-opus-4-6"
    min_words: int = Field(1400, ge=300, le=10000)
    max_words: int = Field(2400, ge=500, le=20000)
    max_iters: int = Field(4, ge=0, le=10)

    # header (optional)
    title: str = "Research Paper"
    author: str = "Your Name"
    institution: str = "Your Institution"
    course: str = "Course"
    instructor: str = "Instructor"
    date: str = "Date"


class GenerateResponse(BaseModel):
    job_id: str


# ----------------------------
# Endpoints
# ----------------------------
@app.get("/api/health")
def health():
    return {"ok": True, "time": _utc_now_iso()}


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    """
    Single-shot endpoint:

    React sends ONLY the research question (rq).
    Backend:
      1) seek_bot downloads papers into job's papers/
      2) research_bot extracts quotes -> csvs/
      3) clean/merge/(optional ideas)
      4) full_paper_pipeline generates paper.md + paper.pdf
    """
    job_id = _new_job_id()

    # Create job directories
    root = _ensure_dir(_runs_root())
    job_root = _ensure_dir(_job_dir(job_id))
    papers_dir = _ensure_dir(os.path.join(job_root, "papers"))
    csv_dir = _ensure_dir(os.path.join(job_root, "csvs"))
    out_dir = _ensure_dir(os.path.join(job_root, "outputs"))

    topic = (req.topic or "").strip()
    if not topic:
        # safe default: treat rq as topic-ish
        topic = req.rq.strip()
        if len(topic) > 120:
            topic = topic[:120].rstrip() + "…"

    JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",  # queued | running | succeeded | failed
        "stage": "queued",
        "progress": 0,
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
        "error": None,
        "rq": req.rq,
        "topic": topic,
        "paths": {
            "job_root": job_root,
            "papers_dir": papers_dir,
            "csv_dir": csv_dir,
            "out_dir": out_dir,
        },
        "artifacts": {},  # filled on success
    }

    async def _runner():
        _update_job(job_id, status="running")
        try:
            # ---- QUOTES PIPELINE ----
            def quotes_prog(p: int):
                _set_progress(job_id, stage="quotes_pipeline", pct=p)

            _set_progress(job_id, stage="quotes_pipeline", pct=1)
            quotes_art = await run_quotes_pipeline(
                rq=req.rq,
                papers_dir=papers_dir,
                csv_dir=csv_dir,
                depth=req.depth,
                with_ideas=req.with_ideas,
                ideas_model=req.ideas_model,
                no_dedupe=req.no_dedupe,
                clear_existing_pdfs=True,
                progress_cb=quotes_prog,
            )

            # choose notes CSV for paper generation
            notes_csv = quotes_art["final_csv"]

            # ---- PAPER PIPELINE ----
            def paper_prog(p: int):
                # map paper progress into 60..100 so UI feels smooth
                p = max(0, min(100, int(p)))
                mapped = 60 + int(p * 0.4)
                _set_progress(job_id, stage="paper_pipeline", pct=mapped)

            _set_progress(job_id, stage="paper_pipeline", pct=60)
            paper_art = await run_paper_pipeline(
                rq=req.rq,
                topic=topic,
                papers_dir=papers_dir,
                notes_csv=notes_csv,
                out_dir=out_dir,
                model=req.model,
                title=req.title,
                author=req.author,
                institution=req.institution,
                course=req.course,
                instructor=req.instructor,
                date=req.date,
                min_words=req.min_words,
                max_words=req.max_words,
                max_iters=req.max_iters,
                progress_cb=paper_prog,
            )

            artifacts = {
                # quotes artifacts
                "rq_quotes_csv": quotes_art.get("rq_quotes_csv"),
                "merged_csv": quotes_art.get("merged_csv"),
                "final_csv": quotes_art.get("final_csv"),
                # paper artifacts
                "paper_md": paper_art.get("paper_md"),
                "paper_pdf": paper_art.get("paper_pdf"),
                "citations_json": paper_art.get("citations_json"),
            }

            _update_job(
                job_id,
                status="succeeded",
                stage="done",
                progress=100,
                artifacts=artifacts,
            )

        except Exception as e:
            _update_job(job_id, status="failed", stage="failed", error=str(e), progress=100)

    # Launch background task
    asyncio.create_task(_runner())

    return GenerateResponse(job_id=job_id)


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(job)


@app.get("/api/jobs/{job_id}/download/{artifact_name}")
def download_artifact(job_id: str, artifact_name: str):
    """
    Download a job artifact by name.

    Valid names (if job succeeded):
      - paper.pdf
      - paper.md
      - citations.json
      - rq_quotes.csv
      - all_quotes.csv
      - all_quotes_with_ideas.csv
    """
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    artifacts = job.get("artifacts") or {}
    paths = job.get("paths") or {}
    csv_dir = paths.get("csv_dir")
    out_dir = paths.get("out_dir")

    # Map friendly names to actual paths
    name_map = {
        "paper.pdf": artifacts.get("paper_pdf") or (os.path.join(out_dir, "paper.pdf") if out_dir else None),
        "paper.md": artifacts.get("paper_md") or (os.path.join(out_dir, "paper.md") if out_dir else None),
        "citations.json": artifacts.get("citations_json") or (os.path.join(out_dir, "citations.json") if out_dir else None),
        "rq_quotes.csv": artifacts.get("rq_quotes_csv") or (os.path.join(csv_dir, "rq_quotes.csv") if csv_dir else None),
        "all_quotes.csv": artifacts.get("merged_csv") or (os.path.join(csv_dir, "all_quotes.csv") if csv_dir else None),
        "all_quotes_with_ideas.csv": artifacts.get("final_csv") or (os.path.join(csv_dir, "all_quotes_with_ideas.csv") if csv_dir else None),
    }

    path = name_map.get(artifact_name)
    if not path:
        raise HTTPException(status_code=404, detail="Unknown artifact name")

    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Artifact not found on disk (job may have failed or not finished)")

    filename = os.path.basename(path)
    return FileResponse(path, filename=filename)


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    """
    Optional cleanup endpoint.
    Removes the job record and deletes run files on disk.
    """
    job = JOBS.pop(job_id, None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    paths = job.get("paths") or {}
    job_root = paths.get("job_root")
    if job_root:
        _safe_rm_tree(job_root)

    return {"ok": True, "deleted": job_id}
