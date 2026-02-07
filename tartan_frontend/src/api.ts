/**
 * API client for the Veritas backend.
 * VITE_API_URL defaults to http://localhost:8000 (set in .env for production).
 */

import type { Source } from './types';

// In dev, use relative URL so Vite proxy forwards /api to the backend
const API_BASE = (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? '';

export interface ResearchResponse {
  sources: Source[];
  summary: string;
  /** Names of the source PDF files (e.g. from arXiv); use with getPaperDownloadUrl to download */
  source_files: string[];
}

/** URL to download a source paper PDF by filename */
export function getPaperDownloadUrl(filename: string): string {
  const API_BASE = (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? '';
  const base = API_BASE || '';
  return `${base}/api/papers/${encodeURIComponent(filename)}`;
}

/**
 * Submit a research query to the backend. Optionally include PDF files as sources.
 * If no files are sent, the backend will search for papers (e.g. arXiv) to answer the question.
 */
export async function submitResearch(query: string, files: File[] = []): Promise<ResearchResponse> {
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
    throw new Error(message);
  }

  return res.json() as Promise<ResearchResponse>;
}
