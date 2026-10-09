/**
 * hooks/useCredits.ts
 * ───────────────────
 * Live credit balance (Phase 9, Lesson 9.6).
 * Low-balance threshold: 10 credits (UI warning).
 */
import { useQuery } from '@tanstack/react-query';
import { creditsApi } from '../api/credits';

export const LOW_BALANCE_THRESHOLD = 10;

export function useCredits() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['credits', 'balance'],
    queryFn: () => creditsApi.balance(),
    staleTime: 30_000,
  });

  const balance = Number(data?.balance ?? 0);
  const creditsPerUsd = Number(data?.credits_per_usd ?? 100);

  return {
    balance,
    creditsPerUsd,
    isLoading,
    isError,
    refetch,
    isLow: balance < LOW_BALANCE_THRESHOLD,
    isEmpty: balance <= 0,
  };
}
