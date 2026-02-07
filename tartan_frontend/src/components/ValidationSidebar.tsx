import "./ValidationSidebar.css";
import type { JobRecord } from "../types";
import { artifactDownloadUrl } from "../api";

export default function ValidationSidebar({ job }: { job: JobRecord | null }) {
  if (!job) {
    return (
      <div className="validationSidebar">
        <h3>Status</h3>
        <div className="validationSidebar__empty">No job running.</div>
      </div>
    );
  }

  const succeeded = job.status === "succeeded";
  const failed = job.status === "failed";

  return (
    <div className="validationSidebar">
      <h3>Status</h3>

      <div className="validationSidebar__row">
        <span>Job</span>
        <span className="validationSidebar__mono">{job.job_id}</span>
      </div>
      <div className="validationSidebar__row">
        <span>State</span>
        <span>{job.status}</span>
      </div>
      <div className="validationSidebar__row">
        <span>Stage</span>
        <span>{job.stage}</span>
      </div>
      <div className="validationSidebar__row">
        <span>Progress</span>
        <span>{Math.floor(job.progress || 0)}%</span>
      </div>

      {failed && (
        <div className="validationSidebar__error">
          <b>Error:</b> {job.error || "Unknown error"}
        </div>
      )}

      {succeeded && (
        <>
          <h4>Quick downloads</h4>
          <div className="validationSidebar__links">
            <a
              href={artifactDownloadUrl(job.job_id, "paper.pdf")}
              target="_blank"
              rel="noreferrer"
            >
              paper.pdf
            </a>
            <a
              href={artifactDownloadUrl(job.job_id, "paper.md")}
              target="_blank"
              rel="noreferrer"
            >
              paper.md
            </a>
            <a
              href={artifactDownloadUrl(job.job_id, "citations.json")}
              target="_blank"
              rel="noreferrer"
            >
              citations.json
            </a>
          </div>
        </>
      )}
    </div>
  );
}
