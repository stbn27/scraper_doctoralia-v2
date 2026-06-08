/**
 * selectStyles.js — Estilos reutilizables para react-select
 * Adaptados al sistema de diseño MedRec (modo claro/oscuro).
 *
 * Uso:
 *   import Select from 'react-select';
 *   import { selectStyles } from '@/components/ui/selectStyles';
 *
 *   <Select styles={selectStyles} ... />
 */

/** Estilos base que usan CSS variables del proyecto */
export const selectStyles = {
  control: (base, state) => ({
    ...base,
    minHeight: '38px',
    borderRadius: '0.5rem',
    background: 'var(--glass-bg)',
    borderColor: state.isFocused
      ? 'var(--color-primary-400)'
      : 'rgba(255, 255, 255, 0.08)',
    boxShadow: state.isFocused
      ? '0 0 0 2px rgba(96, 165, 250, 0.2)'
      : 'none',
    backdropFilter: 'var(--glass-blur)',
    cursor: 'pointer',
    transition: 'border-color 150ms ease, box-shadow 150ms ease',
    '&:hover': {
      borderColor: 'rgba(255, 255, 255, 0.18)',
    },
  }),
  menu: (base) => ({
    ...base,
    zIndex: 50,
    borderRadius: '0.75rem',
    overflow: 'hidden',
    background: 'var(--bg-body)',
    border: '1px solid var(--glass-border)',
  }),
  option: (base, state) => ({
    ...base,
    cursor: 'pointer',
    background: state.isSelected
      ? 'var(--color-primary-600)'
      : state.isFocused
        ? 'rgba(59, 130, 246, 0.18)'
        : 'transparent',
    color: state.isSelected ? '#fff' : 'var(--text-primary)',
  }),
  singleValue: (base) => ({
    ...base,
    color: 'var(--text-primary)',
  }),
  multiValue: (base) => ({
    ...base,
    backgroundColor: 'rgba(99, 102, 241, 0.3)',
    borderRadius: '0.375rem',
  }),
  multiValueLabel: (base) => ({
    ...base,
    color: 'var(--text-primary)',
  }),
  multiValueRemove: (base) => ({
    ...base,
    color: 'var(--text-primary)',
    '&:hover': {
      backgroundColor: 'rgba(239, 68, 68, 0.4)',
      color: '#fff',
    },
  }),
  input: (base) => ({
    ...base,
    color: 'var(--text-primary)',
  }),
  placeholder: (base) => ({
    ...base,
    color: 'var(--text-muted)',
  }),
  dropdownIndicator: (base) => ({
    ...base,
    color: 'var(--text-muted)',
  }),
  indicatorSeparator: (base) => ({
    ...base,
    backgroundColor: 'var(--glass-border)',
  }),
  clearIndicator: (base) => ({
    ...base,
    color: 'var(--text-muted)',
    cursor: 'pointer',
    '&:hover': {
      color: 'var(--text-primary)',
    },
  }),
  noOptionsMessage: (base) => ({
    ...base,
    color: 'var(--text-muted)',
  }),
};
