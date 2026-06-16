import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  RiArrowDownSLine,
  RiHeartLine,
  RiHistoryLine,
  RiLogoutBoxRLine,
  RiUserLine,
  RiDashboardLine,
} from 'react-icons/ri';

import { AccessibilityDropdown } from '@/components/layout/AccessibilityDropdown.jsx';

function getUserFirstName(user) {
  return user?.nombre || user?.name || 'Usuario';
}

function getUserInitials(user) {
  const firstName = user?.nombre || user?.name || '';
  const lastName = user?.apellido || user?.lastName || '';

  const firstInitial = firstName.charAt(0);
  const lastInitial = lastName.charAt(0);

  const initials = `${firstInitial}${lastInitial}`.toUpperCase();

  return initials || 'U';
}

export function UserDropdown({ user, onLogout }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [imgError, setImgError] = useState(false);
  const menuRef = useRef(null);

  const firstName = getUserFirstName(user);
  const initials = getUserInitials(user);
  const avatarUrl = user?.avatar_url || user?.avatar;

  useEffect(() => {
    setImgError(false);
  }, [avatarUrl]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const closeMenu = () => {
    setMenuOpen(false);
  };

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setMenuOpen((currentValue) => !currentValue)}
        className="flex items-center gap-2 rounded-xl px-2 py-1.5 transition-colors hover:bg-black/10 dark:hover:bg-white/10"
        aria-label="Abrir menú de usuario"
        aria-expanded={menuOpen}
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-royalBlue-600 text-sm font-semibold text-white overflow-hidden">
          {avatarUrl && avatarUrl.startsWith('http') && !imgError ? (
            <img
              src={avatarUrl}
              alt={firstName}
              className="h-full w-full object-cover"
              onError={() => setImgError(true)}
            />
          ) : (
            initials
          )}
        </div>

        <span className="hidden text-sm font-medium sm:block">
          {firstName}
        </span>

        <RiArrowDownSLine
          className={`text-lg transition-transform duration-300 ${menuOpen ? 'rotate-180' : ''
            }`}
        />
      </button>

      {menuOpen && (
        <div className="absolute right-0 mt-2 w-64 rounded-2xl border border-white/20 bg-white/80 p-2 shadow-2xl backdrop-blur-xl dark:bg-slate-950/95">

          <div className="px-3 py-2">
            <p className="text-sm font-semibold">
              {firstName}
            </p>
            <p
              className="truncate text-xs"
              style={{ color: 'var(--text-muted)' }}
            >
              {user?.email}
            </p>
          </div>

          <div className="my-1 h-px bg-black/10 dark:bg-white/10" />

          <Link
            to="/perfil"
            onClick={closeMenu}
            className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors hover:bg-black/10 dark:hover:bg-white/10"
          >
            <RiUserLine />
            Mi perfil
          </Link>

          {user?.rol === 'ADMIN' && (
            <Link
              to="/admin"
              onClick={closeMenu}
              className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors text-royalBlue-600 dark:text-royalBlue-400 hover:bg-royalBlue-50 dark:hover:bg-royalBlue-900/20"
            >
              <RiDashboardLine />
              Administrador
            </Link>
          )}

          <Link
            to="/favoritos"
            onClick={closeMenu}
            className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors hover:bg-black/10 dark:hover:bg-white/10"
          >
            <RiHeartLine />
            Mis favoritos
          </Link>

          <Link
            to="/historial"
            onClick={closeMenu}
            className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors hover:bg-black/10 dark:hover:bg-white/10"
          >
            <RiHistoryLine />
            Historial de búsqueda
          </Link>

          <div className="my-1 h-px bg-black/10 dark:bg-white/10" />

          <AccessibilityDropdown />

          <div className="my-1 h-px bg-black/10 dark:bg-white/10" />

          <button
            type="button"
            onClick={() => {
              closeMenu();
              onLogout();
            }}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-medium text-red-500 transition-colors hover:bg-red-500/10"
          >
            <RiLogoutBoxRLine />
            Cerrar sesión
          </button>
        </div>
      )}
    </div>
  );
}