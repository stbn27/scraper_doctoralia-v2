# Variables de entorno 📓

El proyecto usa archivos de entorno distintos para desarrollo y producción. No todos sirven para lo mismo y no conviene mezclarlos sin revisar hostnames, puertos y secretos.

## Archivos usados 📝

| Archivo | Uso recomendado | Lo consume |
|---|---|---|
| `.env` | Desarrollo con `docker-compose.yml`. | Compose raíz y contenedor `backend`. |
| `backend/.env` | Desarrollo local del backend fuera de Docker o base para crear producción. | Backend cuando se ejecuta manualmente. |
| `backend/.env.prod` | Producción con `docker-compose.prod.yml`. | Backend productivo y MySQL productivo. |

## Diferencias importantes 💥

| Variable | Desarrollo | Producción Docker |
|---|---|---|
| `MYSQL_HOST` | `127.0.0.1` o `mysql` según cómo arranques. | `mysql_prod` |
| `MYSQL_PORT` | `3310` desde el host; `3306` entre contenedores. | `3306` entre contenedores. |
| `MONGO_URL_DOCTORALIA` | Puede apuntar a `127.0.0.1:27017` desde el host o `mongodb:27017` dentro de Docker. | Debe apuntar a `mongodb_prod:27017`. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` desde host o `http://ollama:11434` dentro de Docker. | `http://ollama_prod:11434` si se activa el perfil. |
| `LMSTUDIO_BASE_URL` | Usualmente `http://127.0.0.1:1234` fuera de Docker. | `http://host.docker.internal:1234` si LM Studio corre en el host. |

## Variables mínimas 🗯️

```env
MYSQL_ROOT_PASSWORD=...
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=...
MYSQL_DATABASE=medicos_db

MONGO_URL_DOCTORALIA=mongodb://admin:password123@mongodb:27017/doctoralia?authSource=admin
MONGO_DB_DOCTORALIA=doctoralia

SECRET_KEY=...
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

MODELO_ACTIVO=lmstudio
LMSTUDIO_BASE_URL=http://host.docker.internal:1234
LMSTUDIO_MODEL=...
```

## ¿Se puede usar un solo archivo? 💬

Sí se puede, pero no es lo más cómodo para este proyecto. El problema no es el formato `.env`, sino que desarrollo y producción necesitan valores diferentes para hostnames y puertos.

La opción más segura es mantener:

- `.env` para desarrollo con `docker-compose.yml`.
- `backend/.env.prod` para producción con `docker-compose.prod.yml`.

Si quieres usar un solo archivo, tendría que estar diseñado para Docker y evitar valores como `127.0.0.1` cuando el backend corre dentro de un contenedor. En ese caso también tendrías que apuntar `env_file` de ambos compose al mismo archivo y aceptar que producción/desarrollo compartirán credenciales.
