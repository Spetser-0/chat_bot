/**
 * pages/HomePage.tsx
 * ────────────────────
 * Exact replica of Stitch Project 65770937400041676:
 * - Desktop View (>= 768px): Stitch Perplexity Search Desk with Left Sidebar,
 *   Top Header chips, Mode Badge, Hero, Dominant Search Box, Inquiry Cards Grid,
 *   Live Academic Index, and Keyboard Shortcuts.
 * - Mobile View (< 768px): Stitch Perplexity Mobile with Top Bar (Hamburger, Brand, Profile),
 *   Centered 12-arm Teal Starburst, "Where knowledge begins", and Bottom Floating Dock.
 */
import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { StitchSidebar } from '../components/stitch/StitchSidebar';
import { StitchDesktopHome } from '../components/stitch/StitchDesktopHome';
import { StitchMobileHome } from '../components/stitch/StitchMobileHome';
import { StitchMobileDrawer } from '../components/stitch/StitchMobileDrawer';

export function HomePage() {
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const chat = useChat(
    useCallback(
      (id: string) => navigate(`/chat/${id}`, { replace: true }),
      [navigate],
    ),
  );

  const handleSearch = (query: string, _mode?: string) => {
    if (!query.trim()) return;
    chat.send(query.trim());
  };

  return (
    <div className="w-full min-h-screen bg-parchment text-ink" dir="ltr">
      {/* ── DESKTOP VIEW (Visible on screens >= 768px) ─────────────────── */}
      <div className="hidden md:block">
        <StitchSidebar onNewThread={() => window.scrollTo({ top: 0, behavior: 'smooth' })} />
        <StitchDesktopHome onSearch={handleSearch} isStreaming={chat.isStreaming} />
      </div>

      {/* ── MOBILE VIEW (Visible on screens < 768px) ───────────────────── */}
      <div className="block md:hidden">
        <StitchMobileHome
          onSearch={handleSearch}
          onOpenMenu={() => setMobileMenuOpen(true)}
          isStreaming={chat.isStreaming}
        />
        <StitchMobileDrawer
          isOpen={mobileMenuOpen}
          onClose={() => setMobileMenuOpen(false)}
          onNewThread={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        />
      </div>
    </div>
  );
}
