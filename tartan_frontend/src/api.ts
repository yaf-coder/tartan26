import type { GenerateRequest, GenerateResponse, JobRecord } from "./types";

const API_BASE =
  (import.meta as any).env?.VITE_API_BASE_URL?.toString?.() ?? "";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `HTTP ${res.status} ${res.statusText} for ${path}${
        text ? ` — ${text}` : ""
      }`
    );
  }

  return (await res.json()) as T;
}

export async function startGenerate(payload: GenerateRequest) {
  return await http<GenerateResponse>("/api/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getJob(jobId: string) {
  return await http<JobRecord>(`/api/jobs/${jobId}`, { method: "GET" });
}

// Download endpoints (browser will handle as file)
export function artifactDownloadUrl(jobId: string, artifactName: string) {
  return `${API_BASE}/api/jobs/${jobId}/download/${encodeURIComponent(
    artifactName
  )}`;
}

export async function fetchCitationsJson(jobId: string) {
  const url = artifactDownloadUrl(jobId, "citations.json");
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch citations.json (${res.status})`);
  return (await res.json()) as any;
}
