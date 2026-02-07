import "./SourceCard.css";

type Props = {
  filename: string;
  reference: string;
  footnote: string;
};

export default function SourceCard({ filename, reference, footnote }: Props) {
  return (
    <div className="sourceCard">
      <div className="sourceCard__title">{filename}</div>
      <div className="sourceCard__ref">{reference}</div>
      <div className="sourceCard__foot">{footnote}</div>
    </div>
  );
}
