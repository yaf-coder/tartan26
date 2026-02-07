export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export type JobStage =
  | "queued"
  | "quotes_pipeline"
  | "paper_pipeline"
  | "done"
  | "failed";

export type JobArtifacts = Partial<{
  rq_quotes_csv: string;
  merged_csv: string;
  final_csv: string;
  paper_md: string;
  paper_pdf: string;
  citations_json: string;
}>;

export type JobPaths = Partial<{
  job_root: string;
  papers_dir: string;
  csv_dir: string;
  out_dir: string;
}>;

export type JobRecord = {
  job_id: string;
  status: JobStatus;
  stage: JobStage | string;
  progress: number; // 0-100
  created_at: string;
  updated_at: string;
  error: string | null;
  rq: string;
  topic: string;
  paths?: JobPaths;
  artifacts?: JobArtifacts;
};

export type GenerateRequest = {
  rq: string;
  topic?: string;
  depth?: number;
  with_ideas?: boolean;
  ideas_model?: string;
  no_dedupe?: boolean;
  model?: string;
  min_words?: number;
  max_words?: number;
  max_iters?: number;

  title?: string;
  author?: string;
  institution?: string;
  course?: string;
  instructor?: string;
  date?: string;
};

export type GenerateResponse = {
  job_id: string;
};

export type CitationEntry = {
  filename: string;
  reference: string;
  footnote: string;
};

export type CitationsJson = Record<
  string,
  {
    reference: string;
    footnote: string;
  }
>;
