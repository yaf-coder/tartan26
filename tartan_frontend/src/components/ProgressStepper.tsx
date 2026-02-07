import "./ProgressStepper.css";

type Props = {
  stage: string;
  progress: number; // 0-100
  status: string; // queued|running|succeeded|failed (or unknown)
};

function stageLabel(stage: string) {
  switch (stage) {
    case "queued":
      return "Queued";
    case "quotes_pipeline":
      return "Finding sources & extracting quotes";
    case "paper_pipeline":
      return "Writing paper (outline → draft → revise)";
    case "done":
      return "Complete";
    case "failed":
      return "Failed";
    default:
      return stage;
  }
}

export default function ProgressStepper({ stage, progress, status }: Props) {
  const pct = Math.max(0, Math.min(100, Math.floor(progress || 0)));

  return (
    <div className="progressStepper">
      <div className="progressStepper__top">
        <div className="progressStepper__label">
          <span className="progressStepper__stage">{stageLabel(stage)}</span>
          <span className="progressStepper__status">{status}</span>
        </div>
        <div className="progressStepper__pct">{pct}%</div>
      </div>

      <div className="progressStepper__barOuter">
        <div
          className="progressStepper__barInner"
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="progressStepper__steps">
        <Step active={stage === "quotes_pipeline"} done={pct >= 60}>
          Quotes
        </Step>
        <Step active={stage === "paper_pipeline"} done={pct >= 100}>
          Paper
        </Step>
        <Step active={stage === "done"} done={status === "succeeded"}>
          Output
        </Step>
      </div>
    </div>
  );
}

function Step({
  children,
  active,
  done,
}: {
  children: React.ReactNode;
  active?: boolean;
  done?: boolean;
}) {
  const cls = [
    "progressStepper__step",
    done ? "is-done" : "",
    active ? "is-active" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return <div className={cls}>{children}</div>;
}
