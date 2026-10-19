import { useState, useRef, useEffect, type KeyboardEvent, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/useAuth';

interface StitchDesktopHomeProps {
  onSearch: (query: string, mode?: string) => void;
  isStreaming?: boolean;
}

export function StitchDesktopHome({ onSearch, isStreaming = false }: StitchDesktopHomeProps) {
  const navigate = useNavigate();
  const { student } = useAuth();

  const [query, setQuery] = useState('');
  const [activeMode, setActiveMode] = useState<'search' | 'deep' | 'academic' | 'writing'>('search');
  const [isPro, setIsPro] = useState(false);
  const [activeCategory, setActiveCategory] = useState('Discover');
  const [files, setFiles] = useState<File[]>([]);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const categories = ['Discover', 'Academic', 'Finance', 'Health', 'Patents'];

  const templates = [
    {
      icon: 'token',
      badge: 'NEW',
      title: 'Synthesize recent findings in quantum annealing',
      desc: 'Cross-correlate decoherence suppression techniques and Ising spin-glass benchmark papers.',
      source: 'arXiv:2403 • Physical Sciences',
    },
    {
      icon: 'show_chart',
      badge: '10-Q SEC',
      title: 'Analyze quarterly revenue trends for S&P 500 tech',
      desc: 'Extract guidance revisions, cloud infrastructure CAPEX, and forward P/E multiples.',
      source: 'Q3 Filings • Equities',
    },
    {
      icon: 'biotech',
      badge: 'PubMed Central',
      title: 'Explain mechanisms of CRISPR base editing',
      desc: 'Contrast cytidine and adenine deaminases with prime editing efficiency margins.',
      source: 'Cell Mol Bio • Peer-reviewed',
    },
    {
      icon: 'gavel',
      badge: 'USPTO / EPO',
      title: 'Draft a patent claim for autonomous navigation sensors',
      desc: 'Structure independent apparatus claims highlighting multi-spectral LiDAR time-of-flight arrays.',
      source: 'Intellectual Property • Claims',
    },
  ];

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if (!query.trim() || isStreaming) return;
    onSearch(query.trim(), activeMode);
  };

  const handleTemplateClick = (title: string) => {
    setQuery(title);
    if (textareaRef.current) {
      textareaRef.current.focus();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  // Keyboard shortcut listener: Tab to focus search, Esc to blur
  useEffect(() => {
    const handleGlobalKeys = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Tab' && document.activeElement !== textareaRef.current) {
        e.preventDefault();
        textareaRef.current?.focus();
      } else if (e.key === 'Escape' && document.activeElement === textareaRef.current) {
        textareaRef.current?.blur();
      }
    };
    window.addEventListener('keydown', handleGlobalKeys);
    return () => window.removeEventListener('keydown', handleGlobalKeys);
  }, []);

  return (
    <div className="min-h-screen bg-parchment text-on-surface font-body-md text-body-md antialiased select-auto">
      {/* ── Fixed Desktop Top Header ───────────────────────────────────── */}
      <header className="fixed top-0 left-64 right-0 h-16 bg-parchment/90 backdrop-blur-md border-b border-warm-mist z-40 flex items-center justify-between px-space-xl">
        <div className="flex items-center gap-space-lg">
          <nav className="flex items-center gap-space-xs">
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setActiveCategory(cat)}
                className={`px-space-md py-space-xs rounded-full border border-warm-mist font-label-sm text-label-sm transition-colors cursor-pointer ${
                  activeCategory === cat
                    ? 'bg-primary-container text-on-primary font-medium'
                    : 'text-graphite hover:bg-surface-container-high hover:text-on-surface'
                }`}
              >
                {cat}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-space-sm">
          <button
            onClick={() => {
              setQuery('');
              textareaRef.current?.focus();
            }}
            className="flex items-center gap-space-xs px-space-md py-space-xs bg-ink text-soft-paper rounded hover:bg-pure-black transition-colors font-label-sm text-label-sm cursor-pointer shadow-sm"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px]">add</span>
            <span>New</span>
          </button>
          <div
            onClick={() => navigate('/settings')}
            className="w-8 h-8 rounded-full bg-primary flex items-center justify-center cursor-pointer shadow-sm hover:opacity-90"
            title={student?.display_name || 'Account'}
          >
            <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
          </div>
        </div>
      </header>

      {/* ── Main Canvas (Centered 900px, pt-16) ─────────────────────────── */}
      <main className="relative pt-16 bg-parchment min-h-screen">
        <div className="max-w-[900px] mx-auto px-margin-desktop py-space-xl">
          <div className="flex flex-col w-full items-center">
            {/* Top Mode Badge */}
            <div className="flex flex-col items-center justify-center pt-space-md pb-space-xl">
              <div className="flex items-center gap-space-sm mb-space-xl">
                <div className="flex items-center gap-space-xs px-space-md py-space-xs rounded-full bg-soft-paper shadow-sm border border-warm-mist/60">
                  <span className="w-2 h-2 rounded-full bg-deep-teal animate-pulse"></span>
                  <span className="font-label-xs text-label-xs text-graphite uppercase tracking-wider">Workspace Mode</span>
                  <span className="font-label-xs text-label-xs text-ash">•</span>
                  <span className="font-label-xs text-label-xs text-ink font-medium">Consensus 3.4 Active</span>
                </div>
              </div>

              {/* Central Hero Header */}
              <div className="text-center mb-space-xl max-w-xl">
                <h1 className="font-headline-lg text-[28px] text-ink font-normal tracking-tight mb-space-xs">
                  Where knowledge begins
                </h1>
                <p className="font-body-md text-body-md text-graphite font-normal">
                  Synthesize literature, analyze empirical datasets, and cross-reference citations.
                </p>
              </div>

              {/* Dominant Central Search Box */}
              <div className="w-full max-w-[640px] mb-space-xl">
                <div
                  className="w-full bg-soft-paper rounded-xl shadow-sm hover:shadow-md focus-within:shadow-md p-space-lg flex flex-col gap-space-md border border-warm-mist transition-all duration-200"
                  id="search-container"
                >
                  {/* Textarea inquiry field */}
                  <div className="relative w-full">
                    <textarea
                      ref={textareaRef}
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={handleKeyDown}
                      className="w-full bg-transparent border-0 resize-none outline-none font-body-lg text-body-lg text-ink placeholder:text-graphite font-normal leading-relaxed p-0 selection:bg-secondary-container"
                      id="search-input"
                      placeholder="Ask anything or search the web..."
                      rows={3}
                      dir="auto"
                    />
                  </div>

                  {/* Attached file badges if any */}
                  {files.length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {files.map((f, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-container text-ink font-label-xs text-xs border border-warm-mist"
                        >
                          <span className="material-symbols-outlined text-[14px]">attachment</span>
                          <span className="truncate max-w-[150px]">{f.name}</span>
                          <button
                            type="button"
                            onClick={() => setFiles(files.filter((_, idx) => idx !== i))}
                            className="text-graphite hover:text-ink ml-1"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Embedded Controls Row */}
                  <div className="flex items-center justify-between gap-space-sm pt-space-xs border-t border-warm-mist/40">
                    {/* Search Mode Pill Chips */}
                    <div className="flex items-center gap-space-xs flex-wrap" id="mode-pills">
                      <button
                        type="button"
                        onClick={() => setActiveMode('search')}
                        className={`mode-btn px-space-md py-space-xs rounded-full font-label-sm text-label-sm transition-all flex items-center gap-1 cursor-pointer ${
                          activeMode === 'search'
                            ? 'bg-deep-teal text-soft-paper font-medium'
                            : 'bg-surface-container text-graphite hover:text-ink font-normal'
                        }`}
                      >
                        <span className="material-symbols-outlined text-[15px]">globe</span>
                        <span>Search</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setActiveMode('deep')}
                        className={`mode-btn px-space-md py-space-xs rounded-full font-label-sm text-label-sm transition-all flex items-center gap-1 cursor-pointer ${
                          activeMode === 'deep'
                            ? 'bg-deep-teal text-soft-paper font-medium'
                            : 'bg-surface-container text-graphite hover:text-ink font-normal'
                        }`}
                      >
                        <span className="material-symbols-outlined text-[15px]">psychology</span>
                        <span>Deep Research</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setActiveMode('academic')}
                        className={`mode-btn px-space-md py-space-xs rounded-full font-label-sm text-label-sm transition-all flex items-center gap-1 cursor-pointer ${
                          activeMode === 'academic'
                            ? 'bg-deep-teal text-soft-paper font-medium'
                            : 'bg-surface-container text-graphite hover:text-ink font-normal'
                        }`}
                      >
                        <span className="material-symbols-outlined text-[15px]">school</span>
                        <span>Academic</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setActiveMode('writing')}
                        className={`mode-btn px-space-md py-space-xs rounded-full font-label-sm text-label-sm transition-all flex items-center gap-1 cursor-pointer ${
                          activeMode === 'writing'
                            ? 'bg-deep-teal text-soft-paper font-medium'
                            : 'bg-surface-container text-graphite hover:text-ink font-normal'
                        }`}
                      >
                        <span className="material-symbols-outlined text-[15px]">edit_note</span>
                        <span>Writing</span>
                      </button>
                    </div>

                    {/* Action Buttons Group */}
                    <div className="flex items-center gap-space-xs shrink-0">
                      <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        className="hidden"
                        onChange={handleFileChange}
                      />
                      {/* Attach File Button */}
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-graphite hover:text-ink hover:bg-surface-container transition-colors cursor-pointer"
                        title="Attach document or reference"
                      >
                        <span className="material-symbols-outlined text-[18px]">attach_file</span>
                      </button>

                      {/* Pro Toggle Pill */}
                      <button
                        type="button"
                        onClick={() => setIsPro(!isPro)}
                        className={`flex items-center gap-1 px-space-sm py-space-xs rounded-full transition-colors font-label-xs text-label-xs cursor-pointer ${
                          isPro
                            ? 'bg-deep-teal text-soft-paper'
                            : 'bg-surface-container text-graphite hover:text-ink'
                        }`}
                        title="Toggle Pro mode"
                      >
                        <span
                          className={`material-symbols-outlined text-[14px] ${isPro ? 'text-soft-paper' : 'text-deep-teal'}`}
                          style={{ fontVariationSettings: "'FILL' 1" }}
                        >
                          bolt
                        </span>
                        <span className="font-medium">Pro</span>
                      </button>

                      {/* Submit Action Button */}
                      <button
                        type="button"
                        onClick={handleSubmit}
                        disabled={!query.trim() || isStreaming}
                        className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors cursor-pointer ${
                          query.trim() && !isStreaming
                            ? 'bg-ink text-soft-paper hover:bg-pure-black shadow-sm'
                            : 'bg-surface-container text-graphite opacity-60 cursor-not-allowed'
                        }`}
                        title="Submit Inquiry"
                      >
                        <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Suggestion Cards Grid (2-column layout) */}
              <div className="w-full max-w-[640px] flex flex-col gap-space-md mb-space-xl">
                <div className="flex items-center justify-between px-space-xs">
                  <span className="font-label-xs text-label-xs text-ash uppercase tracking-wider">
                    Inquiry Templates
                  </span>
                  <span
                    onClick={() => handleTemplateClick('Synthesize recent papers in physical and machine intelligence')}
                    className="font-label-xs text-label-xs text-graphite hover:text-ink cursor-pointer transition-colors"
                  >
                    View Library
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md w-full">
                  {templates.map((card, i) => (
                    <div
                      key={i}
                      onClick={() => handleTemplateClick(card.title)}
                      className="suggestion-card bg-soft-paper rounded-xl p-space-lg shadow-sm hover:shadow-md hover:bg-surface-container-low transition-all cursor-pointer flex flex-col justify-between group border border-warm-mist/60"
                    >
                      <div className="flex flex-col gap-space-xs mb-space-md">
                        <div className="flex items-center justify-between mb-space-xs">
                          <span className="material-symbols-outlined text-ink text-[20px] group-hover:text-deep-teal transition-colors">
                            {card.icon}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded-full font-label-xs text-label-xs font-medium ${
                              card.badge === 'NEW'
                                ? 'bg-deep-teal text-soft-paper'
                                : 'text-ash border border-warm-mist/60'
                            }`}
                          >
                            {card.badge}
                          </span>
                        </div>
                        <h3 className="font-headline-sm text-headline-sm text-ink font-normal leading-snug group-hover:text-deep-teal transition-colors">
                          {card.title}
                        </h3>
                        <p className="font-body-md text-body-md text-graphite font-normal line-clamp-2">
                          {card.desc}
                        </p>
                      </div>
                      <div className="flex items-center gap-space-xs pt-space-xs border-t border-warm-mist/30">
                        <span className="font-label-xs text-label-xs text-ash font-medium">{card.source}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Contextual Research Density Row / Data Snapshot */}
              <div className="w-full max-w-[640px] bg-soft-paper rounded-xl p-space-lg shadow-sm mb-space-xl flex flex-col gap-space-md border border-warm-mist/60">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-space-xs">
                    <span className="material-symbols-outlined text-deep-teal text-[18px]">history_edu</span>
                    <span className="font-label-sm text-label-sm text-ink font-medium">Live Academic Index</span>
                  </div>
                  <span className="font-label-xs text-label-xs text-ash">Updated 14m ago</span>
                </div>
                <div className="grid grid-cols-3 gap-space-md text-center py-space-xs">
                  <div className="flex flex-col items-center">
                    <span className="font-headline-md text-headline-md text-ink font-medium">214.8M</span>
                    <span className="font-label-xs text-label-xs text-graphite">Citations Mapped</span>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="font-headline-md text-headline-md text-ink font-medium">98.4%</span>
                    <span className="font-label-xs text-label-xs text-graphite">DOI Grounding</span>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="font-headline-md text-headline-md text-ink font-medium">1,420</span>
                    <span className="font-label-xs text-label-xs text-graphite">Active Repositories</span>
                  </div>
                </div>
              </div>

              {/* Keyboard Shortcut and Footnote Row */}
              <div className="flex items-center justify-center gap-space-sm text-center">
                <span className="font-label-sm text-label-sm text-ash font-normal">
                  Tab to focus &nbsp;•&nbsp; Esc to close &nbsp;•&nbsp; ⌘K for commands
                </span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
