import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { RiCloseLine, RiMapPinLine, RiSearchLine, RiMenuSearchLine } from 'react-icons/ri';
import Select from 'react-select';
import makeAnimated from 'react-select/animated';

import { Button } from '@/components/ui/Button';
import { selectStyles } from '@/components/ui/selectStyles';
import { buscarUbicaciones } from '@/services/ubicaciones.api';

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

/** Retorna el ícono/badge del tipo de ubicación */
function TipoBadge({ tipo }) {
    const estilos = {
        ciudad: { bg: 'rgba(79,125,255,0.15)', color: '#4f7dff', texto: 'Ciudad' },
        estado: { bg: 'rgba(100,200,100,0.15)', color: '#4caf50', texto: 'Estado' },
        alcaldia: { bg: 'rgba(255,165,0,0.15)', color: '#ff9800', texto: 'Alcaldía' },
        municipio: { bg: 'rgba(255,165,0,0.15)', color: '#ff9800', texto: 'Municipio' },
    };
    const est = estilos[tipo] || estilos.ciudad;
    return (
        <span style={{
            fontSize: '10px',
            fontWeight: 600,
            padding: '1px 6px',
            borderRadius: '999px',
            background: est.bg,
            color: est.color,
            flexShrink: 0,
        }}>
            {est.texto}
        </span>
    );
}

/**
 * Combobox de ubicación con autocompletado dinámico desde la API.
 * Soporta búsqueda por ciudad, alcaldía, municipio y estado.
 *
 * @param {Object}   props
 * @param {string}   props.valor         - Valor actual (slug de ubicación)
 * @param {string}   props.valorTexto    - Texto mostrado actualmente
 * @param {Function} props.onChange      - Callback al seleccionar: ({ slug, nombre, tipo })
 * @param {Function} props.onClear       - Callback al limpiar
 */
function ComboboxUbicacion({ valor, valorTexto, onChange, onClear }) {
    const [texto, setTexto] = useState(valorTexto || '');
    const [sugerencias, setSugerencias] = useState([]);
    const [abierto, setAbierto] = useState(false);
    const [cargando, setCargando] = useState(false);
    const [indiceFoco, setIndiceFoco] = useState(-1);
    const timerRef = useRef(null);
    const inputRef = useRef(null);
    const listaRef = useRef(null);

    // Sincronizar texto con valor externo
    useEffect(() => {
        if (!valorTexto && !valor) setTexto('');
    }, [valorTexto, valor]);

    const buscar = useCallback(async (q) => {
        if (q.length < 2) {
            setSugerencias([]);
            setAbierto(false);
            return;
        }
        setCargando(true);
        try {
            const resultados = await buscarUbicaciones(q, 12);
            setSugerencias(resultados);
            setAbierto(resultados.length > 0);
            setIndiceFoco(-1);
        } catch {
            setSugerencias([]);
        } finally {
            setCargando(false);
        }
    }, []);

    const handleInputChange = (e) => {
        const val = e.target.value;
        setTexto(val);
        if (val !== valorTexto) onChange(null); // Limpiar selección cuando escribe
        clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => buscar(val), 280);
    };

    const handleSeleccionar = (ubicacion) => {
        setTexto(ubicacion.nombre);
        setSugerencias([]);
        setAbierto(false);
        onChange(ubicacion);
    };

    const handleLimpiar = () => {
        setTexto('');
        setSugerencias([]);
        setAbierto(false);
        onClear();
        inputRef.current?.focus();
    };

    const handleKeyDown = (e) => {
        if (!abierto) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setIndiceFoco((prev) => Math.min(prev + 1, sugerencias.length - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setIndiceFoco((prev) => Math.max(prev - 1, 0));
        } else if (e.key === 'Enter' && indiceFoco >= 0) {
            e.preventDefault();
            handleSeleccionar(sugerencias[indiceFoco]);
        } else if (e.key === 'Escape') {
            setAbierto(false);
        }
    };

    return (
        <div style={{ position: 'relative' }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                background: 'var(--surface-2, rgba(255,255,255,0.06))',
                border: '1px solid var(--border-subtle, rgba(255,255,255,0.12))',
                borderRadius: '8px',
                padding: '0 10px',
                gap: '6px',
                transition: 'border-color 0.2s',
            }}>
                <RiMapPinLine style={{ color: 'var(--text-muted)', flexShrink: 0, fontSize: '14px' }} />
                <input
                    ref={inputRef}
                    id="ubicacion-input"
                    type="text"
                    value={texto}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    onFocus={() => texto.length >= 2 && sugerencias.length > 0 && setAbierto(true)}
                    onBlur={() => setTimeout(() => setAbierto(false), 160)}
                    placeholder="Ciudad, alcaldía o estado..."
                    autoComplete="off"
                    style={{
                        flex: 1,
                        background: 'transparent',
                        border: 'none',
                        outline: 'none',
                        color: 'var(--text-primary, #fff)',
                        fontSize: '14px',
                        padding: '8px 0',
                    }}
                />
                {cargando && (
                    <span style={{
                        width: 14, height: 14, border: '2px solid var(--text-muted)',
                        borderTopColor: '#4f7dff', borderRadius: '50%',
                        animation: 'spin 0.7s linear infinite', flexShrink: 0,
                    }} />
                )}
                {texto && !cargando && (
                    <button
                        type="button"
                        onClick={handleLimpiar}
                        style={{
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: 'var(--text-muted)', padding: '2px', display: 'flex',
                            alignItems: 'center', flexShrink: 0,
                        }}
                        aria-label="Limpiar ubicación"
                    >
                        <RiCloseLine size={14} />
                    </button>
                )}
            </div>

            {/* Dropdown de sugerencias */}
            {abierto && sugerencias.length > 0 && (
                <ul
                    ref={listaRef}
                    role="listbox"
                    style={{
                        position: 'absolute',
                        top: 'calc(100% + 4px)',
                        left: 0,
                        right: 0,
                        zIndex: 9999,
                        background: 'var(--surface-elevated, #1a1a2e)',
                        border: '1px solid var(--border-subtle, rgba(255,255,255,0.12))',
                        borderRadius: '8px',
                        padding: '4px 0',
                        margin: 0,
                        listStyle: 'none',
                        boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                        maxHeight: '220px',
                        overflowY: 'auto',
                    }}
                >
                    {sugerencias.map((sug, idx) => (
                        <li
                            key={sug.slug + sug.tipo}
                            role="option"
                            aria-selected={idx === indiceFoco}
                            onMouseDown={() => handleSeleccionar(sug)}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                gap: '8px',
                                padding: '8px 12px',
                                cursor: 'pointer',
                                fontSize: '13px',
                                color: idx === indiceFoco ? '#fff' : 'var(--text-secondary, #ccc)',
                                background: idx === indiceFoco ? 'rgba(79,125,255,0.12)' : 'transparent',
                                transition: 'background 0.15s',
                            }}
                            onMouseEnter={() => setIndiceFoco(idx)}
                        >
                            <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {sug.nombre}
                            </span>
                            <TipoBadge tipo={sug.tipo} />
                        </li>
                    ))}
                </ul>
            )}

            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
    );
}

/**
 * Formulario de búsqueda tradicional de especialistas.
 *
 * Props
 * -----
 * @param {Object}   props
 * @param {Object}   props.filters            - Estado de filtros activos
 * @param {Function} props.onFiltersChange    - Actualiza el estado de filtros
 * @param {Function} props.onSearch           - Dispara la búsqueda
 * @param {Function} props.onClear            - Limpia todos los filtros
 * @param {Array}    props.specialties        - Lista de especialidades del catálogo
 * @param {boolean}  props.catalogsLoading    - Estado de carga del catálogo
 */
export function TraditionalSearchForm({
    filters,
    onFiltersChange,
    onSearch,
    onClear,
    specialties = [],
    catalogsLoading = false,
}) {
    const [inputEspecialidad, setInputEspecialidad] = useState('');
    // Texto legible de la ubicación seleccionada (puede ser diferente al slug)
    const [textoUbicacion, setTextoUbicacion] = useState(filters.ciudad || '');

    const updateFilter = (field, value) => {
        onFiltersChange({ ...filters, [field]: value });
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

    const handleUbicacionChange = (ubicacion) => {
        if (!ubicacion) {
            updateFilter('ciudad', '');
            return;
        }
        // Guardar el slug como valor del filtro y el nombre legible para mostrar
        setTextoUbicacion(ubicacion.nombre);
        // Usar searchLoc para el filtro de ciudad (más compatible con los datos)
        updateFilter('ciudad', ubicacion.searchLoc || ubicacion.nombre || ubicacion.slug);
    };

    const handleUbicacionLimpiar = () => {
        setTextoUbicacion('');
        updateFilter('ciudad', '');
    };

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

            {/* Ciudad / Alcaldía / Estado — combobox dinámico */}
            <div className="space-y-1.5">
                <label
                    htmlFor="ubicacion-input"
                    className="block text-xs font-medium"
                    style={{ color: 'var(--text-muted)' }}
                >
                    Ciudad, Alcaldía o Estado
                </label>
                <ComboboxUbicacion
                    valor={filters.ciudad}
                    valorTexto={textoUbicacion}
                    onChange={handleUbicacionChange}
                    onClear={handleUbicacionLimpiar}
                />
            </div>

            {/* Tipo de paciente */}
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

            <div className="pt-2 border-t border-royalBlue-900"></div>

            {/* Boton de búsqueda avanzada */}
            <Button variant="outline" className="mt-1 text-royalBlue-200/40" fullWidth>
                <RiMenuSearchLine />
                Búsqueda avanzada
            </Button>
        </div>
    );
}