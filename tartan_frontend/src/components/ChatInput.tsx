import { useEffect, useMemo, useState } from "react";
import "./ChatInput.css";

type Props = {
  disabled?: boolean;
  defaultValue?: string;
  onSubmit: (rq: string) => void;
};

export default function ChatInput({ disabled, defaultValue, onSubmit }: Props) {
  const [value, setValue] = useState(defaultValue ?? "");

  useEffect(() => {
    if (defaultValue !== undefined) setValue(defaultValue);
  }, [defaultValue]);

  const canSubmit = useMemo(() => {
    return !disabled && value.trim().length >= 5;
  }, [disabled, value]);

  function submit() {
    if (!canSubmit) return;
    onSubmit(value.trim());
  }

  return (
    <div className="chatInput">
      <textarea
        className="chatInput__textarea"
        placeholder="Type a research question…"
        value={value}
        disabled={!!disabled}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <div className="chatInput__actions">
        <button
          className="chatInput__button"
          onClick={submit}
          disabled={!canSubmit}
          title="Ctrl+Enter / Cmd+Enter"
        >
          Generate
        </button>
      </div>
      <div className="chatInput__hint">
        Tip: Press <b>Ctrl+Enter</b> / <b>Cmd+Enter</b> to submit
      </div>
    </div>
  );
}
