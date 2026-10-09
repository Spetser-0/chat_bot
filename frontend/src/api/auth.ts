/**
 * api/auth.ts — Authentication API calls
 */
import { apiClient, extractData } from './client';

export interface Student {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
  credit_balance: number;
  is_premium: boolean;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  display_name?: string;
  /** Referral code — sent as ?ref= query param (Phase 7 backend). */
  ref?: string;
}

export const authApi = {
  async register(payload: RegisterPayload): Promise<Student> {
    const { ref, ...body } = payload;
    const res = await apiClient.post('/auth/register', body, {
      params: ref ? { ref } : undefined,
    });
    return extractData<Student>(res);
  },

  async login(payload: LoginPayload): Promise<Student> {
    const res = await apiClient.post('/auth/login', payload);
    return extractData<Student>(res);
  },

  async logout(): Promise<void> {
    await apiClient.post('/auth/logout');
  },

  async me(): Promise<Student> {
    const res = await apiClient.get('/auth/me');
    return extractData<Student>(res);
  },
};
