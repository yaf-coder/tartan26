/**
 * API client for the Veritas backend.
 * VITE_API_URL defaults to http://localhost:8000 (set in .env for production).
 */

import type { LoadingStep, Source, ThinkingLog } from './types';

// In dev, use relative URL so Vite proxy forwards /api to the backend
const API_BASE = (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? '';

export interface ResearchResponse {
  sources: Source[];
  summary: string;
  /** Comprehensive literature review markdown document */
  literature_review?: string;
  /** Metadata about the literature review */
  review_metadata?: {
    word_count: number;
    sources_analyzed: number;
    evidence_items: number;
  };
  /** Names of the source PDF files (e.g. from arXiv); use with getPaperDownloadUrl to download */
  source_files: string[];
}

/** URL to download a source paper PDF by filename */
export function getPaperDownloadUrl(filename: string): string {
  const base = API_BASE || '';
  return `${base}/api/papers/${encodeURIComponent(filename)}`;
}

export interface ResearchStreamCallbacks {
  onStep: (step: LoadingStep) => void;
  onLog: (log: ThinkingLog) => void;
  onResult: (data: ResearchResponse) => void;
  onError: (message: string) => void;
}

/**
 * Submit research and consume the NDJSON stream: progress steps then result.
 * Calls onStep(step) for each progress event, onResult(data) when done, or onError(message) on failure.
 */
export async function submitResearchStream(
  query: string,
  files: File[],
  callbacks: ResearchStreamCallbacks
): Promise<void> {
  const formData = new FormData();
  formData.append('query', query.trim());
  for (const file of files) {
    formData.append('files', file);
  }

  const url = API_BASE ? `${API_BASE}/api/research` : '/api/research';
  const res = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const message = (body.detail as string) || res.statusText || 'Research request failed';
    callbacks.onError(message);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    callbacks.onError('No response body');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';
  let currentStep: LoadingStep = 'finding-sources';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const obj = JSON.parse(trimmed) as {
            type: string;
            step?: string;
            message?: string;
            detail?: string;
            sources?: Source[];
            summary?: string;
            literature_review?: string;
            review_metadata?: { word_count: number; sources_analyzed: number; evidence_items: number };
            source_files?: string[];
          };
          if (obj.type === 'step' && obj.step) {
            currentStep = obj.step as LoadingStep;
            callbacks.onStep(currentStep);
          } else if (obj.type === 'log' && obj.message) {
            callbacks.onLog({
              step: currentStep,
              message: obj.message,
              timestamp: new Date().toLocaleTimeString(),
            });
          } else if (obj.type === 'result') {
            callbacks.onResult({
              sources: obj.sources ?? [],
              summary: obj.summary ?? '',
              literature_review: obj.literature_review,
              review_metadata: obj.review_metadata,
              source_files: obj.source_files ?? [],
            });
            return;
          } else if (obj.type === 'error' && obj.detail) {
            callbacks.onError(obj.detail);
            return;
          }
        } catch {
          // ignore malformed lines
        }
      }
    }
    if (buffer.trim()) {
      try {
        const obj = JSON.parse(buffer.trim()) as {
          type: string;
          detail?: string;
          sources?: Source[];
          summary?: string;
          literature_review?: string;
          review_metadata?: { word_count: number; sources_analyzed: number; evidence_items: number };
          source_files?: string[];
        };
        if (obj.type === 'result') {
          callbacks.onResult({
            sources: obj.sources ?? [],
            summary: obj.summary ?? '',
            literature_review: obj.literature_review,
            review_metadata: obj.review_metadata,
            source_files: obj.source_files ?? [],
          });
          return;
        }
        if (obj.type === 'error' && obj.detail) {
          callbacks.onError(obj.detail);
          return;
        }
      } catch {
        // ignore
      }
    }
    callbacks.onError('Incomplete response');
  } finally {
    reader.releaseLock();
  }
}
