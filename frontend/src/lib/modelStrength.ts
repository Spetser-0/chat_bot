/**
 * lib/modelStrength.ts — "AI model strength" selector state.
 * 
 * Maps to backend ChatCompletionRequest.model_strength ("flash" | "think" | "pro").
 */

export type ModelStrength = 'flash' | 'think' | 'pro';

export const MODEL_STRENGTHS: { value: ModelStrength; label: string; description: string }[] = [
  { 
    value: 'flash', 
    label: 'Flash',
    description: 'Fast responses for simple questions',
  },
  { 
    value: 'think', 
    label: 'Think',
    description: 'Balanced analysis for most tasks',
  },
  { 
    value: 'pro', 
    label: 'Pro',
    description: 'Deep reasoning for complex problems',
  },
];

const STORAGE_KEY = 'spetser.modelStrength';

export function getModelStrength(): ModelStrength {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'flash' || stored === 'think' || stored === 'pro') return stored;
  } catch {
    /* ignore */
  }
  return 'think'; // Default to 'think'
}

export function setModelStrength(value: ModelStrength): void {
  try {
    localStorage.setItem(STORAGE_KEY, value);
  } catch {
    /* ignore */
  }
}
