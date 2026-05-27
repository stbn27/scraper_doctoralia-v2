import { useContext } from 'react';
import { AuthContext } from '@/context/AuthContext';

/**
 * Hook para acceder al contexto de autenticación.
 * @returns {{ user: Object|null, login: Function, loginWithGoogle: Function, logout: Function, updateProfile: Function }}
 * @example
 * const { user, login, logout } = useAuth();
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe usarse dentro de un AuthProvider');
  }
  return context;
}
