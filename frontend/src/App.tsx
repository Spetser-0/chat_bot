import { Suspense, lazy, type ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { LanguageProvider } from './contexts/LanguageContext';
import { useAuth } from './contexts/useAuth';
import { AppShell } from './components/AppShell';
import { AdminLayout } from './components/admin/AdminLayout';
import { HomePage } from './pages/HomePage';
import { SettingsPage } from './pages/SettingsPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ChatPage } from './pages/ChatPage';
import { ReferralLandingPage } from './pages/ReferralLandingPage';
import { ReferralPage } from './pages/ReferralPage';
import { VerifyEmailPage } from './pages/VerifyEmailPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';

// Admin pages are code-split (Lesson 9.10) so the student bundle stays lean.
const AdminDashboardPage = lazy(() =>
  import('./pages/admin/AdminDashboardPage').then((m) => ({ default: m.AdminDashboardPage })));
const AdminProvidersPage = lazy(() =>
  import('./pages/admin/AdminProvidersPage').then((m) => ({ default: m.AdminProvidersPage })));
const AdminSkillsPage = lazy(() =>
  import('./pages/admin/AdminSkillsPage').then((m) => ({ default: m.AdminSkillsPage })));
const AdminUsersPage = lazy(() =>
  import('./pages/admin/AdminUsersPage').then((m) => ({ default: m.AdminUsersPage })));
const AdminPaymentsPage = lazy(() =>
  import('./pages/admin/AdminPaymentsPage').then((m) => ({ default: m.AdminPaymentsPage })));
const AdminReferralsPage = lazy(() =>
  import('./pages/admin/AdminReferralsPage').then((m) => ({ default: m.AdminReferralsPage })));
const AdminAuditPage = lazy(() =>
  import('./pages/admin/AdminAuditPage').then((m) => ({ default: m.AdminAuditPage })));
const DeveloperPage = lazy(() =>
  import('./pages/DeveloperPage').then((m) => ({ default: m.DeveloperPage })));

function RouteFallback() {
  return (
    <div className="flex items-center justify-center p-8" style={{ minHeight: '40vh' }}>
      <div className="spinner spinner--lg" />
    </div>
  );
}

function LazyAdminPage({ children }: { children: ReactNode }) {
  return (
    <AdminLayout>
      <Suspense fallback={<RouteFallback />}>{children}</Suspense>
    </AdminLayout>
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Guard for routes that require authentication
function RequireAuth() {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="app-shell__content flex items-center justify-center"><div className="spinner spinner--lg" /></div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <Outlet />;
}

// Guard for developer-only routes
function RequireDeveloper() {
  const { student, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="app-shell__content flex items-center justify-center"><div className="spinner spinner--lg" /></div>;
  }
  
  if (!student || !['developer', 'admin', 'superadmin'].includes(student.role)) {
    return <Navigate to="/" replace />;
  }
  
  return <Outlet />;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <LanguageProvider>
          <BrowserRouter>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/verify-email" element={<VerifyEmailPage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              {/* Referral landing (Phase 9, Lesson 9.3) — validates code, funnels to register */}
              <Route path="/r/:code" element={<ReferralLandingPage />} />
              
              {/* Routes inside AppShell */}
              <Route element={<AppShell><Outlet /></AppShell>}>
                <Route path="/" element={<HomePage />} />
                {/* Authenticated student routes */}
                <Route element={<RequireAuth />}>
                  {/* Placeholders for Phase 2+ */}
                  <Route path="/presentations/new" element={
                    <div className="empty-state">
                      <div className="empty-state__icon">🖥️</div>
                      <div className="empty-state__title">العروض التقديمية</div>
                      <div className="empty-state__desc">هذه الميزة سيتم إضافتها في المرحلة الثانية.</div>
                    </div>
                  } />
                  <Route path="/chat" element={<ChatPage />} />
                  <Route path="/chat/:conversationId" element={<ChatPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                  <Route path="/history" element={
                    <div className="empty-state">
                      <div className="empty-state__icon">🕐</div>
                      <div className="empty-state__title">السجل</div>
                      <div className="empty-state__desc">سجل طلباتك سيظهر هنا.</div>
                    </div>
                  } />
                  <Route path="/referrals" element={<ReferralPage />} />
                </Route>
              </Route>

              {/* Admin dashboard (Phase 9, Lessons 9.8 + 9.10 code-split) */}
              <Route element={<RequireDeveloper />}>
                <Route path="/admin" element={<LazyAdminPage><AdminDashboardPage /></LazyAdminPage>} />
                <Route path="/admin/providers" element={<LazyAdminPage><AdminProvidersPage /></LazyAdminPage>} />
                <Route path="/admin/skills" element={<LazyAdminPage><AdminSkillsPage /></LazyAdminPage>} />
                <Route path="/admin/users" element={<LazyAdminPage><AdminUsersPage /></LazyAdminPage>} />
                <Route path="/admin/payments" element={<LazyAdminPage><AdminPaymentsPage /></LazyAdminPage>} />
                <Route path="/admin/referrals" element={<LazyAdminPage><AdminReferralsPage /></LazyAdminPage>} />
                <Route path="/admin/audit" element={<LazyAdminPage><AdminAuditPage /></LazyAdminPage>} />
                <Route path="/developer" element={<LazyAdminPage><DeveloperPage /></LazyAdminPage>} />
              </Route>

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </LanguageProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
