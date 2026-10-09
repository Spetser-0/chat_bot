/**
 * api/payments.ts — Invoice creation + status (Phase 6, Lesson 6.3).
 */
import { apiClient, extractData } from './client';

export interface InvoiceResponse {
  invoice_id: string;
  status: string;
  amount_usd: number | string;
  credits_if_paid: number | string;
  currency: string;
  crypto_amount: number | string | null;
  crypto_address: string | null;
  payment_url: string | null;
  qr_code_url: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface InvoiceStatusResponse {
  invoice_id: string;
  status: string;
  amount_usd: number | string;
  paid_at: string | null;
  expires_at: string | null;
  credits: number | string;
}

export const paymentsApi = {
  async createInvoice(payload: {
    amount_usd: number;
    currency?: string;
    idempotency_key: string;
    description?: string;
  }): Promise<InvoiceResponse> {
    const res = await apiClient.post('/payments/create-invoice', payload);
    return extractData<InvoiceResponse>(res);
  },

  async status(invoiceId: string): Promise<InvoiceStatusResponse> {
    const res = await apiClient.get(`/payments/${invoiceId}/status`);
    return extractData<InvoiceStatusResponse>(res);
  },
};
