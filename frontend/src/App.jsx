import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from '@/components/shared/ToastContainer';
import { AccessibilityBar } from '@/components/shared/AccessibilityBar';
import { useAuth } from '@/hooks/useAuth';

/* Lazy loading de páginas para code-splitting */
const Home = lazy(() => import('@/pages/Home/index'));
const Search = lazy(() => import('@/pages/Search/index'));
const Detail = lazy(() => import('@/pages/Detail/index'));
const Login = lazy(() => import('@/pages/Login/index'));
const Dashboard = lazy(() => import('@/pages/Dashboard/index'));

/**
 * ProtectedRoute — Redirige a /login si no hay sesión activa.
 * @param {{ children: React.ReactNode }} props
 */
function ProtectedRoute({ children }) {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

/**
 * PageLoader — Spinner de carga para lazy loading.
 */
function PageLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg-body)' }}>
      <div className="flex flex-col items-center gap-3">
        <svg className="animate-spin h-8 w-8 text-royalBlue-500" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Cargando...</p>
      </div>
    </div>
  );
}

/**
 * App — Componente raíz de la aplicación.
 * Incluye el router, toasts globales y barra de accesibilidad.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/busqueda" element={<Search />} />
          <Route path="/especialista/:id" element={<Detail />} />
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
      <ToastContainer />
      <AccessibilityBar />
    </BrowserRouter>
  );
}
