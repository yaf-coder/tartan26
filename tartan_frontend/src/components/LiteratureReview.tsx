import { useEffect, useMemo, useState } from "react";
import "./LiteratureReview.css";
import type { CitationsJson, JobRecord } from "../types";
import { artifactDownloadUrl, fetchCitationsJson } from "../api";
import SourceCard from "./SourceCard";

type Props = {
  job: JobRecord | null;
};

export default function LiteratureReview({ job }: Props) {
  const [citations, setCitations] = useState<CitationsJson | null>(null);
  const [citErr, setCitErr] = useState<string | null>(null);
  const [citLoading, setCitLoading] = useState(false);

  const succeeded = job?.status === "succeeded";
  const jobId = job?.job_id;

  const downloads = useMemo(() => {
    if (!jobId) return [];
    return [
      { name: "paper.pdf", label: "Paper (PDF)" },
      { name: "paper.md", label: "Paper (Markdown)" },
      { name: "citations.json", label: "Citations (JSON)" },
      { name: "rq_quotes.csv", label: "RQ Quotes (CSV)" },
      { name: "all_quotes.csv", label: "All Quotes (CSV)" },
      { name: "all_quotes_with_ideas.csv", label: "Quotes + Ideas (CSV)" },
    ];
  }, [jobId]);

  useEffect(() => {
    setCitations(null);
    setCitErr(null);
  }, [jobId]);

  async function loadCitations() {
    if (!jobId) return;
    setCitLoading(true);
    setCitErr(null);
    try {
      const obj = (await fetchCitationsJson(jobId)) as CitationsJson;
      setCitations(obj);
    } catch (e: any) {
      setCitErr(e?.message ?? String(e));
    } finally {
      setCitLoading(false);
    }
  }

  if (!job) {
    return (
      <div className="literatureReview">
        <h2>Results</h2>
        <div className="literatureReview__empty">
          Submit a research question to generate a paper.
        </div>
      </div>
    );
  }

  return (
    <div className="literatureReview">
      <h2>Results</h2>

      <div className="literatureReview__meta">
        <div>
          <b>Job:</b> {job.job_id}
        </div>
        <div>
          <b>Status:</b> {job.status}
        </div>
        <div>
          <b>Stage:</b> {job.stage}
        </div>
      </div>

      {!succeeded && (
        <div className="literatureReview__empty">
          Outputs will appear here when the job finishes.
        </div>
      )}

      {succeeded && jobId && (
        <>
          <div className="literatureReview__downloads">
            <h3>Downloads</h3>
            <div className="literatureReview__downloadGrid">
              {downloads.map((d) => (
                <a
                  key={d.name}
                  className="literatureReview__download"
                  href={artifactDownloadUrl(jobId, d.name)}
                  target="_blank"
                  rel="noreferrer"
                >
                  {d.label}
                </a>
              ))}
            </div>
          </div>

          <div className="literatureReview__sources">
            <div className="literatureReview__sourcesHeader">
              <h3>Sources</h3>
              <button
                className="literatureReview__button"
                onClick={loadCitations}
                disabled={citLoading}
              >
                {citLoading ? "Loading…" : citations ? "Refresh" : "Load"}
              </button>
            </div>

            {citErr && (
              <div className="literatureReview__error">
                Failed to load citations.json: {citErr}
              </div>
            )}

            {!citations && !citErr && (
              <div className="literatureReview__empty">
                Click “Load” to display citations parsed from downloaded PDFs.
              </div>
            )}

            {citations && (
              <div className="literatureReview__sourceList">
                {Object.entries(citations).map(([filename, v]) => (
                  <SourceCard
                    key={filename}
                    filename={filename}
                    reference={v.reference}
                    footnote={v.footnote}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
