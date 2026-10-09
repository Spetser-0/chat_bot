/**
 * api/credits.ts — Wallet endpoints (Lesson 5.5).
 */
import { apiClient, extractData } from './client';

export interface BalanceResponse {
  balance: number | string;
  credits_per_usd: number | string;
}

export interface LedgerEntry {
  id: string;
  entry_type: string;
  credits_charged: number | string | null;
  balance_after: number | string | null;
  description: string | null;
  reference_type: string | null;
  reference_id: string | null;
  created_at: string;
}

export interface HistoryResponse {
  entries: LedgerEntry[];
  total: number;
}

export const creditsApi = {
  async balance(): Promise<BalanceResponse> {
    const res = await apiClient.get('/credits/balance');
    return extractData<BalanceResponse>(res);
  },

  async history(limit = 50, offset = 0): Promise<HistoryResponse> {
    const res = await apiClient.get('/credits/history', { params: { limit, offset } });
    return extractData<HistoryResponse>(res);
  },
};
