import React, { createContext, useState, useEffect, useCallback } from 'react';
import {
  iniciarSesion as apiIniciarSesion,
  registrarUsuario as apiRegistrarUsuario,
  obtenerPerfilUsuario as apiObtenerPerfilUsuario,
  actualizarPerfilUsuario as apiActualizarPerfilUsuario,
  listarFavoritos as apiListarFavoritos
} from '@/services/api';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('medrec_token') || null);
  const [loading, setLoading] = useState(true);

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
      
      // Sincronizar favoritos
      try {
        await apiListarFavoritos();
      } catch (e) {
        console.error("Error sincronizando favoritos al recargar usuario:", e);
      }
      
      return perfil;
    } catch (error) {
      console.error("Error al recargar perfil de usuario:", error);
      // Si falla por token inválido/expirado, limpiar sesión
      cerrarSesion();
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Cargar usuario inicial al montar
  useEffect(() => {
    recargarUsuario();
  }, [recargarUsuario]);

  /**
   * Inicia sesión con la API del backend.
   */
  const iniciarSesion = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const result = await apiIniciarSesion(email, password);
      setUser(result.user);
      setToken(result.token);
      return { success: true, message: '¡Bienvenido de nuevo!' };
    } catch (error) {
      console.error("Error de inicio de sesión:", error);
      return { success: false, message: error.message || 'Credenciales incorrectas.' };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Registra un nuevo usuario en la API del backend.
   */
  const registrarUsuario = useCallback(async (email, password) => {
    setLoading(true);
    try {
      await apiRegistrarUsuario(email, password);
      return { success: true, message: 'Usuario registrado con éxito. Ahora puedes iniciar sesión.' };
    } catch (error) {
      console.error("Error de registro:", error);
      return { success: false, message: error.message || 'Error al registrar el usuario.' };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Cierra la sesión y limpia el almacenamiento local.
   */
  const cerrarSesion = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('medrec_token');
    localStorage.removeItem('medrec_user');
    localStorage.removeItem('medrec_favorites');
  }, []);

  /**
   * Actualiza el usuario localmente sin consultar el backend.
   */
  const actualizarUsuarioLocal = useCallback((updates) => {
    setUser((prev) => {
      if (!prev) return null;
      const updated = { ...prev, ...updates };
      localStorage.setItem('medrec_user', JSON.stringify(updated));
      return updated;
    });
  }, []);

  /**
   * Actualiza el perfil en el backend y refresca el estado local.
   */
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

  // Compatibilidad con aliases en inglés para no romper componentes existentes
  const login = iniciarSesion;
  const logout = cerrarSesion;

  const loginWithGoogle = useCallback(async () => {
    // Simulado para compatibilidad
    return { success: false, message: 'El inicio de sesión con Google no está configurado.' };
  }, []);

  const isAuthenticated = Boolean(user && token);

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
        // Compatibilidad:
        login,
        loginWithGoogle,
        logout,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
