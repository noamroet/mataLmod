import type {
  EligibilityRequest,
  EligibilityResponse,
  ProgramDetail,
} from '@/types';

// Server-side (SSR/ISR): use the Docker service hostname.
// Client-side (browser): use the public URL (reaches the published port).
const API_BASE =
  typeof window === 'undefined'
    ? (process.env.API_URL ?? 'http://localhost:8000')
    : (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000');

// ── Shared fetch wrapper ──────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // ignore parse error
    }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ── Endpoints ─────────────────────────────────────────────────────────────────

export function calculateEligibility(
  request: EligibilityRequest
): Promise<EligibilityResponse> {
  return apiFetch<EligibilityResponse>('/api/v1/eligibility/calculate', {
    method: 'POST',
    body:   JSON.stringify(request),
  });
}

export function fetchProgram(id: string): Promise<ProgramDetail> {
  return apiFetch<ProgramDetail>(`/api/v1/programs/${id}`);
}
