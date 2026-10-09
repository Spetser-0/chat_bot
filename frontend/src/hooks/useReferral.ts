/**
 * hooks/useReferral.ts
 * ────────────────────
 * Referral link + stats (Phase 9, Lesson 9.7).
 */
import { useQuery } from '@tanstack/react-query';
import { referralsApi } from '../api/referrals';

export function useReferral() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['referrals', 'me'],
    queryFn: () => referralsApi.stats(),
    staleTime: 60_000,
  });

  return {
    stats: data ?? null,
    isLoading,
    isError,
    refetch,
  };
}
