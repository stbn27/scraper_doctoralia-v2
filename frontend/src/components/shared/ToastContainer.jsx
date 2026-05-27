import React from 'react';
import {
  RiCheckboxCircleLine,
  RiErrorWarningLine,
  RiInformationLine,
  RiAlertLine,
  RiCloseLine,
} from 'react-icons/ri';
import { useToast } from '@/hooks/useToast';

/**
 * Iconos y colores por tipo de toast.
 */
const TOAST_CONFIG = {
  success: { icon: RiCheckboxCircleLine, color: '#10b981', bgAccent: 'rgba(16, 185, 129, 0.15)' },
  error:   { icon: RiErrorWarningLine,   color: '#ef4444', bgAccent: 'rgba(239, 68, 68, 0.15)' },
  info:    { icon: RiInformationLine,    color: '#3b82f6', bgAccent: 'rgba(59, 130, 246, 0.15)' },
  warning: { icon: RiAlertLine,          color: '#f59e0b', bgAccent: 'rgba(245, 158, 11, 0.15)' },
};

/**
 * Toast individual.
 * @param {{ toast: { id: number, type: string, message: string, exiting: boolean } }} props
 */
function Toast({ toast }) {
  const { removeToast } = useToast();
  const config = TOAST_CONFIG[toast.type] || TOAST_CONFIG.info;
  const Icon = config.icon;

  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-xl shadow-2xl max-w-sm w-full relative overflow-hidden ${toast.exiting ? 'toast-exit' : 'toast-enter'}`}
      style={{
        background: 'rgba(30, 58, 138, 0.75)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        border: '1px solid rgba(96, 165, 250, 0.3)',
      }}
    >
      {/* Icono */}
      <Icon className="text-xl mt-0.5 shrink-0" style={{ color: config.color }} />

      {/* Mensaje */}
      <p className="text-sm text-white/90 flex-1 leading-relaxed">{toast.message}</p>

      {/* Botón cerrar */}
      <button
        onClick={() => removeToast(toast.id)}
        className="text-white/50 hover:text-white/90 transition-colors shrink-0"
        aria-label="Cerrar notificación"
      >
        <RiCloseLine className="text-lg" />
      </button>

      {/* Barra de progreso */}
      {!toast.exiting && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5">
          <div
            className="h-full toast-progress-bar rounded-full"
            style={{ background: config.color }}
          />
        </div>
      )}
    </div>
  );
}

/**
 * ToastContainer — Contenedor global de toasts.
 * Posición fija inferior derecha, máximo 3 toasts visibles.
 * @example
 * // En App.jsx:
 * <ToastContainer />
 */
export function ToastContainer() {
  const { toasts } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3" id="toast-container">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} />
      ))}
    </div>
  );
}
