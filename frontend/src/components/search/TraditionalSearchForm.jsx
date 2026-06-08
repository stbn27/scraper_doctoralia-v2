import React, { useMemo, useState } from 'react';
import { RiCloseLine, RiSearchLine } from 'react-icons/ri';
import Select from 'react-select';
import makeAnimated from 'react-select/animated';

import { Button } from '@/components/ui/Button';
import { selectStyles } from '@/components/ui/selectStyles';

const animatedComponents = makeAnimated();
const textLikeSelectComponents = {
    ...animatedComponents,
    DropdownIndicator: () => null,
    IndicatorSeparator: () => null,
};

const ORDER_OPTIONS = [
    { value: 'puntuacion_desc', label: 'Mejor puntuación' },
    { value: 'puntuacion_asc', label: 'Menor puntuación' },
    { value: 'opiniones_desc', label: 'Más opiniones' },
    { value: 'opiniones_asc', label: 'Menos opiniones' },
    { value: 'rating_desc', label: 'Mejor rating' },
    { value: 'rating_asc', label: 'Menor rating' },
];

const CONFIDENCE_OPTIONS = [
    { value: '', label: 'Todas' },
    { value: 'alta', label: 'Alta' },
    { value: 'media', label: 'Media' },
    { value: 'baja', label: 'Baja' },
    { value: 'sospechosa', label: 'Sospechosa' },
];

const PATIENT_TYPE_OPTIONS = [
    { value: 'todos', label: 'Todos' },
    { value: 'ninos', label: 'Niños' },
    { value: 'adultos', label: 'Adultos' },
    { value: 'adolescentes', label: 'Adolescentes' },
];

export function TraditionalSearchForm({
    filters,
    onFiltersChange,
    onSearch,
    onClear,
    specialties = [],
    cities = [],
    catalogsLoading = false,
}) {
    const [inputEspecialidad, setInputEspecialidad] = useState('');
    const [inputCiudad, setInputCiudad] = useState('');

    const updateFilter = (field, value) => {
        onFiltersChange({
            ...filters,
            [field]: value,
        });
    };

    const filteredSpecialties = useMemo(
        () =>
            inputEspecialidad.length >= 2
                ? specialties.filter((opt) =>
                    opt.label.toLowerCase().includes(inputEspecialidad.toLowerCase())
                )
                : [],
        [specialties, inputEspecialidad]
    );

    const filteredCities = useMemo(
        () =>
            inputCiudad.length >= 2
                ? cities.filter((opt) =>
                    opt.label.toLowerCase().includes(inputCiudad.toLowerCase())
                )
                : [],
        [cities, inputCiudad]
    );

    return (
        <div className="space-y-5">
            {/* Especialidad con autocompletado */}
            <div className="space-y-1.5">
                <label
                    htmlFor="especialidad-select"
                    className="block text-xs font-medium"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Especialidad
                </label>

                <Select
                    inputId="especialidad-select"
                    placeholder="Ej: Dentista, Cardiólogo..."
                    isClearable
                    isSearchable
                    openMenuOnFocus={false}
                    openMenuOnClick={false}
                    inputValue={inputEspecialidad}
                    onInputChange={(val, { action }) => {
                        if (action === 'input-change') setInputEspecialidad(val);
                        if (action === 'menu-close' || action === 'input-blur') setInputEspecialidad('');
                    }}
                    menuIsOpen={inputEspecialidad.length >= 2 && filteredSpecialties.length > 0}
                    options={filteredSpecialties}
                    value={specialties.find((opt) => opt.value === filters.especialidad) || null}
                    onChange={(selected) => {
                        setInputEspecialidad('');
                        updateFilter('especialidad', selected?.value ?? '');
                    }}
                    onMenuClose={() => setInputEspecialidad('')}
                    isLoading={catalogsLoading}
                    noOptionsMessage={() => 'Sin resultados'}
                    styles={selectStyles}
                    components={textLikeSelectComponents}
                    className="text-sm"
                />
            </div>

            {/* Ciudad con autocompletado */}
            <div className="space-y-1.5">
                <label
                    htmlFor="ciudad-select"
                    className="block text-xs font-medium"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Ciudad
                </label>

                <Select
                    inputId="ciudad-select"
                    placeholder="Ej: Ciudad de México"
                    isClearable
                    isSearchable
                    openMenuOnFocus={false}
                    openMenuOnClick={false}
                    inputValue={inputCiudad}
                    onInputChange={(val, { action }) => {
                        if (action === 'input-change') setInputCiudad(val);
                        if (action === 'menu-close' || action === 'input-blur') setInputCiudad('');
                    }}
                    menuIsOpen={inputCiudad.length >= 2 && filteredCities.length > 0}
                    options={filteredCities}
                    value={cities.find((opt) => opt.value === filters.ciudad) || null}
                    onChange={(selected) => {
                        setInputCiudad('');
                        updateFilter('ciudad', selected?.value ?? '');
                    }}
                    onMenuClose={() => setInputCiudad('')}
                    isLoading={catalogsLoading}
                    noOptionsMessage={() => 'Sin resultados'}
                    styles={selectStyles}
                    components={textLikeSelectComponents}
                    className="text-sm"
                />
            </div>

            {/* Tipo de paciente — selección única */}
            <div className="space-y-1.5">
                <label
                    htmlFor="tipo-paciente"
                    className="block text-xs font-medium"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Tipo de paciente
                </label>

                <Select
                    inputId="tipo-paciente"
                    isClearable={filters.tipoPaciente !== 'todos'}
                    isSearchable={false}
                    options={PATIENT_TYPE_OPTIONS}
                    value={PATIENT_TYPE_OPTIONS.find((opt) => opt.value === filters.tipoPaciente) ?? PATIENT_TYPE_OPTIONS[0]}
                    onChange={(selected) => updateFilter('tipoPaciente', selected?.value ?? 'todos')}
                    styles={selectStyles}
                    components={animatedComponents}
                    className="text-sm"
                />
            </div>

            {/* Ordenar por */}
            <div className="space-y-1.5">
                <label
                    htmlFor="orden-select"
                    className="block text-xs font-medium"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Ordenar por
                </label>

                <Select
                    inputId="orden-select"
                    placeholder="Seleccionar orden"
                    isClearable={false}
                    isSearchable={false}
                    options={ORDER_OPTIONS}
                    value={ORDER_OPTIONS.find((opt) => opt.value === filters.orden) || ORDER_OPTIONS[0]}
                    onChange={(selected) => updateFilter('orden', selected?.value || 'puntuacion_desc')}
                    styles={selectStyles}
                    components={animatedComponents}
                    className="text-sm"
                />
            </div>

            {/* Confiabilidad */}
            <div className="space-y-1.5">
                <label
                    htmlFor="confiabilidad-select"
                    className="block text-xs font-medium"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Confiabilidad
                </label>

                <Select
                    inputId="confiabilidad-select"
                    placeholder="Todas"
                    isClearable
                    isSearchable={false}
                    options={CONFIDENCE_OPTIONS}
                    value={CONFIDENCE_OPTIONS.find((opt) => opt.value === filters.confiabilidad) || CONFIDENCE_OPTIONS[0]}
                    onChange={(selected) => updateFilter('confiabilidad', selected?.value || '')}
                    styles={selectStyles}
                    components={animatedComponents}
                    className="text-sm"
                />
            </div>

            {/* Solo con análisis NLP disponible */}
            <div>
                <label className="flex cursor-pointer items-center gap-3 text-sm">
                    <div className="relative">
                        <input
                            type="checkbox"
                            checked={filters.soloAnalizados}
                            onChange={(event) => updateFilter('soloAnalizados', event.target.checked)}
                            className="peer sr-only"
                        />
                        <div className="h-5 w-9 rounded-full bg-white/20 transition-colors peer-checked:bg-royalBlue-600" />
                        <div className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform peer-checked:translate-x-4" />
                    </div>
                    <span style={{ color: 'var(--text-muted)' }}>
                        Solo con análisis NLP disponible
                    </span>
                </label>
            </div>

            {/* Botones */}
            <div className="flex gap-2 pt-2">
                <Button variant="ghost" fullWidth onClick={onClear}>
                    <RiCloseLine />
                    Limpiar
                </Button>

                <Button variant="primary" fullWidth onClick={onSearch}>
                    <RiSearchLine />
                    Buscar
                </Button>
            </div>
        </div>
    );
}