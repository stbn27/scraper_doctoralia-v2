import React, {createContext, useState, useEffect, useCallback} from 'react';

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
export function ThemeProvider({children}) {
    const [theme, setTheme] = useState(() => {
        const saved = localStorage.getItem('medrec_theme');
        return saved || 'dark';
    });

    const [bgPreset, setBgPreset] = useState(() => {
        const saved = localStorage.getItem('medrec_bg_preset');
        return saved ? parseInt(saved, 10) : 1;
    });

    const applyTheme = useCallback((nextTheme) => {
        const html = document.documentElement;
        html.classList.remove('dark', 'light');
        html.classList.add(nextTheme);
        localStorage.setItem('medrec_theme', nextTheme);
    }, []);

    useEffect(() => {
        applyTheme(theme);
    }, [applyTheme, theme]);

    useEffect(() => {
        localStorage.setItem('medrec_bg_preset', String(bgPreset));
    }, [bgPreset]);

    const DEBUG_THEME_TRANSITION = false;
    const DEBUG_DURATION_MS = 400;

    /**
     * Alterna entre dark y light mode usando View Transitions API
     * con un clip-path circular que se expande desde la parte superior.
     */
    const toggleTheme = useCallback((event) => {
        const newTheme = theme === 'dark' ? 'light' : 'dark';

        if (DEBUG_THEME_TRANSITION) {
            console.debug('[theme] toggle start', {from: theme, to: newTheme});
        }

        if (!document.startViewTransition) {
            if (DEBUG_THEME_TRANSITION) {
                console.debug('[theme] ViewTransition not supported, fallback');
            }
            applyTheme(newTheme);
            setTheme(newTheme);
            return;
        }

        const x = event?.clientX ?? window.innerWidth / 2;
        const y = event?.clientY ?? window.innerHeight / 2;

        const endRadius = Math.hypot(
            Math.max(x, window.innerWidth - x),
            Math.max(y, window.innerHeight - y)
        );

        if (DEBUG_THEME_TRANSITION) {
            console.debug('[theme] ViewTransition start', {x, y, endRadius});
        }

        const transition = document.startViewTransition(() => {
            applyTheme(newTheme);
            setTheme(newTheme);
        });

        transition.ready.then(() => {
            if (DEBUG_THEME_TRANSITION) {
                console.debug('[theme] ViewTransition ready, animating');
            }
            document.documentElement.animate(
                {
                    clipPath: [
                        `circle(0px at ${x}px ${y}px)`,
                        `circle(${endRadius}px at ${x}px ${y}px)`,
                    ],
                },
                {
                    duration: DEBUG_DURATION_MS,
                    easing: 'ease-in-out',
                    fill: 'both',
                    pseudoElement: '::view-transition-new(root)',
                }
            );
        });

        transition.finished.then(() => {
            if (DEBUG_THEME_TRANSITION) {
                console.debug('[theme] ViewTransition finished');
            }
        });
    }, [applyTheme, theme]);

    /**
     * Cicla entre los 3 presets de fondo.
     */
    const cycleBgPreset = useCallback(() => {
        setBgPreset((prev) => (prev % 3) + 1);
    }, []);

    return (
        <ThemeContext.Provider value={{theme, toggleTheme, bgPreset, cycleBgPreset}}>
            {children}
        </ThemeContext.Provider>
    );
}
