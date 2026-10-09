/**
 * api/referrals.ts — Public/authenticated referral API calls (Phase 7 + 9.7)
 */
import { apiClient, extractData } from './client';

export interface ReferralValidateResult {
  valid: boolean;
  referrer_display_name: string | null;
}

export interface ReferralLinkResult {
  referral_link: string;
  referral_code: string;
}

export interface ReferralStats {
  total_referrals: number;
  qualified_referrals: number;
  rewarded_referrals: number;
  total_earnings_usd: string;
  referral_link: string;
  referral_code: string;
  referred_by_user_id?: string | null;
}

export const referralsApi = {
  /** Public: check if a referral code is valid (Phase 7). */
  async validate(code: string): Promise<ReferralValidateResult> {
    const res = await apiClient.get(
      `/referrals/${encodeURIComponent(code)}/validate`,
    );
    return extractData<ReferralValidateResult>(res);
  },

  /** Authenticated: my referral link + code. */
  async link(): Promise<ReferralLinkResult> {
    const res = await apiClient.get('/referrals/link');
    return extractData<ReferralLinkResult>(res);
  },

  /** Authenticated: my referral stats. */
  async stats(): Promise<ReferralStats> {
    const res = await apiClient.get('/referrals/stats');
    return extractData<ReferralStats>(res);
  },
};
