const API_BASE = '/api/v1';

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export class ApiClientError extends Error {
  code: string;
  details?: Record<string, unknown>;
  status: number;
  constructor(status: number, body: { error?: ApiError }) {
    const err = body.error ?? { code: 'INTERNAL_ERROR', message: 'Unknown error' };
    super(err.message);
    this.code = err.code;
    this.details = err.details;
    this.status = status;
  }
}

export async function apiFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
    ...init,
  });
  const ct = res.headers.get('content-type') ?? '';
  const body = ct.includes('application/json') ? await res.json() : {};
  if (!res.ok) {
    throw new ApiClientError(res.status, body as { error?: ApiError });
  }
  return body as T;
}

export async function uploadSpec(projectId: string, file: File | null, url: string | null) {
  const fd = new FormData();
  if (file) fd.append('file', file);
  if (url) fd.append('url', url);
  const res = await fetch(`${API_BASE}/projects/${projectId}/specifications/import`, {
    method: 'POST',
    credentials: 'include',
    body: fd,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiClientError(res.status, body);
  return body;
}
