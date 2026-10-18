/**
 * lib/quickActions.ts — floating context-setter chips above the composer.
 *
 * Phase 1 (frontend-only): selecting a chip is local state. The backend
 * phase wires each id to the matching `active_skill_slug`.
 */
export type QuickActionId = 'presentation' | 'math' | 'report';

export type QuickActionIcon = 'Presentation' | 'Calculator' | 'FileText';

export interface QuickAction {
  id: QuickActionId;
  label: string;
  icon: QuickActionIcon;
}

export const QUICK_ACTIONS: QuickAction[] = [
  { id: 'presentation', label: 'إنشاء عرض تقديمي', icon: 'Presentation' },
  { id: 'math', label: 'حل مسائل رياضية', icon: 'Calculator' },
  { id: 'report', label: 'كتابة بحث / تقرير', icon: 'FileText' },
];

// TODO(backend): wire each id to the matching active_skill_slug.
