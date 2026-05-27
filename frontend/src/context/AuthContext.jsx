import React, { createContext, useState, useCallback } from 'react';

/**
 * AuthContext — Maneja la autenticación mockeada de la aplicación.
 * Credenciales válidas: test@medrec.mx / 1234
 * @typedef {{ name: string, email: string, avatar: string }} User
 */
export const AuthContext = createContext(null);

/** Usuario mock predeterminado al autenticarse */
const MOCK_USER = {
  name: 'Usuario MedRec',
  email: 'test@medrec.mx',
  avatar: '👤',
};

/**
 * AuthProvider — Envuelve la app con el contexto de autenticación.
 * @param {{ children: React.ReactNode }} props
 * @example
 * <AuthProvider>
 *   <App />
 * </AuthProvider>
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('medrec_user');
    return saved ? JSON.parse(saved) : null;
  });

  /**
   * Intenta autenticar con credenciales mock.
   * @param {string} email — Correo del usuario.
   * @param {string} password — Contraseña del usuario.
   * @returns {{ success: boolean, message: string }}
   */
  const login = useCallback((email, password) => {
    if (email === 'test@medrec.mx' && password === '1234') {
      const userData = { ...MOCK_USER, email };
      setUser(userData);
      localStorage.setItem('medrec_user', JSON.stringify(userData));
      return { success: true, message: '¡Bienvenido de nuevo!' };
    }
    return { success: false, message: 'Credenciales incorrectas.' };
  }, []);

  /**
   * Autenticación mock con Google (simula 1s de espera).
   * @returns {Promise<{ success: boolean, message: string }>}
   */
  const loginWithGoogle = useCallback(() => {
    return new Promise((resolve) => {
      setTimeout(() => {
        const userData = { ...MOCK_USER, name: 'Usuario Google', email: 'google@medrec.mx' };
        setUser(userData);
        localStorage.setItem('medrec_user', JSON.stringify(userData));
        resolve({ success: true, message: '¡Bienvenido de nuevo!' });
      }, 1000);
    });
  }, []);

  /**
   * Cierra la sesión del usuario y limpia localStorage.
   */
  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('medrec_user');
  }, []);

  /**
   * Actualiza los datos del perfil del usuario.
   * @param {{ name?: string, avatar?: string }} updates
   */
  const updateProfile = useCallback((updates) => {
    setUser((prev) => {
      const updated = { ...prev, ...updates };
      localStorage.setItem('medrec_user', JSON.stringify(updated));
      return updated;
    });
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, loginWithGoogle, logout, updateProfile }}>
      {children}
    </AuthContext.Provider>
  );
}
