/**
 * components/billing/BuyCreditsModal.tsx
 * ───────────────────────────────────────
 * Buy-credits modal (Phase 9, Lesson 9.6).
 * Preset USD packs → POST /payments/create-invoice (mock crypto gateway)
 * → show address / payment link / credits preview / expiry.
 * Idempotency key is generated per modal-open so double-clicks don't
 * create duplicate invoices.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { paymentsApi, type InvoiceResponse } from '../../api/payments';
import { useCredits } from '../../hooks/useCredits';
import { useDismissable } from '../../hooks/useDismissable';

interface BuyCreditsModalProps {
  open: boolean;
  onClose: () => void;
}

const PACKS_USD = [5, 10, 25, 50] as const;
const CURRENCIES = ['USDT', 'BTC', 'ETH'] as const;

export function BuyCreditsModal({ open, onClose }: BuyCreditsModalProps) {
  const queryClient = useQueryClient();
  const { creditsPerUsd, refetch } = useCredits();
  const [amountUsd, setAmountUsd] = useState<number>(10);
  const [currency, setCurrency] = useState<string>('USDT');
  const [invoice, setInvoice] = useState<InvoiceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const dialogRef = useDismissable<HTMLDivElement>({ open, onClose, restoreFocus: true });

  // Fresh idempotency key per modal session (min 8 chars per schema).
  const idempotencyKey = useMemo(
    () => `buy-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [open],
  );

  useEffect(() => {
    if (!open) {
      setInvoice(null);
      setError(null);
    }
  }, [open]);

  const handleCreate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const inv = await paymentsApi.createInvoice({
        amount_usd: amountUsd,
        currency,
        idempotency_key: idempotencyKey,
        description: `شحن ${amountUsd} دولار رصيد`,
      });
      setInvoice(inv);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'تعذر إنشاء الفاتورة.');
    } finally {
      setLoading(false);
    }
  }, [amountUsd, currency, idempotencyKey]);

  const handleCheckStatus = useCallback(async () => {
    if (!invoice) return;
    setLoading(true);
    try {
      const status = await paymentsApi.status(invoice.invoice_id);
      if (status.status === 'paid') {
        await refetch();
        void queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      }
      setInvoice((prev) => (prev ? { ...prev, status: status.status } : prev));
    } catch {
      setError('تعذر التحقق من حالة الفاتورة.');
    } finally {
      setLoading(false);
    }
  }, [invoice, queryClient, refetch]);

  if (!open) return null;

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="buy-credits-title"
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        className="modal-card"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-card__header">
          <h2 id="buy-credits-title" className="modal-card__title">
            ⚡ شراء رصيد
          </h2>
          <button className="icon-btn" onClick={onClose} aria-label="إغلاق">
            ✕
          </button>
        </div>

        {invoice ? (
          /* ── Invoice view ─────────────────────────────────────────── */
          <div className="flex flex-col gap-3">
            <div
              role="status"
              style={{
                padding: 'var(--space-3)', borderRadius: 'var(--radius-md)',
                background: 'var(--color-parchment)', fontSize: 'var(--text-sm)',
              }}
            >
              الحالة:{' '}
              <strong>
                {invoice.status === 'paid' ? '✅ مدفوعة' :
                  invoice.status === 'pending' ? '⏳ بانتظار الدفع' :
                    invoice.status}
              </strong>
              {' — '}
              {Number(invoice.credits_if_paid).toFixed(0)} رصيد عند الدفع
            </div>

            {invoice.crypto_address && (
              <div className="field">
                <span className="field__label">عنوان الدفع ({invoice.currency})</span>
                <div className="code-block" dir="ltr">
                  <pre className="code-block__pre">
                    <code>{invoice.crypto_address}</code>
                  </pre>
                </div>
              </div>
            )}

            {invoice.crypto_amount && (
              <p className="text-sm text-secondary" dir="ltr" style={{ textAlign: 'left' }}>
                المبلغ: {Number(invoice.crypto_amount)} {invoice.currency}
              </p>
            )}

            {invoice.payment_url && (
              <a
                href={invoice.payment_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn--primary btn--full"
              >
                فتح صفحة الدفع 🔗
              </a>
            )}

            <button
              className="btn btn--ghost btn--full"
              onClick={handleCheckStatus}
              disabled={loading}
              aria-busy={loading}
            >
              🔄 تحديث الحالة
            </button>

            {invoice.status === 'paid' && (
              <p className="text-sm" style={{ color: 'var(--color-success)', textAlign: 'center' }}>
                تم شحن الرصيد! يمكنك إغلاق هذه النافذة.
              </p>
            )}
          </div>
        ) : (
          /* ── Pack picker ──────────────────────────────────────────── */
          <div className="flex flex-col gap-4">
            {error && (
              <div role="alert" className="text-sm" style={{
                padding: 'var(--space-3)', borderRadius: 'var(--radius-md)',
                background: 'var(--color-error-bg)', color: 'var(--color-error)',
              }}>
                {error}
              </div>
            )}

            <div>
              <span className="field__label">اختر الباقة</span>
              <div className="pack-grid" role="radiogroup" aria-label="باقات الشحن">
                {PACKS_USD.map((usd) => (
                  <button
                    key={usd}
                    type="button"
                    role="radio"
                    aria-checked={amountUsd === usd}
                    className={`pack-card${amountUsd === usd ? ' pack-card--active' : ''}`}
                    onClick={() => setAmountUsd(usd)}
                  >
                    <div className="pack-card__usd">${usd}</div>
                    <div className="pack-card__credits">
                      {(usd * creditsPerUsd).toFixed(0)} رصيد
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <label htmlFor="buy-currency" className="field__label">
                عملة الدفع
              </label>
              <select
                id="buy-currency"
                className="input"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
              >
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <button
              className="btn btn--primary btn--full"
              onClick={handleCreate}
              disabled={loading}
              aria-busy={loading}
            >
              {loading ? 'جاري الإنشاء…' : `إنشاء فاتورة — $${amountUsd}`}
            </button>

            <p className="text-xs text-muted" style={{ textAlign: 'center' }}>
              الدفع عبر مزوّد العملات الرقمية — تُضاف الرصيد تلقائياً بعد التأكيد.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
