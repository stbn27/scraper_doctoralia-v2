import React, {useContext} from 'react';
import {RiSunLine, RiMoonLine} from 'react-icons/ri';
import {ThemeContext} from '@/context/ThemeContext';

/**
 * ThemeToggle — Botón de toggle entre dark/light mode.
 * Usa View Transitions API con clip-path circular.
 * @param {{ className?: string }} props
 * @example
 * <ThemeToggle />
 */
export function ThemeToggle({className = ''}) {
    const {theme, toggleTheme} = useContext(ThemeContext);

    return (
        <button
            onClick={(event) => toggleTheme(event)}
            className={`p-2 rounded-lg hover:bg-white/10 transition-colors text-lg ${className}`}
            style={{color: 'var(--text-muted)'}}
            aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
            title={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
        >
            {theme === 'dark' ? <RiSunLine/> : <RiMoonLine/>}
        </button>
    );
}
