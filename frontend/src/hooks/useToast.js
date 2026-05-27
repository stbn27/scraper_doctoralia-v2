import { useContext } from 'react';
import { ToastContext } from '@/context/ToastContext';

/**
 * Hook para acceder al sistema de toasts.
 * @returns {{ toasts: Array, addToast: Function, removeToast: Function }}
 * @example
 * const { addToast } = useToast();
 * addToast({ type: 'success', message: 'Guardado correctamente' });
 */
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast debe usarse dentro de un ToastProvider');
  }
  return context;
}
