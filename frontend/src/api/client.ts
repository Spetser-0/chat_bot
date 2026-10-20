/**
 * api/client.ts
 * ─────────────
 * Typed API client. All requests go through this module.
 * Uses axios with credentials (session cookies) included.
 * Provider keys are never exposed here.
 */

import axios, { AxiosError } from 'axios';

export interface ApiResponse<T> {
  data: T | null;
  error: { code: string; message: string } | null;
  request_id?: string | null;
}

export interface ApiError {
  code: string;
  message: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

/** Absolute backend origin (no /api/v1) — used by fetch-based streaming. */
export const API_BASE_URL = API_BASE;


export const apiClient = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  withCredentials: true, // Send session cookies
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  timeout: 30_000,
});

// Response interceptor: extract data or throw typed error
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiResponse<unknown>>) => {
    const apiError = error.response?.data?.error;
    if (apiError) {
      const e = new Error(apiError.message) as Error & { code: string };
      e.code = apiError.code;
      return Promise.reject(e);
    }
    return Promise.reject(error);
  }
);

/**
 * Defensive envelope extractor.
 * Handles three shapes:
 *   1. Wrapped success:  { data: <T>, error: null, request_id }
 *   2. Wrapped error:    { data: null, error: {...}, request_id }
 *   3. Legacy bare:       <T>  (array or object) — tolerated during rollout
 */
export function extractData<T>(response: { data: unknown }): T {
  const body = response.data as Record<string, unknown> | unknown[] | null | undefined;

  // ── Shape 2: wrapped error (explicit) ──
  if (
    body !== null &&
    typeof body === "object" &&
    !Array.isArray(body) &&
    "error" in body &&
    body.error !== null &&
    typeof body.error === "object"
  ) {
    const err = body.error as { code: string; message: string };
    const wrappedError = Object.assign(new Error(err.message), {
      code: err.code,
    });
    throw wrappedError;
  }

  // ── Shape 1: wrapped success ──
  if (
    body !== null &&
    typeof body === "object" &&
    !Array.isArray(body) &&
    "data" in body &&
    "error" in body &&
    "request_id" in body
  ) {
    return (body as unknown as ApiResponse<T>).data as T;
  }

  // ── Shape 3: legacy bare (tolerance mode) ──
  // This branch should become dead code once P0.1 is fully deployed.
  // Remove in a future cleanup commit.
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.warn(
      "[extractData] Bare response received — backend envelope middleware may not be active.",
      body,
    );
  }
  return body as T;
}
