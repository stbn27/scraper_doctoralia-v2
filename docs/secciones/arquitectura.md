# Arquitectura del sistema

MedRec separa la experiencia de usuario, la API, la persistencia y los procesos de enriquecimiento de datos. El frontend consume una API REST; la API consulta MySQL para identidad y datos de usuario, MongoDB para perfiles médicos, reseñas y análisis, y usa servicios NLP/scraping para generar información adicional.

![Arquitectura general](../figures/arquitectura-general.png)

## Diagrama lógico

```mermaid
flowchart LR
    subgraph Cliente
        FE[React + Vite]
    end

    subgraph Backend
        API[FastAPI]
        ROUTERS[Routers API]
        SERVICES[Servicios]
        REPOS[Repositorios]
        NLP[Pipeline NLP]
        SCRAPER[Scraper Doctoralia]
    end

    subgraph Datos
        MYSQL[(MySQL)]
        MONGO[(MongoDB Doctoralia)]
    end

    subgraph IA
        LMSTUDIO[LM Studio externo]
        OLLAMA[Ollama opcional]
        REMOTOS[Groq / Gemini / DeepSeek / MiniMax]
    end

    FE --> API
    API --> ROUTERS
    ROUTERS --> SERVICES
    SERVICES --> REPOS
    REPOS --> MYSQL
    REPOS --> MONGO
    SERVICES --> NLP
    SERVICES --> SCRAPER
    NLP --> LMSTUDIO
    NLP --> OLLAMA
    NLP --> REMOTOS
    SCRAPER --> MONGO
```

## Componentes principales

| Componente | Directorio | Responsabilidad |
|---|---|---|
| Frontend | `frontend/src` | SPA React, rutas públicas, sesión, favoritos, historial, búsqueda y administración. |
| API | `backend/app/api` | Endpoints FastAPI por dominio: usuarios, especialistas, catálogos, chatbot y administración. |
| Servicios | `backend/app/services` | Lógica de negocio reutilizable, búsqueda avanzada, chat y operaciones sobre especialistas. |
| Repositorios | `backend/app/db` | Conexión y consultas a MySQL/MongoDB. |
| NLP | `backend/app/nlp` | Preprocesamiento de opiniones, prompts, selección de modelo y persistencia de análisis. |
| Scraper | `backend/app/scraper` | Extracción de catálogos, listados, perfiles y opiniones desde Doctoralia. |
| Docker | `docker-compose.yml`, `docker-compose.prod.yml` | Orquestación de desarrollo y producción. |

## Flujo de búsqueda

```mermaid
sequenceDiagram
    actor U as Usuario
    participant F as Frontend
    participant A as FastAPI
    participant M as MongoDB
    participant S as Servicio busqueda

    U->>F: Ingresa filtros o consulta
    F->>A: GET /especialistas
    A->>S: Normaliza filtros y paginacion
    S->>M: Consulta perfiles, opiniones y analisis
    M-->>S: Resultados documentales
    S-->>A: Tarjetas enriquecidas
    A-->>F: JSON paginado
    F-->>U: Lista de especialistas
```

## Persistencia

MySQL guarda información relacional del usuario: roles, cuentas, direcciones, favoritos, historial de búsqueda y tokens LLM. MongoDB Doctoralia guarda información documental: perfiles médicos, opiniones, catálogos de especialidades/ciudades y análisis semánticos.

```mermaid
erDiagram
    ROLES ||--o{ USUARIOS : asigna
    USUARIOS ||--o{ USUARIOS_DIRECCIONES : define
    USUARIOS ||--o{ FAVORITOS : guarda
    USUARIOS ||--o{ HISTORIAL_BUSQUEDAS : registra
    USUARIOS ||--o{ TOKENS_LLM : almacena
```

## Proveedores IA

El sistema puede trabajar con proveedores remotos y locales. LM Studio se ejecuta fuera del `docker-compose` del proyecto y el backend lo consume por HTTP. Ollama es opcional y se activa con perfil Docker cuando existe GPU NVIDIA. Los proveedores remotos dependen de sus API keys.

La selección exacta depende del flujo: el pipeline CLI puede usar `MODELO_ACTIVO` o argumento `--modelo`; el chatbot prioriza proveedores locales disponibles antes de probar proveedores externos configurados.
