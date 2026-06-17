import React from 'react';
import { createPortal } from 'react-dom';
import { RiDeleteBinLine } from 'react-icons/ri';
import { Button } from './Button';

/**
 * ConfirmModal — Modal de confirmación moderno y reutilizable.
 * @param {{
 *   isOpen: boolean;
 *   onClose: () => void;
 *   onConfirm: () => void | Promise<void>;
 *   title: string;
 *   message: string;
 *   confirmText?: string;
 *   cancelText?: string;
 *   variant?: 'danger' | 'primary';
 *   icon?: React.ReactNode;
 * }} props
 */
export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Eliminar',
  cancelText = 'Cancelar',
  variant = 'danger',
  icon = null
}) {
  if (!isOpen) return null;
  if (typeof document === 'undefined') return null;

  const defaultIcon = variant === 'danger' 
    ? <RiDeleteBinLine className="text-xl" />
    : null;

  const iconColorClass = variant === 'danger'
    ? 'bg-red-500/10 border-red-500/20 text-red-500'
    : 'bg-royalBlue-500/10 border-royalBlue-500/20 text-royalBlue-400';

  const modalContent = (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Background overlay */}
      <div 
        className="absolute inset-0 bg-slate-950/70 backdrop-blur-md transition-opacity duration-300"
        onClick={onClose}
      />
      
      {/* Modal content */}
      <div className="relative w-full max-w-sm transform overflow-hidden rounded-3xl border border-white/10 bg-[#0d0d0f]/90 p-6 shadow-2xl backdrop-blur-xl transition-all duration-300 animate-in fade-in zoom-in-95">
        <div className="flex flex-col items-center text-center space-y-4">
          {/* Icon */}
          <div className={`flex h-12 w-12 items-center justify-center rounded-2xl border ${iconColorClass}`}>
            {icon || defaultIcon}
          </div>
          
          {/* Title & Description */}
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-100">
              {title}
            </h3>
            <p className="text-xs text-slate-400">
              {message}
            </p>
          </div>
          
          {/* Actions */}
          <div className="flex w-full items-center justify-center gap-2 pt-2">
            <Button
              variant="ghost"
              onClick={onClose}
              className="flex-1 text-xs py-2"
            >
              {cancelText}
            </Button>
            <Button
              variant={variant}
              onClick={onConfirm}
              className="flex-grow flex-1 text-xs py-2"
            >
              {confirmText}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
