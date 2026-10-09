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
  request_id?: string;
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

export function extractData<T>(response: { data: ApiResponse<T> }): T {
  if (response.data.error) {
    throw Object.assign(new Error(response.data.error.message), {
      code: response.data.error.code,
    });
  }
  return response.data.data as T;
}
