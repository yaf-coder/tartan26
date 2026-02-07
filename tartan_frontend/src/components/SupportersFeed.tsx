import "./SupportersFeed.css";
import type { JobRecord } from "../types";

export default function SupportersFeed({ job }: { job: JobRecord | null }) {
  return (
    <div className="supportersFeed">
      <h3>Run log</h3>
      {!job ? (
        <div className="supportersFeed__empty">Nothing yet.</div>
      ) : (
        <div className="supportersFeed__list">
          <div className="supportersFeed__item">
            <b>Created:</b> {job.created_at}
          </div>
          <div className="supportersFeed__item">
            <b>Updated:</b> {job.updated_at}
          </div>
          <div className="supportersFeed__item">
            <b>Status:</b> {job.status}
          </div>
          <div className="supportersFeed__item">
            <b>Stage:</b> {job.stage}
          </div>
          {job.error && (
            <div className="supportersFeed__item supportersFeed__error">
              <b>Error:</b> {job.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
