/**
 * components/chat/Markdown.tsx
 * ────────────────────────────
 * Markdown renderer for assistant messages (Phase 9, Lesson 9.4).
 *
 * - react-markdown (no dangerouslySetInnerHTML — safe by default)
 * - Code blocks: language label + copy button + lightweight
 *   regex-based highlighting for common languages (no heavy deps).
 */
import { useCallback, useMemo, useState } from 'react';
import MarkdownLib from 'react-markdown';

/* ── Minimal syntax highlighter (keywords / strings / comments) ────────── */

const KEYWORDS: Record<string, string[]> = {
  python: ['def', 'class', 'import', 'from', 'return', 'if', 'elif', 'else',
    'for', 'while', 'try', 'except', 'finally', 'with', 'as', 'async', 'await',
    'None', 'True', 'False', 'and', 'or', 'not', 'in', 'is', 'lambda', 'yield'],
  javascript: ['const', 'let', 'var', 'function', 'return', 'if', 'else',
    'for', 'while', 'class', 'extends', 'import', 'export', 'from', 'default',
    'async', 'await', 'try', 'catch', 'finally', 'new', 'this', 'null',
    'undefined', 'true', 'false'],
  typescript: ['const', 'let', 'var', 'function', 'return', 'if', 'else',
    'for', 'while', 'class', 'implements', 'interface', 'type', 'enum',
    'import', 'export', 'from', 'async', 'await', 'try', 'catch', 'new',
    'this', 'null', 'undefined', 'true', 'false'],
  jsx: [], tsx: [],
};
KEYWORDS.jsx = KEYWORDS.javascript;
KEYWORDS.tsx = KEYWORDS.typescript;

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/** Highlight one line of code into safe HTML spans. */
function highlightLine(line: string, lang: string): string {
  const kw = KEYWORDS[lang] ?? [];
  let out = escapeHtml(line);
  // Comments first (# or //), then strings, then keywords.
  out = out.replace(/(^|\s)(#.*)$/, '$1<span class="tok-comment">$2</span>');
  out = out.replace(/(\/\/.*)$/, '<span class="tok-comment">$1</span>');
  out = out.replace(/(&quot;[^&]*?&quot;|&#39;[^&]*?&#39;|"[^"]*"|'[^']*')/g,
    '<span class="tok-string">$1</span>');
  if (kw.length) {
    const re = new RegExp(`\\b(${kw.join('|')})\\b`, 'g');
    out = out.replace(re, '<span class="tok-kw">$1</span>');
  }
  return out;
}

/* ── Copy button ───────────────────────────────────────────────────────── */

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable — silently ignore */
    }
  }, [text]);
  return (
    <button
      type="button"
      className="code-copy-btn"
      onClick={copy}
      aria-label={copied ? 'تم النسخ' : 'نسخ الكود'}
    >
      {copied ? '✓ نُسخ' : '📋 نسخ'}
    </button>
  );
}

/* ── Code block ────────────────────────────────────────────────────────── */

interface CodeBlockProps {
  code: string;
  lang: string;
}

function CodeBlock({ code, lang }: CodeBlockProps) {
  const lines = useMemo(() => {
    const raw = code.replace(/\n$/, '');
    return raw.split('\n').map((l) => highlightLine(l, lang));
  }, [code, lang]);

  return (
    <div className="code-block" dir="ltr">
      <div className="code-block__header">
        <span className="code-block__lang">{lang || 'code'}</span>
        <CopyButton text={code} />
      </div>
      <pre className="code-block__pre">
        <code
          // Safe: every line is HTML-escaped before highlighting.
          dangerouslySetInnerHTML={{ __html: lines.join('\n') }}
        />
      </pre>
    </div>
  );
}

/* ── Exported Markdown view ────────────────────────────────────────────── */

interface MarkdownProps {
  content: string;
}

export function Markdown({ content }: MarkdownProps) {
  return (
    <div className="markdown-body">
      <MarkdownLib
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className ?? '');
            const text = String(children ?? '');
            const isBlock = text.includes('\n') || match !== null;
            if (!isBlock) {
              return (
                <code className="inline-code" dir="ltr" {...props}>
                  {children}
                </code>
              );
            }
            return <CodeBlock code={text} lang={match?.[1] ?? ''} />;
          },
          pre({ children }) {
            // CodeBlock already renders its own <pre>; unwrap wrapper.
            return <>{children}</>;
          },
          a({ children, href }) {
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </MarkdownLib>
    </div>
  );
}
