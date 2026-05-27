import React from 'react';
import { RiSearch2Line, RiHeartLine, RiHistoryLine, RiUserLine } from 'react-icons/ri';

/**
 * Sidebar — Navegación lateral del Dashboard.
 * @param {{ activeSection: string, onSectionChange: (section: string) => void }} props
 * @example
 * <Sidebar activeSection="favoritos" onSectionChange={setSection} />
 */
export function Sidebar({ activeSection, onSectionChange }) {
  const sections = [
    { id: 'buscar', label: 'Buscar especialistas', icon: RiSearch2Line },
    { id: 'favoritos', label: 'Mis favoritos', icon: RiHeartLine },
    { id: 'historial', label: 'Historial de búsquedas', icon: RiHistoryLine },
    { id: 'perfil', label: 'Mi perfil', icon: RiUserLine },
  ];

  return (
    <aside className="glass-card p-3 space-y-1 w-full lg:w-64 min-h-72 h-full shrink-0">
      <h3 className="text-xs uppercase font-semibold px-3 py-2" style={{ color: 'var(--text-muted)' }}>
        Menú
      </h3>
      {sections.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onSectionChange(id)}
          className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${activeSection === id
            ? 'bg-royalBlue-600/30 text-royalBlue-700 dark:text-royalBlue-300'
            : 'hover:bg-white/10 text-black/60 dark:text-white/70 hover:text-black/90 dark:hover:text-white transition-colors'
            }`}
        >
          <Icon className="text-lg" />
          {label}
        </button>
      ))}
    </aside>
  );
}
