import React, { useState } from 'react';
import { RiEyeLine, RiEyeOffLine } from 'react-icons/ri';

/**
 * Input — Componente de input con label, error y variante password.
 * @param {{ label?: string, error?: string, type?: string, id: string, className?: string }} props
 * @example
 * <Input id="email" label="Correo electrónico" type="email" error={errors.email} />
 * <Input id="password" label="Contraseña" type="password" />
 */
export function Input({
  label,
  error,
  type = 'text',
  id,
  className = '',
  ...rest
}) {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === 'password';
  const inputType = isPassword && showPassword ? 'text' : type;

  return (
    <div className={`space-y-1.5 ${className}`}>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
          {label}
        </label>
      )}
      <div className="relative">
        <input
          id={id}
          type={inputType}
          className={`glass-input w-full px-4 py-2.5 text-sm ${error ? 'border-red-500 focus:border-red-500' : ''}`}
          {...rest}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-lg hover:text-royalBlue-400 transition-colors"
            style={{ color: 'var(--text-muted)' }}
            tabIndex={-1}
            aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
          >
            {showPassword ? <RiEyeOffLine /> : <RiEyeLine />}
          </button>
        )}
      </div>
      {error && (
        <p className="text-xs text-red-400 mt-1">{error}</p>
      )}
    </div>
  );
}
