/**
 * components/chat/QuickActions.tsx
 * ──────────────────────────────────
 * Floating context-setter chips rendered directly above the composer.
 * Exactly one may be active; clicking the active one clears it.
 */
import { Presentation, Calculator, FileText } from 'lucide-react';
import { QUICK_ACTIONS, type QuickActionIcon, type QuickActionId } from '../../lib/quickActions';

const ICONS: Record<QuickActionIcon, typeof Presentation> = {
  Presentation,
  Calculator,
  FileText,
};

interface QuickActionsProps {
  active: QuickActionId | null;
  onChange: (id: QuickActionId | null) => void;
}

export function QuickActions({ active, onChange }: QuickActionsProps) {
  return (
    <div className="quick-actions" role="group" aria-label="أوضاع سريعة">
      {QUICK_ACTIONS.map((action) => {
        const Icon = ICONS[action.icon];
        const isActive = active === action.id;
        return (
          <button
            key={action.id}
            type="button"
            className={`quick-action-chip${isActive ? ' quick-action-chip--active' : ''}`}
            aria-pressed={isActive}
            onClick={() => onChange(isActive ? null : action.id)}
          >
            <Icon size={15} strokeWidth={2} aria-hidden="true" />
            <span>{action.label}</span>
          </button>
        );
      })}
    </div>
  );
}
