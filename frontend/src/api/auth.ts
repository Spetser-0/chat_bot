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
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  display_name?: string;
}

export const authApi = {
  async register(payload: RegisterPayload): Promise<Student> {
    const res = await apiClient.post('/auth/register', payload);
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
