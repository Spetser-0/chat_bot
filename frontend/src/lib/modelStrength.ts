/**
 * lib/modelStrength.ts — "AI model strength" selector state.
 *
 * Phase 1 (frontend-only): the choice is persisted locally and NOT sent to
 * the API. The backend phase maps these values onto the chat request.
 */
export type ModelStrength = 'fast' | 'balanced' | 'deep';

export const MODEL_STRENGTHS: { value: ModelStrength; label: string }[] = [
  { value: 'fast', label: 'سريع' },
  { value: 'balanced', label: 'متوازن' },
  { value: 'deep', label: 'عميق' },
];

const STORAGE_KEY = 'spetser.modelStrength';

export function getModelStrength(): ModelStrength {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'fast' || stored === 'balanced' || stored === 'deep') return stored;
  } catch {
    /* ignore */
  }
  return 'balanced';
}

export function setModelStrength(value: ModelStrength): void {
  try {
    localStorage.setItem(STORAGE_KEY, value);
  } catch {
    /* ignore */
  }
  // TODO(backend): map this onto the chat request once the API supports it.
}
