import { describe, it, expect } from 'vitest';
import { BRAND } from './constants';

describe('Branding Constants', () => {
  it('uses Spetser name, not Perplexity', () => {
    expect(BRAND.name).toBe('سبيتسر');
    expect(BRAND.nameEn).toBe('Spetser');
    expect(BRAND.name.toLowerCase()).not.toContain('perplexity');
  });

  it('uses correct brand colors', () => {
    expect(BRAND.colorPrimary).toBe('#01696D');
    expect(BRAND.colorAccent).toBe('#F59E0B');
  });

  it('references correct icon paths', () => {
    expect(BRAND.iconSvg).toMatch(/spetser.*\.svg$/);
    expect(BRAND.favicon).toMatch(/favicon\.ico$/);
    expect(BRAND.ogImage).toMatch(/spetser.*og.*\.png$/);
  });
});
