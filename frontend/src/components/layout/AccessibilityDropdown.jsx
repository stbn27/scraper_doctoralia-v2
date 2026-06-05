import React, { useContext, useState } from 'react';
import {
    RiArrowDownSLine,
    RiFontSize,
    RiSubtractLine,
    RiAddLine,
    RiSunLine,
    RiMoonLine,
} from 'react-icons/ri';

import { ThemeContext } from '@/context/ThemeContext.jsx';

const MIN_FONT_SIZE = 14;
const MAX_FONT_SIZE = 20;
const DEFAULT_FONT_SIZE = 16;

function getCurrentFontSize() {
    const root = document.documentElement;
    const currentFontSize = window.getComputedStyle(root).fontSize;

    return Number.parseInt(currentFontSize, 10) || DEFAULT_FONT_SIZE;
}

export function AccessibilityDropdown() {
    const [open, setOpen] = useState(false);
    const [fontSize, setFontSize] = useState(getCurrentFontSize);
    const { theme, toggleTheme } = useContext(ThemeContext);

    const updateFontSize = (newFontSize) => {
        const safeFontSize = Math.min(
            Math.max(newFontSize, MIN_FONT_SIZE),
            MAX_FONT_SIZE
        );

        document.documentElement.style.fontSize = `${safeFontSize}px`;
        setFontSize(safeFontSize);
    };

    const increaseFontSize = () => {
        updateFontSize(fontSize + 1);
    };

    const decreaseFontSize = () => {
        updateFontSize(fontSize - 1);
    };

    return (
        <div>
            <button
                type="button"
                onClick={() => setOpen((currentValue) => !currentValue)}
                className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm transition-colors hover:bg-black/10 dark:hover:bg-white/10"
                aria-expanded={open}
            >
                <span className={`flex items-center gap-2 ${!open ? 'text-gray-400' : ''}`}>
                    <RiFontSize />
                    Accesibilidad
                </span>

                <RiArrowDownSLine
                    className={`text-lg transition-transform duration-300 ${open ? 'rotate-180' : ''
                        }`}
                />
            </button>

            <div
                className={`mt-1 overflow-hidden rounded-xl bg-black/5 transition-all duration-300 ease-out dark:bg-white/5 ${open
                        ? 'max-h-48 scale-100 opacity-100 p-2'
                        : 'max-h-0 scale-95 opacity-0 p-0'
                    }`}
            >
                <div
                    className={`space-y-1 transition-transform duration-300 ease-out ${open ? 'translate-y-0' : '-translate-y-2'
                        }`}
                >
                    <button
                        type="button"
                        onClick={increaseFontSize}
                        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-black/10 dark:hover:bg-white/10"
                    >
                        <RiAddLine />
                        Aumentar fuente
                    </button>

                    <button
                        type="button"
                        onClick={decreaseFontSize}
                        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-black/10 dark:hover:bg-white/10"
                    >
                        <RiSubtractLine />
                        Reducir fuente
                    </button>

                    <button
                        type="button"
                        onClick={(event) => toggleTheme(event)}
                        aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
                        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-black/10 dark:hover:bg-white/10"
                    >
                        {theme === 'dark' ? <RiSunLine /> : <RiMoonLine />}
                        Cambiar tema
                    </button>
                </div>
            </div>
        </div>
    );
}