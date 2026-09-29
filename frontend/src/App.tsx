import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AppShell } from './components/AppShell';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';

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
  
  if (!student || (student.role !== 'developer' && student.role !== 'admin')) {
    return <Navigate to="/" replace />;
  }
  
  return <Outlet />;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            
            {/* Authenticated student routes inside AppShell */}
            <Route element={<RequireAuth />}>
              <Route element={<AppShell><Outlet /></AppShell>}>
                <Route path="/" element={<HomePage />} />
                {/* Placeholders for Phase 2+ */}
                <Route path="/presentations/new" element={
                  <div className="empty-state">
                    <div className="empty-state__icon">🖥️</div>
                    <div className="empty-state__title">العروض التقديمية</div>
                    <div className="empty-state__desc">هذه الميزة سيتم إضافتها في المرحلة الثانية.</div>
                  </div>
                } />
                <Route path="/chat" element={
                  <div className="empty-state">
                    <div className="empty-state__icon">💬</div>
                    <div className="empty-state__title">المحادثة الأكاديمية</div>
                    <div className="empty-state__desc">هذه الميزة سيتم إضافتها في مراحل قادمة.</div>
                  </div>
                } />
                <Route path="/history" element={
                  <div className="empty-state">
                    <div className="empty-state__icon">🕐</div>
                    <div className="empty-state__title">السجل</div>
                    <div className="empty-state__desc">سجل طلباتك سيظهر هنا.</div>
                  </div>
                } />
              </Route>
            </Route>

            {/* Developer Dashboard Route */}
            <Route element={<RequireDeveloper />}>
               <Route path="/developer" element={
                 <div className="app-shell" dir="rtl">
                   <div className="app-shell__content">
                     <h1 className="text-2xl font-semibold mb-4">لوحة المطور (Developer Dashboard)</h1>
                     <p className="text-secondary">This will be implemented in Phase 3.</p>
                     <Link to="/" className="btn btn--secondary mt-4">العودة للرئيسية</Link>
                   </div>
                 </div>
               } />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
