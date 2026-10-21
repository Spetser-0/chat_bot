import { describe, it, expect } from 'vitest';
import { existsSync, statSync, readFileSync, readdirSync } from 'fs';
import { join } from 'path';

const PUBLIC_DIR = join(__dirname, '../public');

describe('Spetser icon assets', () => {
  const requiredAssets = [
    'favicon.ico',
    'spetser-icon.svg',
    'spetser-512.png',
    'spetser-192.png',
    'spetser-32.png',
    'spetser-16.png',
    'spetser-apple.png',
    'spetser-og.png',
  ];

  for (const asset of requiredAssets) {
    it(`${asset} exists and is non-empty`, () => {
      const path = join(PUBLIC_DIR, asset);
      expect(existsSync(path)).toBe(true);
      expect(statSync(path).size).toBeGreaterThan(0);
    });
  }

  it('SVG icon is valid', () => {
    const svgPath = join(PUBLIC_DIR, 'spetser-icon.svg');
    const content = readFileSync(svgPath, 'utf-8');
    expect(content).toContain('<svg');
    expect(content).toContain('</svg>');
    expect(content).toContain('#01696D'); // teal
    expect(content).toContain('#F59E0B'); // amber spark
  });

  it('no old Perplexity icons remain', () => {
    const files = readdirSync(PUBLIC_DIR);
    const perplexityFiles = files.filter((f) =>
      f.toLowerCase().includes('perplexity')
    );
    expect(perplexityFiles).toEqual([]);
  });
});
