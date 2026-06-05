import React from 'react';
import { RiCloseLine, RiSearchLine } from 'react-icons/ri';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

const ORDER_OPTIONS = [
    { value: 'puntuacion', label: 'Mejor puntuación' },
    { value: 'opiniones', label: 'Más opiniones' },
    { value: 'rating', label: 'Mejor rating' },
];

const CONFIDENCE_OPTIONS = [
    { value: '', label: 'Todas' },
    { value: 'alta', label: 'Alta' },
    { value: 'media', label: 'Media' },
    { value: 'baja', label: 'Baja' },
    { value: 'sospechosa', label: 'Sospechosa' },
];

export function TraditionalSearchForm({
    filters,
    onFiltersChange,
    onSearch,
    onClear,
}) {
    const updateFilter = (field, value) => {
        onFiltersChange({
            ...filters,
            [field]: value,
        });
    };

    return (
        <div className="space-y-5">
            <div className="space-y-1.5">
                <Input
                    id="especialidad"
                    label="Especialidad"
                    placeholder="Ej: Dentista, Cardiólogo..."
                    value={filters.especialidad}
                    onChange={(event) => updateFilter('especialidad', event.target.value)}
                />
            </div>

            <div className="space-y-1.5">
                <Input
                    id="ciudad"
                    label="Ciudad"
                    placeholder="Ej: Ciudad de México"
                    value={filters.ciudad}
                    onChange={(event) => updateFilter('ciudad', event.target.value)}
                />
            </div>

            <div className="space-y-2">
                <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                    Tipo de paciente
                </p>

                <div className="space-y-2">
                    <CheckboxOption
                        label="Niños"
                        checked={filters.atiendeNinos}
                        onChange={(checked) => updateFilter('atiendeNinos', checked)}
                    />

                    <CheckboxOption
                        label="Adultos"
                        checked={filters.atiendeAdultos}
                        onChange={(checked) => updateFilter('atiendeAdultos', checked)}
                    />

                    <CheckboxOption
                        label="Adolescentes"
                        checked={filters.atiendeAdolescentes}
                        onChange={(checked) => updateFilter('atiendeAdolescentes', checked)}
                    />
                </div>
            </div>

            <div className="space-y-1.5">
                <label
                    htmlFor="orden"
                    className="block text-xs font-medium"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Ordenar por
                </label>

                <select
                    id="orden"
                    value={filters.orden}
                    onChange={(event) => updateFilter('orden', event.target.value)}
                    className="glass-input w-full px-3 py-2 text-sm"
                >
                    {ORDER_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
            </div>

            <div className="space-y-1.5">
                <label
                    htmlFor="confiabilidad"
                    className="block text-xs font-medium"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Confiabilidad
                </label>

                <select
                    id="confiabilidad"
                    value={filters.confiabilidad}
                    onChange={(event) => updateFilter('confiabilidad', event.target.value)}
                    className="glass-input w-full px-3 py-2 text-sm"
                >
                    {CONFIDENCE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
            </div>

            <CheckboxOption
                label="Solo con análisis NLP disponible"
                checked={filters.soloAnalizados}
                onChange={(checked) => updateFilter('soloAnalizados', checked)}
            />

            <div className="space-y-2 pt-2">
                <Button variant="primary" fullWidth onClick={onSearch}>
                    <RiSearchLine />
                    Buscar
                </Button>

                <Button variant="ghost" fullWidth onClick={onClear}>
                    <RiCloseLine />
                    Limpiar
                </Button>
            </div>
        </div>
    );
}

function CheckboxOption({ label, checked, onChange }) {
    return (
        <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
                type="checkbox"
                checked={checked}
                onChange={(event) => onChange(event.target.checked)}
                className="h-4 w-4 rounded border-white/20 bg-white/10 text-royalBlue-600 focus:ring-royalBlue-500"
            />
            {label}
        </label>
    );
}