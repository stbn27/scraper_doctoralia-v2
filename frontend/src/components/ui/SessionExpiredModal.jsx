import React from 'react';
import { RiLockLine } from 'react-icons/ri';

/**
 * Modal de sesión expirada.
 * Aparece como overlay encima de todo cuando el JWT expira y no puede refrescarse.
 *
 * Props
 * -----
 * onLogin : () => void  — Callback para ir al login (el padre gestiona la navegación)
 */
export function SessionExpiredModal({ onLogin }) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="session-expired-title"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)',
        padding: 16,
      }}
    >
      <div
        style={{
          background: 'var(--glass-bg, #18181b)',
          border: '1px solid var(--glass-border, rgba(255,255,255,0.1))',
          borderRadius: 20,
          padding: '36px 32px',
          maxWidth: 360,
          width: '100%',
          textAlign: 'center',
          boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
          animation: 'sessionExpiredIn 0.25s ease',
        }}
      >
        {/* Icono */}
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: '50%',
            background: 'rgba(239,68,68,0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
          }}
        >
          <RiLockLine size={28} style={{ color: '#ef4444' }} />
        </div>

        {/* Título */}
        <h2
          id="session-expired-title"
          style={{
            fontSize: 18,
            fontWeight: 700,
            color: 'var(--text-primary, #fff)',
            margin: '0 0 10px',
          }}
        >
          Sesión expirada
        </h2>

        {/* Descripción */}
        <p
          style={{
            fontSize: 13,
            color: 'var(--text-muted, rgba(255,255,255,0.6))',
            margin: '0 0 28px',
            lineHeight: 1.6,
          }}
        >
          Tu sesión ha caducado por inactividad. Inicia sesión de nuevo para continuar donde lo dejaste.
        </p>

        {/* Botón */}
        <button
          id="btn-reiniciar-sesion"
          onClick={onLogin}
          style={{
            width: '100%',
            padding: '12px 0',
            borderRadius: 12,
            background: 'var(--color-primary-500, #4f7dff)',
            color: '#fff',
            fontWeight: 600,
            fontSize: 14,
            border: 'none',
            cursor: 'pointer',
            transition: 'opacity 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.opacity = '0.85'; }}
          onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
        >
          Iniciar sesión
        </button>
      </div>

      <style>{`
        @keyframes sessionExpiredIn {
          from { opacity: 0; transform: scale(0.94) translateY(8px); }
          to   { opacity: 1; transform: scale(1) translateY(0); }
        }
      `}</style>
    </div>
  );
}
