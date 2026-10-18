/**
 * pages/HomePage.tsx
 * ────────────────────
 * Chat-first home: greeting, floating quick-action chips, the composer and a
 * grid of the latest conversations.
 */
import { useCallback, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Sparkles } from 'lucide-react';
import { useAuth } from '../contexts/useAuth';
import { Composer } from '../components/chat/Composer';
import { QuickActions } from '../components/chat/QuickActions';
import { useChat } from '../hooks/useChat';
import { conversationsApi } from '../api/conversations';
import type { QuickActionId } from '../lib/quickActions';

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return 'الآن';
  if (minutes < 60) return `قبل ${minutes} د`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `قبل ${hours} س`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `قبل ${days} يوم`;
  return new Date(iso).toLocaleDateString('ar');
}

const QUICK_LABELS: Record<QuickActionId, string> = {
  presentation: 'إنشاء عرض تقديمي',
  math: 'حل مسائل رياضية',
  report: 'كتابة بحث / تقرير',
};

export function HomePage() {
  const { student, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const [quickAction, setQuickAction] = useState<QuickActionId | null>(null);

  const chat = useChat(
    useCallback(
      (id: string) => navigate(`/chat/${id}`, { replace: true }),
      [navigate],
    ),
  );

  const { data: conversations = [] } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => conversationsApi.list(),
    enabled: isAuthenticated,
  });


  if (isLoading) {
    return (
      <div className="empty-state">
        <div className="spinner spinner--lg" aria-label="جار التحميل..." />
      </div>
    );
  }

  const latest = conversations.slice(0, 4);
  const greeting = isAuthenticated && student
    ? `أهلاً، ${student.display_name || 'بك'}`
    : 'مرحباً بك';

  return (
    <div className="fade-in home">
      {/* ── Hero / composer ─────────────────────────────────────────── */}
      <section className="home__hero" aria-labelledby="home-heading">
        <div className="home__mark" aria-hidden="true">
          <Sparkles size={34} strokeWidth={1.6} />
        </div>
        <h1 id="home-heading" className="home__heading">{greeting}</h1>
        <p className="home__subtitle">اسأل أي شيء، أو ابدأ من أحد الأزرار بالأسفل</p>

        <QuickActions active={quickAction} onChange={setQuickAction} />
        <Composer
          onSend={(text) => chat.send(text)}
          onStop={chat.stop}
          isStreaming={chat.isStreaming}
          modeLabel={quickAction ? QUICK_LABELS[quickAction] : null}
          onClearMode={() => setQuickAction(null)}
        />

      </section>

      {/* ── Latest chats ────────────────────────────────────────────── */}
      {isAuthenticated && (
        <section aria-labelledby="home-latest" className="home__latest">
          <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-3)' }}>
            <h2 id="home-latest" className="home__section-title">أحدث المحادثات</h2>
            <Link to="/history" className="btn btn--ghost btn--sm">
              عرض الكل
            </Link>
          </div>

          {latest.length === 0 ? (
            <div className="empty-state card">
              <div className="empty-state__icon" aria-hidden="true"><Sparkles size={34} /></div>
              <div className="empty-state__title">لا توجد محادثات بعد</div>
              <div className="empty-state__desc">
                ابدأ بطرح سؤال أو إنشاء عرض تقديمي لترى نتائجك هنا.
              </div>
            </div>
          ) : (
            <div className="feature-grid">
              {latest.map((c) => (
                <Link
                  key={c.id}
                  to={`/chat/${c.id}`}
                  className="feature-card"
                  aria-label={`فتح المحادثة ${c.title}`}
                >
                  <div className="feature-card__icon" aria-hidden="true">
                    <Sparkles size={20} />
                  </div>
                  <div className="feature-card__title">{c.title}</div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="feature-card__desc">{timeAgo(c.updated_at)}</span>
                    <ArrowLeft size={14} aria-hidden="true" className="text-muted" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
