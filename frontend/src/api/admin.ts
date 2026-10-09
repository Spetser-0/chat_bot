/**
 * api/admin.ts — Admin dashboard API client (Phase 9, Lesson 9.8).
 * Covers Phase 8 admin endpoints: analytics, users, payments, audit,
 * referrals, providers, skills. Keys are masked server-side; never plaintext.
 */
import { apiClient, extractData } from './client';

// ── Analytics ────────────────────────────────────────────────────────────────

export interface AnalyticsOverview {
  users: { total: number; new_last_7d: number };
  messages: { total: number; assistant_last_7d: number };
  revenue: { total_usd: string; usd_last_7d: string };
  referrals: { total: number; qualified: number; conversion_rate: number };
}

export interface LlmUsageRowProvider {
  provider_name: string;
  messages: number;
  input_tokens: number;
  output_tokens: number;
  avg_latency_ms: number | null;
}

export interface LlmUsageRowSkill {
  skill_slug: string;
  messages: number;
  input_tokens: number;
  output_tokens: number;
}

export interface LlmUsageResponse {
  window_days: number;
  by_provider: LlmUsageRowProvider[];
  by_skill: LlmUsageRowSkill[];
}

export interface RevenueByStatus {
  status: string;
  count: number;
  total_usd: string;
}

export interface RevenueResponse {
  by_status: RevenueByStatus[];
  paid: { count: number; total_usd: string; average_usd: string };
}

export interface AdminReferralsAnalytics {
  by_status: { status: string; count: number }[];
  total: number;
  qualified: number;
  conversion_rate: number;
  rewards: {
    pending_count: number;
    pending_amount_usd: string;
    paid_count: number;
    paid_amount_usd: string;
  };
}

// ── Users ────────────────────────────────────────────────────────────────────

export interface AdminUser {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
  status: string;
  credit_balance: string;
  is_premium: boolean;
  premium_expires_at: string | null;
  failed_login_attempts: number;
  locked_until: string | null;
  referral_code: string | null;
  created_at: string | null;
}

export interface AdminUserList {
  items: AdminUser[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreditLedgerRow {
  id: string;
  credits_charged: string;
  balance_after: string | null;
  entry_type: string;
  description: string | null;
  reference_type: string | null;
  reference_id: string | null;
  created_at: string | null;
}

export interface AdminUserTransactions {
  items: CreditLedgerRow[];
  limit: number;
  offset: number;
}

// ── Payments ─────────────────────────────────────────────────────────────────

export interface AdminInvoice {
  id: string;
  user_id: string;
  provider: string;
  external_invoice_id: string | null;
  amount_usd: string;
  currency: string;
  crypto_amount: string | null;
  crypto_address: string | null;
  payment_url: string | null;
  status: string;
  expires_at: string | null;
  paid_at: string | null;
  idempotency_key: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AdminInvoiceList {
  items: AdminInvoice[];
  total: number;
  limit: number;
  offset: number;
}

export interface WebhookEventRow {
  id: string;
  provider: string;
  event_type: string;
  processed: boolean;
  processed_at: string | null;
  error: string | null;
  created_at: string | null;
}

export interface AdminInvoiceDetail extends AdminInvoice {
  webhook_events: WebhookEventRow[];
}

// ── Audit ────────────────────────────────────────────────────────────────────

export interface AuditLogRow {
  id: string;
  actor_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  metadata: Record<string, unknown> | null;
  correlation_id: string | null;
  created_at: string | null;
}

export interface AuditLogList {
  items: AuditLogRow[];
  total: number;
  limit: number;
  offset: number;
}

// ── Referrals ────────────────────────────────────────────────────────────────

export interface AdminReferral {
  id: string;
  referrer_user_id: string;
  referrer_email: string | null;
  referred_user_id: string;
  referred_email: string | null;
  referral_code: string;
  status: string;
  ip_address: string | null;
  device_fingerprint: string | null;
  created_at: string | null;
  qualified_at: string | null;
  rewarded_at: string | null;
  reward_amount: string | null;
  reward_status: string | null;
}

export interface AdminReferralList {
  items: AdminReferral[];
  count: number;
  limit: number;
  offset: number;
}

// ── Providers ────────────────────────────────────────────────────────────────

export interface AdminProvider {
  id: string;
  name: string;
  slug: string;
  model_name: string;
  base_url: string | null;
  api_key_masked: string;
  priority_weight: number;
  timeout_seconds: number;
  max_retries: number;
  cost_input_per_1k: string;
  cost_output_per_1k: string;
  is_active: boolean;
  is_primary: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface ProviderCreatePayload {
  name: string;
  slug: string;
  model_name: string;
  api_key: string;
  base_url?: string | null;
  priority_weight?: number;
  timeout_seconds?: number;
  max_retries?: number;
  cost_input_per_1k?: string;
  cost_output_per_1k?: string;
  is_active?: boolean;
  is_primary?: boolean;
}

export interface ProviderUpdatePayload {
  name?: string;
  model_name?: string;
  api_key?: string;
  base_url?: string | null;
  priority_weight?: number;
  timeout_seconds?: number;
  max_retries?: number;
  cost_input_per_1k?: string;
  cost_output_per_1k?: string;
  is_active?: boolean;
  is_primary?: boolean;
}

export interface ProviderTestResult {
  healthy: boolean;
  error: string | null;
}

// ── Skills ───────────────────────────────────────────────────────────────────

export interface AdminSkillTool {
  id: string;
  tool_name: string;
  tool_config: Record<string, unknown> | null;
  is_enabled: boolean;
}

export interface AdminSkill {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  system_prompt: string;
  temperature: string;
  max_tokens: number;
  preferred_provider_id: string | null;
  fallback_provider_id: string | null;
  is_public: boolean;
  is_premium: boolean;
  cost_multiplier: string;
  version: number;
  tools: AdminSkillTool[];
}

export interface SkillCountMeta {
  total: number;
  public: number;
}

export interface SkillCreatePayload {
  name: string;
  slug: string;
  description?: string | null;
  system_prompt: string;
  temperature?: string;
  max_tokens?: number;
  preferred_provider_id?: string | null;
  fallback_provider_id?: string | null;
  is_public?: boolean;
  is_premium?: boolean;
  cost_multiplier?: string;
}

export interface SkillUpdatePayload {
  name?: string;
  description?: string | null;
  system_prompt?: string;
  temperature?: string;
  max_tokens?: number;
  preferred_provider_id?: string | null;
  fallback_provider_id?: string | null;
  is_public?: boolean;
  is_premium?: boolean;
  cost_multiplier?: string;
}

export interface SkillTestResult {
  skill_slug: string;
  rendered_system_prompt: string;
  reply_text: string | null;
  provider_slug: string | null;
  usage: Record<string, unknown> | null;
  note: string | null;
}

// ── API ──────────────────────────────────────────────────────────────────────

export const adminApi = {
  // Analytics
  analyticsOverview: () =>
    apiClient.get('/admin/analytics/overview').then((r) => extractData<AnalyticsOverview>(r)),
  analyticsLlmUsage: (days = 30) =>
    apiClient
      .get('/admin/analytics/llm-usage', { params: { days } })
      .then((r) => extractData<LlmUsageResponse>(r)),
  analyticsRevenue: () =>
    apiClient.get('/admin/analytics/revenue').then((r) => extractData<RevenueResponse>(r)),
  analyticsReferrals: () =>
    apiClient
      .get('/admin/analytics/referrals')
      .then((r) => extractData<AdminReferralsAnalytics>(r)),

  // Users
  listUsers: (params?: { q?: string; role?: string; status?: string; limit?: number; offset?: number }) =>
    apiClient.get('/admin/users', { params }).then((r) => extractData<AdminUserList>(r)),
  getUser: (id: string) =>
    apiClient.get(`/admin/users/${id}`).then((r) => extractData<AdminUser>(r)),
  userTransactions: (id: string, limit = 50, offset = 0) =>
    apiClient
      .get(`/admin/users/${id}/transactions`, { params: { limit, offset } })
      .then((r) => extractData<AdminUserTransactions>(r)),
  adjustCredits: (id: string, body: { amount: string; reason: string; idempotency_key?: string }) =>
    apiClient
      .post(`/admin/users/${id}/adjust-credits`, body)
      .then((r) => extractData<{ user_id: string; credit_balance: string }>(r)),
  banUser: (id: string) =>
    apiClient.post(`/admin/users/${id}/ban`).then((r) => extractData<{ user_id: string; status: string }>(r)),
  unbanUser: (id: string) =>
    apiClient.post(`/admin/users/${id}/unban`).then((r) => extractData<{ user_id: string; status: string }>(r)),

  // Payments
  listPayments: (params?: { status?: string; user_id?: string; limit?: number; offset?: number }) =>
    apiClient.get('/admin/payments', { params }).then((r) => extractData<AdminInvoiceList>(r)),
  getPayment: (id: string) =>
    apiClient.get(`/admin/payments/${id}`).then((r) => extractData<AdminInvoiceDetail>(r)),
  manualConfirm: (id: string, reason: string) =>
    apiClient
      .post(`/admin/payments/${id}/manual-confirm`, { reason })
      .then((r) => extractData<{ invoice_id: string; status: string; credited_usd: string }>(r)),

  // Audit logs
  listAuditLogs: (params?: {
    actor_id?: string;
    action?: string;
    resource_type?: string;
    resource_id?: string;
    from_date?: string;
    to_date?: string;
    limit?: number;
    offset?: number;
  }) =>
    apiClient.get('/admin/audit-logs', { params }).then((r) => extractData<AuditLogList>(r)),

  // Referrals
  listReferrals: (params?: { status?: string; referrer_user_id?: string; limit?: number; offset?: number }) =>
    apiClient.get('/admin/referrals', { params }).then((r) => extractData<AdminReferralList>(r)),
  revokeReferral: (id: string) =>
    apiClient
      .post(`/admin/referrals/${id}/revoke`)
      .then((r) => extractData<{ id: string; status: string }>(r)),
  releaseReferral: (id: string) =>
    apiClient
      .post(`/admin/referrals/${id}/release`)
      .then((r) => extractData<{ reward_id: string; amount: string; status: string }>(r)),
  releaseDueRewards: () =>
    apiClient
      .post('/admin/referrals/release-due')
      .then((r) => extractData<{ released_count: number; total_amount: string }>(r)),

  // Providers
  listProviders: () =>
    apiClient.get('/admin/providers').then((r) => extractData<AdminProvider[]>(r)),
  getProvider: (slug: string) =>
    apiClient.get(`/admin/providers/${slug}`).then((r) => extractData<AdminProvider>(r)),
  createProvider: (body: ProviderCreatePayload) =>
    apiClient.post('/admin/providers', body).then((r) => extractData<AdminProvider>(r)),
  updateProvider: (slug: string, body: ProviderUpdatePayload) =>
    apiClient.patch(`/admin/providers/${slug}`, body).then((r) => extractData<AdminProvider>(r)),
  toggleProvider: (slug: string) =>
    apiClient
      .post(`/admin/providers/${slug}/toggle-active`)
      .then((r) => extractData<AdminProvider>(r)),
  testProvider: (slug: string) =>
    apiClient
      .post(`/admin/providers/${slug}/test`)
      .then((r) => extractData<ProviderTestResult>(r)),
  deleteProvider: (slug: string) =>
    apiClient.delete(`/admin/providers/${slug}`).then((r) => extractData(r)),

  // Skills
  listSkills: (includePrivate = true) =>
    apiClient
      .get('/admin/skills', { params: { include_private: includePrivate } })
      .then((r) => extractData<AdminSkill[]>(r)),
  skillCount: () =>
    apiClient.get('/admin/skills/_meta/count').then((r) => extractData<SkillCountMeta>(r)),
  getSkill: (id: string) =>
    apiClient.get(`/admin/skills/${id}`).then((r) => extractData<AdminSkill>(r)),
  createSkill: (body: SkillCreatePayload) =>
    apiClient.post('/admin/skills', body).then((r) => extractData<AdminSkill>(r)),
  updateSkill: (id: string, body: SkillUpdatePayload) =>
    apiClient.patch(`/admin/skills/${id}`, body).then((r) => extractData<AdminSkill>(r)),
  deleteSkill: (id: string) =>
    apiClient.delete(`/admin/skills/${id}`).then((r) => extractData(r)),
  testSkill: (id: string, sample_message: string) =>
    apiClient
      .post(`/admin/skills/${id}/test`, { sample_message })
      .then((r) => extractData<SkillTestResult>(r)),
};
