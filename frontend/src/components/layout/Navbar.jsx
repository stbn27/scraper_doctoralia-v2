import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  RiUserLine,
  RiLoginBoxLine,
  RiDashboardLine,
  RiLogoutBoxRLine,
  RiArrowLeftLine,
} from 'react-icons/ri';
import { ThemeToggle } from '@/components/shared/ThemeToggle';
import { useAuth } from '@/hooks/useAuth';
import logo from '@/assets/logo.png';

/**
 * Navbar — Barra de navegación principal.
 * Transparente en Home, visible en el resto de pantallas.
 * @example
 * <Navbar />
 */
export function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const isHome = location.pathname === '/';

  // Cerrar menú al hacer clic fuera
  useEffect(() => {
    const handleClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  /**
   * Obtiene el título de la sección actual.
   * @returns {string}
   */
  const getSectionTitle = () => {
    const path = location.pathname;
    if (path === '/resultados') return 'Resultados';
    if (path.startsWith('/especialista')) return 'Detalle del especialista';
    if (path === '/login') return 'Iniciar sesión';
    if (path === '/dashboard') return 'Panel de usuario';
    return '';
  };

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-30 transition-all duration-300 ${isHome
        ? 'bg-transparent'
        : 'glass-card rounded-none border-x-0 border-t-0'
        }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Izquierda: Logo o botón back */}
          <div className="flex items-center gap-3">
            {!isHome && location.pathname !== '/resultados' && location.pathname !== '/dashboard' && (
              <button
                onClick={() => navigate(-1)}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                style={{ color: 'var(--text-muted)' }}
                aria-label="Volver"
              >
                <RiArrowLeftLine className="text-xl" />
              </button>
            )}
            <Link to="/" className="flex items-center gap-2 group">
              <img src={logo} alt="MedRec" className="w-8 h-8 rounded-lg" />
              <span className="text-lg font-semibold group-hover:text-royalBlue-400 transition-colors">
                MedRec
              </span>
            </Link>
          </div>

          {/* Centro: Título de sección */}
          <span className="hidden md:block text-sm font-medium font-secondary" style={{ color: 'var(--text-muted)' }}>
            {getSectionTitle()}
          </span>

          {/* Derecha: Theme toggle + auth */}
          <div className="flex items-center gap-2">
            <ThemeToggle />

            {user ? (
              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setMenuOpen(!menuOpen)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-royalBlue-600 flex items-center justify-center text-white text-sm font-medium">
                    {user.name?.charAt(0) || 'U'}
                  </div>
                  <span className="hidden sm:block text-sm">{user.name}</span>
                </button>

                {menuOpen && (
                  <div className="absolute right-0 mt-2 w-48 glass-card p-2 shadow-2xl">
                    <Link
                      to="/dashboard"
                      className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
                      onClick={() => setMenuOpen(false)}
                    >
                      <RiDashboardLine /> Panel de usuario
                    </Link>
                    <button
                      onClick={() => {
                        logout();
                        setMenuOpen(false);
                        navigate('/');
                      }}
                      className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-black/10 dark:hover:bg-white/10 transition-colors w-full text-left text-red-400"
                    >
                      <RiLogoutBoxRLine /> Cerrar sesión
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Link
                to="/login"
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-royalBlue-600 hover:bg-royalBlue-700 text-white text-sm font-medium transition-colors press-effect"
              >
                <RiLoginBoxLine />
                <span className="hidden sm:inline">Iniciar sesión</span>
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
