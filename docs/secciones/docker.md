# Docker 🪣

El proyecto tiene dos perfiles principales: desarrollo y producción. Ambos usan MongoDB y MySQL, pero cambian la forma de ejecutar backend y frontend.

## Desarrollo ✏️

Archivo principal: `docker-compose.yml`.

```bash
docker compose up -d
docker compose ps
```

Características: 📍

| Servicio | Contenedor | Puerto host | Nota |
|---|---|---:|---|
| MongoDB | `mongodb` | `27017` | Base documental Doctoralia. |
| MySQL | `mysql` | `3310` | Base relacional `medicos_db`. |
| Backend | `backend` | `8000` | FastAPI con código montado. |
| Frontend | `frontend` | `5173` | Vite en desarrollo. |
| Ollama | `ollama`, `ollama2` | `11434`, `11435` | Opcional con perfil `ollama`. |

Activar Ollama en desarrollo:

```bash
docker compose --profile ollama up -d ollama
```

## Producción 🚀

Archivo principal: `docker-compose.prod.yml`.

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

Características: 📍

| Servicio | Contenedor | Puerto host | Nota |
|---|---|---:|---|
| MongoDB | `mongodb_prod` | `27017` | Caché WiredTiger limitada. |
| MySQL | `mysql_prod` | `3310` | Lee variables desde `backend/.env.prod`. |
| Backend | `backend_prod` | `8000` | Imagen productiva sin hot reload. |
| Frontend | `frontend_prod` | `80` | Build estático servido por Nginx. |
| Ollama | `ollama_prod` | `11434` | Opcional con GPU NVIDIA. |

Activar Ollama en producción:

```bash
docker compose -f docker-compose.prod.yml --profile ollama up -d ollama
```

## Arquitectura de producción 🟢

```mermaid
flowchart TB
    B[Navegador http://localhost] --> N[Nginx frontend_prod:80]
    N --> SPA[Archivos estaticos React]
    N -- /api --> API[backend_prod:8000]
    API --> MYSQL[(mysql_prod:3306)]
    API --> MONGO[(mongodb_prod:27017)]
    API -. opcional .-> OLLAMA[ollama_prod:11434]
    API -. host.docker.internal .-> LM[LM Studio en host:1234]
```

## Logs y mantenimiento 🟡

```bash
# Todos los logs
docker compose logs -f

# Logs de un servicio
docker compose logs --tail=50 -f backend
docker compose logs --tail=50 -f mongodb

# Produccion
docker compose -f docker-compose.prod.yml logs --tail=50 -f backend
docker compose -f docker-compose.prod.yml restart backend
```

## Actualizar después de cambios 🔃

Desarrollo normalmente no requiere reconstruir para cambios de código porque hay volúmenes montados, pero sí para cambios de dependencias o Dockerfile:

```bash
docker compose build backend
docker compose up -d backend
```

Producción sí requiere build:

```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.prod.yml up -d
```

## Datos persistentes

Los datos viven en `./data/`. `docker compose down` detiene y elimina contenedores, pero conserva datos. `docker compose down -v` elimina volúmenes administrados por Docker; además, borrar manualmente `./data/` elimina las bases persistidas del proyecto.

> [!CAUTION]
> No ejecutes limpieza de datos ni borres `./data/` si no tienes backups recientes.
