import React, { createContext, useState, useEffect, useCallback, useRef } from 'react';
import {
  iniciarSesion as apiIniciarSesion,
  registrarUsuario as apiRegistrarUsuario,
  obtenerPerfilUsuario as apiObtenerPerfilUsuario,
  actualizarPerfilUsuario as apiActualizarPerfilUsuario,
  listarFavoritos as apiListarFavoritos
} from '@/services/api';
import { SessionExpiredModal } from '@/components/ui/SessionExpiredModal';

export const AuthContext = createContext(null);

/** Tiempo en ms antes del vencimiento para refrescar proactivamente (5 min) */
const REFRESH_ANTES_DE_VENCER_MS = 5 * 60 * 1000;

/**
 * Decodifica el payload del JWT sin verificar la firma (solo para leer exp en el cliente).
 * @param {string} token
 * @returns {{ exp?: number } | null}
 */
function _decodeJwtPayload(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + c.charCodeAt(0).toString(16).padStart(2, '0'))
        .join('')
    );
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('medrec_token') || null);
  const [loading, setLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);
  const refreshTimerRef = useRef(null);

  /**
   * Programa el refresco proactivo del JWT antes de que expire.
   */
  const _programarRefresh = useCallback((rawToken) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    if (!rawToken) return;

    const payload = _decodeJwtPayload(rawToken);
    if (!payload?.exp) return;

    const expiresMs = payload.exp * 1000;
    const ahora = Date.now();
    const tiempoHastaRefresh = expiresMs - ahora - REFRESH_ANTES_DE_VENCER_MS;

    if (tiempoHastaRefresh <= 0) {
      // Ya está muy cerca de expirar o ya expiró — no programar timer
      return;
    }

    refreshTimerRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/auth/refresh`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${rawToken}`,
          },
        });
        if (res.ok) {
          const data = await res.json();
          if (data?.access_token) {
            localStorage.setItem('medrec_token', data.access_token);
            setToken(data.access_token);
            _programarRefresh(data.access_token);
          }
        }
      } catch {
        // Si falla el refresh proactivo se ignora — el interceptor en api.js lo manejará
      }
    }, tiempoHastaRefresh);
  }, []);

  // Recarga el usuario desde el backend usando el token actual
  const recargarUsuario = useCallback(async () => {
    const curToken = localStorage.getItem('medrec_token');
    if (!curToken) {
      setUser(null);
      setToken(null);
      setLoading(false);
      return null;
    }

    try {
      setLoading(true);
      const perfil = await apiObtenerPerfilUsuario();
      setUser(perfil);
      setToken(curToken);
      localStorage.setItem('medrec_user', JSON.stringify(perfil));
      _programarRefresh(curToken);

      // Sincronizar favoritos
      try {
        await apiListarFavoritos();
      } catch (e) {
        console.error("Error sincronizando favoritos al recargar usuario:", e);
      }

      return perfil;
    } catch (error) {
      console.error("Error al recargar perfil de usuario:", error);
      cerrarSesion();
      return null;
    } finally {
      setLoading(false);
    }
  }, [_programarRefresh]);

  // Cargar usuario inicial al montar
  useEffect(() => {
    recargarUsuario();
  }, [recargarUsuario]);

  // Escuchar el evento global de sesión expirada emitido por api.js
  useEffect(() => {
    const handler = () => {
      setUser(null);
      setToken(null);
      setSessionExpired(true);
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
    window.addEventListener('medrec:session-expired', handler);
    return () => window.removeEventListener('medrec:session-expired', handler);
  }, []);

  const cerrarSesion = useCallback(() => {
    setUser(null);
    setToken(null);
    setSessionExpired(false);
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    localStorage.removeItem('medrec_token');
    localStorage.removeItem('medrec_user');
    localStorage.removeItem('medrec_favorites');
  }, []);

  const iniciarSesion = useCallback(async (email, password) => {
    try {
      const result = await apiIniciarSesion(email, password);
      setUser(result.user);
      setToken(result.token);
      setSessionExpired(false);
      _programarRefresh(result.token);
      return { success: true, message: '¡Bienvenido de nuevo!' };
    } catch (error) {
      return { success: false, message: error.message || 'Usuario o contraseña incorrectos.' };
    }
  }, [_programarRefresh]);

  const registrarUsuario = useCallback(async (email, password, extraFields = {}) => {
    try {
      await apiRegistrarUsuario(email, password, extraFields);
      return { success: true, message: 'Usuario registrado con éxito. Ahora puedes iniciar sesión.' };
    } catch (error) {
      console.error("Error de registro:", error);
      return { success: false, message: error.message || 'Error al registrar el usuario.' };
    }
  }, []);

  const actualizarUsuarioLocal = useCallback((updates) => {
    setUser((prev) => {
      if (!prev) return null;
      const updated = { ...prev, ...updates };
      localStorage.setItem('medrec_user', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const updateProfile = useCallback(async (updates) => {
    try {
      const updatedUser = await apiActualizarPerfilUsuario(updates);
      setUser(updatedUser);
      return { success: true, message: 'Perfil actualizado con éxito.' };
    } catch (error) {
      console.error("Error al actualizar perfil:", error);
      return { success: false, message: error.message || 'Error al actualizar perfil.' };
    }
  }, []);

  // Compatibilidad con aliases en inglés
  const login = iniciarSesion;
  const logout = cerrarSesion;

  const loginWithGoogle = useCallback(async () => {
    return { success: false, message: 'El inicio de sesión con Google no está configurado.' };
  }, []);

  const isAuthenticated = Boolean(user && token);

  /**
   * Maneja el click en "Iniciar sesión" del modal de sesión expirada.
   * Guarda la ruta actual y redirige al login para volver después.
   */
  const handleSessionExpiredLogin = useCallback(() => {
    setSessionExpired(false);
    const returnTo = window.location.pathname + window.location.search;
    const loginUrl = returnTo && returnTo !== '/login'
      ? `/login?redirect=${encodeURIComponent(returnTo)}`
      : '/login';
    window.location.href = loginUrl;
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated,
        iniciarSesion,
        registrarUsuario,
        cerrarSesion,
        recargarUsuario,
        actualizarUsuarioLocal,
        login,
        loginWithGoogle,
        logout,
        updateProfile,
      }}
    >
      {children}

      {/* Modal de sesión expirada — aparece como overlay encima de todo */}
      {sessionExpired && (
        <SessionExpiredModal onLogin={handleSessionExpiredLogin} />
      )}
    </AuthContext.Provider>
  );
}

