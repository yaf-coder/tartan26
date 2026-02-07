import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";

import type { JobRecord } from "./types";
import { getJob, startGenerate } from "./api";

import {
  ChatInput,
  LiteratureReview,
  ProgressStepper,
  SupportersFeed,
  UploadDropzone,
  ValidationSidebar,
} from "./components";

// IMPORTANT: this matches your UploadDropzone's internal type
// (If you moved UploadedFile to types.ts, import it instead.)
type UploadedFile = {
  id: string;
  name: string;
  size: number;
  type: string;
};

const POLL_MS = 1500;

export default function App() {
  const [rq, setRq] = useState<string>("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<JobRecord | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // UploadDropzone state (even if v1 doesn’t upload to backend yet)
  const [files, setFiles] = useState<UploadedFile[]>([]);

  const pollingRef = useRef<number | null>(null);

  const isBusy = useMemo(() => {
    return job?.status === "queued" || job?.status === "running";
  }, [job?.status]);

  async function handleSubmit(nextRq: string) {
    setErr(null);
    setRq(nextRq);

    // Optional: clear uploaded files on new run
    // setFiles([]);

    // Reset visible job state immediately
    setJob(null);
    setJobId(null);

    try {
      // Minimal payload: just rq.
      const res = await startGenerate({ rq: nextRq });
      setJobId(res.job_id);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    }
  }

  // Poll job status
  useEffect(() => {
    let cancelled = false;

    async function tick(id: string) {
      try {
        const j = await getJob(id);
        if (!cancelled) setJob(j);
      } catch (e: any) {
        if (!cancelled) setErr(e?.message ?? String(e));
      }
    }

    // clear old
    if (pollingRef.current) {
      window.clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    if (!jobId) return;

    // immediate fetch
    tick(jobId);

    // interval
    pollingRef.current = window.setInterval(() => tick(jobId), POLL_MS);

    return () => {
      cancelled = true;
      if (pollingRef.current) {
        window.clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [jobId]);

  // Stop polling when terminal
  useEffect(() => {
    if (!jobId || !job) return;
    if (job.status === "succeeded" || job.status === "failed") {
      if (pollingRef.current) {
        window.clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }
  }, [jobId, job]);

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__brand">Tartan</div>
        <div className="app__sub">Research question → sources → quotes → paper</div>
      </header>

      <main className="app__main">
        <section className="app__left">
          <ChatInput disabled={isBusy} defaultValue={rq} onSubmit={handleSubmit} />

          {err && <div className="app__error">Error: {err}</div>}

          <div className="app__progress">
            <ProgressStepper
              status={job?.status ?? (jobId ? "running" : "idle")}
              stage={job?.stage ?? (jobId ? "queued" : "queued")}
              progress={job?.progress ?? (jobId ? 1 : 0)}
            />
          </div>

          {/* ✅ FIX: pass required props */}
          <UploadDropzone files={files} onFilesChange={setFiles} disabled={isBusy} />

          <SupportersFeed job={job} />
        </section>

        <section className="app__right">
          <LiteratureReview job={job} />
        </section>

        <aside className="app__sidebar">
          <ValidationSidebar job={job} />
        </aside>
      </main>

      <footer className="app__footer">
        {isBusy ? <span>Working… keep this tab open.</span> : <span>Ready.</span>}
      </footer>
    </div>
  );
}
