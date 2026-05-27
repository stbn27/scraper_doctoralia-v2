import React, { createContext, useState, useEffect, useCallback } from 'react';

/**
 * ThemeContext — Controla el modo oscuro/claro de la aplicación.
 * Usa View Transitions API con clip-path circular para transiciones suaves.
 * @typedef {'dark'|'light'} ThemeMode
 */
export const ThemeContext = createContext(null);

/**
 * ThemeProvider — Envuelve la app con el contexto de tema.
 * @param {{ children: React.ReactNode }} props
 * @example
 * <ThemeProvider>
 *   <App />
 * </ThemeProvider>
 */
export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('medrec_theme');
    return saved || 'dark';
  });

  const [bgPreset, setBgPreset] = useState(() => {
    const saved = localStorage.getItem('medrec_bg_preset');
    return saved ? parseInt(saved, 10) : 1;
  });

  useEffect(() => {
    const html = document.documentElement;
    html.classList.remove('dark', 'light');
    html.classList.add(theme);
    localStorage.setItem('medrec_theme', theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem('medrec_bg_preset', String(bgPreset));
  }, [bgPreset]);

  /**
   * Alterna entre dark y light mode usando View Transitions API
   * con un clip-path circular que se expande desde la parte superior.
   */
  const toggleTheme = useCallback(() => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';

    if (document.startViewTransition) {
      document.documentElement.style.viewTransitionName = 'theme-transition';
      const transition = document.startViewTransition(() => {
        setTheme(newTheme);
      });
      transition.finished.then(() => {
        document.documentElement.style.viewTransitionName = '';
      });
    } else {
      setTheme(newTheme);
    }
  }, [theme]);

  /**
   * Cicla entre los 3 presets de fondo.
   */
  const cycleBgPreset = useCallback(() => {
    setBgPreset((prev) => (prev % 3) + 1);
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, bgPreset, cycleBgPreset }}>
      {children}
    </ThemeContext.Provider>
  );
}
