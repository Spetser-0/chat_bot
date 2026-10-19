import { useState, useRef, useEffect, type KeyboardEvent, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';

interface StitchMobileHomeProps {
  onSearch: (query: string, mode?: string) => void;
  onOpenMenu: () => void;
  isStreaming?: boolean;
}

export function StitchMobileHome({ onSearch, onOpenMenu, isStreaming = false }: StitchMobileHomeProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [selectedModel, setSelectedModel] = useState('Claude 3.5 Sonnet');
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [currentTime, setCurrentTime] = useState('1:48');

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const availableModels = ['Claude 3.5 Sonnet', 'GPT-4o', 'Sonar Deep', 'Gemini 1.5 Pro'];

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const hours = now.getHours();
      const minutes = now.getMinutes().toString().padStart(2, '0');
      setCurrentTime(`${hours % 12 || 12}:${minutes}`);
    };
    updateTime();
    const interval = setInterval(updateTime, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = () => {
    if (!query.trim() || isStreaming) return;
    onSearch(query.trim());
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  return (
    <div className="bg-parchment font-sans text-ink flex flex-col justify-between min-h-screen relative overflow-hidden select-none antialiased">
      {/* ── Status Bar Simulation & Top Bar ──────────────────────────────── */}
      <header className="w-full pt-safe z-30 flex flex-col pt-1">
        {/* Top System Indicators */}
        <div className="px-6 pt-2 pb-1 flex items-center justify-between text-xs text-graphite tracking-normal font-sans">
          <div className="flex items-center gap-1.5 font-medium text-[13px]">
            <span>{currentTime}</span>
            <span className="material-symbols-outlined text-[13px] text-graphite">sentiment_satisfied</span>
            <span className="material-symbols-outlined text-[13px] text-graphite">near_me</span>
          </div>
          <div className="flex items-center gap-1.5 text-[12px]">
            <span className="material-symbols-outlined text-[14px]">wifi</span>
            <span className="text-[11px] font-semibold">4G</span>
            <span className="material-symbols-outlined text-[14px]">signal_cellular_alt</span>
            <div className="flex items-center border border-warm-mist rounded-full px-1 text-[10px] leading-tight text-graphite font-medium">
              33
            </div>
          </div>
        </div>

        {/* Main Navigation Bar */}
        <div className="px-5 h-12 flex items-center justify-between mt-1">
          {/* Minimalist Hamburger Menu */}
          <button
            onClick={onOpenMenu}
            aria-label="Menu"
            className="w-10 h-10 flex flex-col justify-center items-start gap-1.5 text-graphite hover:text-ink transition-colors focus:outline-none cursor-pointer"
          >
            <span className="w-4 h-[1.75px] bg-ink rounded-full"></span>
            <span className="w-4 h-[1.75px] bg-ink rounded-full"></span>
            <span className="w-2.5 h-[1.75px] bg-ink rounded-full"></span>
          </button>

          {/* Wordmark / Center Brand */}
          <div className="flex items-center gap-1.5">
            <span className="font-sans font-medium text-[15px] tracking-tight text-ink">Perplexity</span>
          </div>

          {/* Profile Avatar Outline / Settings */}
          <button
            onClick={() => navigate('/settings')}
            aria-label="Profile"
            className="w-9 h-9 flex items-center justify-center text-graphite hover:text-ink transition-colors focus:outline-none cursor-pointer"
          >
            <span className="material-symbols-outlined text-[24px]">account_circle</span>
          </button>
        </div>
      </header>

      {/* ── Central Focal Hero Area ──────────────────────────────────────── */}
      <main className="flex-1 flex flex-col items-center justify-center -mt-16 px-6 text-center z-10">
        {/* Stylized Perplexity Asterisk / Starburst in Deep Teal (Stitch exact SVG) */}
        <div className="mb-5 text-deep-teal flex items-center justify-center">
          <svg
            className="text-deep-teal transition-transform hover:scale-105 duration-200"
            fill="currentColor"
            height="42"
            viewBox="0 0 24 24"
            width="42"
          >
            <g transform="translate(12,12)">
              <path d="M-1,-11.5 C-1,-12 1,-12 1,-11.5 L1,-2.5 C1,-1.5 -1,-1.5 -1,-2.5 Z"></path>
              <path d="M-1,-11.5 C-1,-12 1,-12 1,-11.5 L1,-2.5 C1,-1.5 -1,-1.5 -1,-2.5 Z" transform="rotate(30)"></path>
              <path d="M-1,-11.5 C-1,-12 1,-12 1,-11.5 L1,-2.5 C1,-1.5 -1,-1.5 -1,-2.5 Z" transform="rotate(60)"></path>
              <path d="M-1,-11.5 C-1,-12 1,-12 1,-11.5 L1,-2.5 C1,-1.5 -1,-1.5 -1,-2.5 Z" transform="rotate(90)"></path>
              <path d="M-1,-11.5 C-1,-12 1,-12 1,-11.5 L1,-2.5 C1,-1.5 -1,-1.5 -1,-2.5 Z" transform="rotate(120)"></path>
              <path d="M-1,-11.5 C-1,-12 1,-12 1,-11.5 L1,-2.5 C1,-1.5 -1,-1.5 -1,-2.5 Z" transform="rotate(150)"></path>
              <path d="M-1,-11.5 C-1,-12 1,-12 1,-11.5 L1,-2.5 C1,-1.5 -1,-1.5 -1,-2.5 Z" transform="rotate(180)"></path>
              <path d="M-1,-11.5 C-1,-12 1,-12 1,-11.5 L1,-2.5 C1,-1.5 -1,-1.5 -1,-2.5 Z" transform="rotate(210)"></path>
              <path d="M-1,-11.5 C-1,-12 1,-12 1,-11.5 L1,-2.5 C1,-1.5 -1,-1.5 -1,-2.5 Z" transform="rotate(240)"></path>
              <path d="M-1,-11.5 C-1,-12 1,-12 1,-11.5 L1,-2.5 C1,-1.5 -1,-1.5 -1,-2.5 Z" transform="rotate(270)"></path>
              <path d="M-1,-11.5 C-1,-12 1,-12 1,-11.5 L1,-2.5 C1,-1.5 -1,-1.5 -1,-2.5 Z" transform="rotate(300)"></path>
              <path d="M-1,-11.5 C-1,-12 1,-12 1,-11.5 L1,-2.5 C1,-1.5 -1,-1.5 -1,-2.5 Z" transform="rotate(330)"></path>
            </g>
          </svg>
        </div>

        {/* Scholar's Parchment Clean Sans Title */}
        <h1 className="font-sans text-[26px] sm:text-[30px] text-ink font-medium tracking-tight">
          Where knowledge begins
        </h1>
        <p className="text-graphite text-[13px] font-normal mt-1 tracking-normal">
          Ask anything or search with curated sources
        </p>
      </main>

      {/* ── Bottom Floating Chat Input Dock Container ─────────────────────── */}
      <footer className="w-full px-3 pb-safe z-30 pb-3">
        <div className="w-full rounded-[24px] bg-soft-paper border border-warm-mist shadow-card overflow-hidden flex flex-col">
          {/* Pro Upgrade / Status Banner Row */}
          <div className="px-4 py-2.5 flex items-center justify-between border-b border-warm-mist/60 bg-parchment/60">
            <span className="text-[12px] text-graphite font-normal">
              Get deeper research with Pro
            </span>
            <button
              type="button"
              onClick={() => navigate('/settings')}
              className="text-[12px] text-deep-teal font-medium hover:underline focus:outline-none tracking-tight cursor-pointer"
            >
              Try Pro
            </button>
          </div>

          {/* Attached Files on Mobile */}
          {files.length > 0 && (
            <div className="px-3.5 pt-2 flex flex-wrap gap-1.5">
              {files.map((f, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container text-ink text-[11px] border border-warm-mist"
                >
                  <span className="material-symbols-outlined text-[12px]">attachment</span>
                  <span className="truncate max-w-[120px]">{f.name}</span>
                  <button
                    type="button"
                    onClick={() => setFiles(files.filter((_, idx) => idx !== i))}
                    className="text-graphite ml-1"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Main Input Field Area */}
          <div className="px-3.5 pt-3 pb-1.5">
            <div className="w-full bg-parchment rounded-[12px] border border-warm-mist px-3 py-2.5 transition-colors focus-within:border-deep-teal">
              <textarea
                ref={textareaRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full bg-transparent text-ink placeholder-graphite text-[15px] outline-none resize-none leading-relaxed font-sans border-0 p-0 focus:ring-0"
                placeholder="Ask anything..."
                rows={1}
                dir="auto"
              />
            </div>
          </div>

          {/* Action & Controls Row */}
          <div className="px-3 pb-3 pt-1 flex items-center justify-between gap-2 relative">
            {/* Left Controls: Plus Attach & Model Selector Chip */}
            <div className="flex items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={handleFileChange}
              />
              {/* Circular Attachment (+) Button */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-8 h-8 rounded-full bg-parchment border border-warm-mist text-graphite flex items-center justify-center hover:text-ink hover:border-ash active:scale-95 transition-all focus:outline-none shadow-subtle cursor-pointer"
                title="Attach document"
              >
                <span className="material-symbols-outlined text-[18px]">add</span>
              </button>

              {/* Model Selector Chip */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setModelMenuOpen(!modelMenuOpen)}
                  className="h-8 px-3 rounded-full bg-parchment border border-warm-mist text-ink text-[12px] font-medium flex items-center gap-1.5 hover:border-ash active:scale-95 transition-all focus:outline-none shadow-subtle cursor-pointer"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-deep-teal"></span>
                  <span>{selectedModel}</span>
                </button>

                {modelMenuOpen && (
                  <div className="absolute bottom-10 left-0 bg-soft-paper border border-warm-mist rounded-xl shadow-lg p-1 min-w-[170px] z-50 flex flex-col gap-1">
                    {availableModels.map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => {
                          setSelectedModel(m);
                          setModelMenuOpen(false);
                        }}
                        className={`px-3 py-1.5 text-left text-xs rounded-lg transition-colors flex items-center justify-between ${
                          selectedModel === m
                            ? 'bg-primary-container text-on-primary font-medium'
                            : 'text-ink hover:bg-surface-container'
                        }`}
                      >
                        <span>{m}</span>
                        {selectedModel === m && <span className="text-xs">✓</span>}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Controls: Mic & Voice/Submit Pill */}
            <div className="flex items-center gap-2">
              {/* Microphone Button */}
              <button
                type="button"
                className="w-8 h-8 rounded-full bg-parchment border border-warm-mist text-graphite flex items-center justify-center hover:text-ink hover:border-ash active:scale-95 transition-all focus:outline-none shadow-subtle cursor-pointer"
                title="Dictate voice"
              >
                <span className="material-symbols-outlined text-[17px]">mic</span>
              </button>

              {/* Voice / Submit Pill Button (Deep Teal) */}
              <button
                type="button"
                onClick={handleSubmit}
                aria-label={query.trim() ? 'Submit query' : 'Voice conversation'}
                className="w-8 h-8 rounded-full bg-deep-teal text-white flex items-center justify-center hover:opacity-90 active:scale-95 transition-all shadow-subtle focus:outline-none cursor-pointer"
              >
                {query.trim() ? (
                  <span className="material-symbols-outlined text-[16px] text-white">arrow_forward</span>
                ) : (
                  <div className="flex items-center justify-center gap-[2px] h-3.5">
                    <span className="w-[1.75px] h-1.5 bg-white rounded-full animate-pulse"></span>
                    <span className="w-[1.75px] h-3 bg-white rounded-full animate-pulse" style={{ animationDelay: '100ms' }}></span>
                    <span className="w-[1.75px] h-3.5 bg-white rounded-full animate-pulse" style={{ animationDelay: '200ms' }}></span>
                    <span className="w-[1.75px] h-2 bg-white rounded-full animate-pulse" style={{ animationDelay: '300ms' }}></span>
                    <span className="w-[1.75px] h-1 bg-white rounded-full animate-pulse" style={{ animationDelay: '400ms' }}></span>
                  </div>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Bottom Mobile Home Indicator Bar */}
        <div className="w-full flex justify-center pt-2.5 pb-1">
          <div className="w-32 h-[4px] bg-warm-mist rounded-full"></div>
        </div>
      </footer>
    </div>
  );
}
