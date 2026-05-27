import React, { useState, useEffect, useContext } from 'react';
import {
  RiAddLine,
  RiSubtractLine,
  RiSunLine,
  RiMoonLine,
  RiPaletteLine,
} from 'react-icons/ri';
import { ThemeContext } from '@/context/ThemeContext';

/**
 * AccessibilityBar — Barra flotante de accesibilidad.
 * Controles: A+ / A- (font-size), tema toggle, preset de fondo.
 * Persiste en localStorage bajo 'a11y_prefs'.
 * @example
 * <AccessibilityBar />
 */
export function AccessibilityBar() {
  const { theme, toggleTheme, cycleBgPreset } = useContext(ThemeContext);
  const [fontSize, setFontSize] = useState(() => {
    const saved = localStorage.getItem('a11y_prefs');
    if (saved) {
      const prefs = JSON.parse(saved);
      return prefs.fontSize || 16;
    }
    return 16;
  });

  useEffect(() => {
    document.documentElement.style.setProperty('--font-size-base', `${fontSize}px`);
    document.documentElement.style.fontSize = `${fontSize}px`;
    const prefs = JSON.parse(localStorage.getItem('a11y_prefs') || '{}');
    prefs.fontSize = fontSize;
    localStorage.setItem('a11y_prefs', JSON.stringify(prefs));
  }, [fontSize]);

  /**
   * Incrementa el font-size en 2px (máx. 22px).
   */
  const increaseFontSize = () => {
    setFontSize((prev) => Math.min(prev + 2, 22));
  };

  /**
   * Decrementa el font-size en 2px (mín. 14px).
   */
  const decreaseFontSize = () => {
    setFontSize((prev) => Math.max(prev - 2, 14));
  };

  const buttons = [
    {
      label: 'Aumentar tamaño de texto',
      icon: <><span className="text-xs font-bold">A</span><RiAddLine className="text-[10px]" /></>,
      onClick: increaseFontSize,
    },
    {
      label: 'Disminuir tamaño de texto',
      icon: <><span className="text-xs font-bold">A</span><RiSubtractLine className="text-[10px]" /></>,
      onClick: decreaseFontSize,
    },
    {
      label: theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro',
      icon: theme === 'dark' ? <RiSunLine className="text-sm" /> : <RiMoonLine className="text-sm" />,
      onClick: toggleTheme,
    },
    {
      label: 'Cambiar fondo',
      icon: <RiPaletteLine className="text-sm" />,
      onClick: cycleBgPreset,
    },
  ];

  return (
    <div
      className="fixed left-4 top-1/2 -translate-y-1/2 z-40 glass-card p-1.5 flex flex-col gap-1"
      style={{ width: '40px' }}
      role="toolbar"
      aria-label="Barra de accesibilidad"
    >
      {buttons.map((btn, i) => (
        <div key={i} className="tooltip-container">
          <button
            onClick={btn.onClick}
            className="w-[28px] h-[28px] flex items-center justify-center rounded-lg hover:bg-white/15 transition-colors press-effect"
            style={{ color: 'var(--text-muted)' }}
            aria-label={btn.label}
          >
            <span className="flex items-center gap-0">{btn.icon}</span>
          </button>
          <span className="tooltip-text">{btn.label}</span>
        </div>
      ))}
    </div>
  );
}
