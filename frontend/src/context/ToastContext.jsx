import React, { createContext, useState, useCallback, useRef } from 'react';

/**
 * ToastContext — Sistema de notificaciones toast con glassmorphism.
 * Máximo 3 toasts simultáneos, auto-dismiss a 3.5s.
 * @typedef {'success'|'error'|'info'|'warning'} ToastType
 * @typedef {{ id: number, type: ToastType, message: string, exiting: boolean }} Toast
 */
export const ToastContext = createContext(null);

let toastIdCounter = 0;

/**
 * ToastProvider — Envuelve la app con el contexto de toasts.
 * @param {{ children: React.ReactNode }} props
 * @example
 * const { addToast } = useToast();
 * addToast({ type: 'success', message: 'Guardado correctamente' });
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timersRef = useRef({});

  /**
   * Elimina un toast con animación de salida.
   * @param {number} id — ID del toast a eliminar.
   */
  const removeToast = useCallback((id) => {
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, exiting: true } : t))
    );
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
      if (timersRef.current[id]) {
        clearTimeout(timersRef.current[id]);
        delete timersRef.current[id];
      }
    }, 250);
  }, []);

  /**
   * Agrega un nuevo toast a la cola.
   * Si hay más de 3, el más antiguo sale automáticamente.
   * @param {{ type: ToastType, message: string }} toast
   */
  const addToast = useCallback(({ type = 'info', message }) => {
    const id = ++toastIdCounter;
    const newToast = { id, type, message, exiting: false };

    setToasts((prev) => {
      const updated = [...prev, newToast];
      if (updated.length > 3) {
        const oldest = updated[0];
        removeToast(oldest.id);
        return updated.slice(1);
      }
      return updated;
    });

    timersRef.current[id] = setTimeout(() => {
      removeToast(id);
    }, 3500);

    return id;
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
    </ToastContext.Provider>
  );
}
