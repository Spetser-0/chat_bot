/**
 * pages/HomePage.tsx
 * ────────────────────
 * Student home — calm academic workspace, Arabic-first.
 * Features: feature selection, recent requests, credit display.
 */
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface Feature {
  id: string;
  icon: string;
  title: string;
  description: string;
  href: string;
  available: boolean;
  accent?: boolean;
}

const FEATURES: Feature[] = [
  {
    id: 'presentation',
    icon: '🖥️',
    title: 'عرض تقديمي',
    description: 'أنشئ عروضاً تقديمية أكاديمية احترافية بالعربية أو الإنجليزية',
    href: '/presentations/new',
    available: true,
    accent: true,
  },
  {
    id: 'chat',
    icon: '💬',
    title: 'محادثة أكاديمية',
    description: 'اطرح أسئلتك واحصل على شرح واضح لأي موضوع دراسي',
    href: '/chat',
    available: true,
  },
  {
    id: 'research',
    icon: '📚',
    title: 'مساعد البحث',
    description: 'أنشئ أوراقاً بحثية أكاديمية بمصادر موثّقة',
    href: '/research',
    available: false,
  },
  {
    id: 'questions',
    icon: '🔢',
    title: 'حل المسائل',
    description: 'احل المسائل الرياضية والعلمية خطوة بخطوة',
    href: '/questions',
    available: false,
  },
];

export function HomePage() {
  const { student, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="empty-state">
        <div className="spinner spinner--lg" aria-label="جار التحميل..." />
      </div>
    );
  }

  return (
    <div className="fade-in">
      {/* Hero */}
      <section aria-labelledby="hero-heading" style={{ marginBottom: 'var(--space-8)' }}>
        {isAuthenticated && student ? (
          <>
            <h2 id="hero-heading" className="section-title">
              أهلاً، {student.display_name || 'بك'} 👋
            </h2>
            <p className="section-subtitle">
              مساعدك الأكاديمي جاهز. ماذا تريد أن تنجز اليوم؟
            </p>
          </>
        ) : (
          <>
            <h2 id="hero-heading" style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-semibold)', color: 'var(--color-ink)', marginBottom: 'var(--space-3)' }}>
              مساعدك الأكاديمي الذكي
            </h2>
            <p className="section-subtitle" style={{ maxWidth: 480, marginBottom: 'var(--space-6)' }}>
              Spetser AI يساعدك في إنشاء العروض التقديمية والأبحاث الأكاديمية وحل المسائل بأسلوب واضح وموثوق.
            </p>
            <div className="flex gap-3">
              <Link to="/register" className="btn btn--primary">
                ابدأ مجاناً
              </Link>
              <Link to="/login" className="btn btn--secondary">
                تسجيل الدخول
              </Link>
            </div>
          </>
        )}
      </section>

      {/* Feature grid */}
      <section aria-labelledby="features-heading" style={{ marginBottom: 'var(--space-8)' }}>
        <h3 id="features-heading" className="sr-only">الميزات المتاحة</h3>
        <div className="feature-grid">
          {FEATURES.map((feature) => (
            <FeatureCard
              key={feature.id}
              feature={feature}
              onClick={() => {
                if (!isAuthenticated) {
                  navigate('/login');
                  return;
                }
                if (feature.available) {
                  navigate(feature.href);
                }
              }}
            />
          ))}
        </div>
      </section>

      {/* Recent activity placeholder */}
      {isAuthenticated && (
        <section aria-labelledby="recent-heading">
          <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-4)' }}>
            <h3 id="recent-heading" className="text-base font-semibold text-primary">
              الطلبات الأخيرة
            </h3>
            <Link to="/history" className="btn btn--ghost btn--sm">
              عرض الكل
            </Link>
          </div>
          <div className="empty-state card" style={{ padding: 'var(--space-8)' }}>
            <div className="empty-state__icon" aria-hidden="true">📂</div>
            <div className="empty-state__title">لا يوجد طلبات بعد</div>
            <div className="empty-state__desc">
              ابدأ بإنشاء عرض تقديمي أو طرح سؤال لترى نتائجك هنا.
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

interface FeatureCardProps {
  feature: Feature;
  onClick: () => void;
}

function FeatureCard({ feature, onClick }: FeatureCardProps) {
  return (
    <button
      className={`feature-card${!feature.available ? ' feature-card--disabled' : ''}`}
      onClick={onClick}
      disabled={!feature.available}
      aria-disabled={!feature.available}
      aria-label={`${feature.title}${!feature.available ? ' — قريباً' : ''}`}
      type="button"
    >
      <div className="feature-card__icon" aria-hidden="true">{feature.icon}</div>
      <div className="flex items-center gap-2">
        <span className="feature-card__title">{feature.title}</span>
        {feature.accent && feature.available && (
          <span className="badge badge--new">جديد</span>
        )}
        {!feature.available && (
          <span className="badge badge--muted">قريباً</span>
        )}
      </div>
      <p className="feature-card__desc">{feature.description}</p>
    </button>
  );
}
