# Variables de entorno 📓

El proyecto usa archivos de entorno distintos para desarrollo y producción. No todos sirven para lo mismo y no conviene mezclarlos sin revisar hostnames, puertos y secretos.

## Archivos usados 📝

| Archivo | Uso recomendado | Lo consume | Obligatorio |
|---|---|---| --- |
| `.env` | Desarrollo con `docker-compose.yml`. | Compose raíz y contenedor `backend`. | No - Se reemplaza por el archivo `backend/.env`|
| `backend/.env` | Desarrollo local del backend fuera de Docker o base para crear producción. | Backend cuando se ejecuta manualmente. | Obligatorio en Desarrollo |
| `backend/.env.prod` | Producción con `docker-compose.prod.yml`. | Backend productivo y MySQL productivo. | Obligatorio para Producción|

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
MYSQL_ROOT_PASSWORD=esteb@n_27J
MYSQL_DATABASE=medicos_db

MONGO_URL_DOCTORALIA=mongodb://admin:password123@mongodb:27017/doctoralia?authSource=admin
MONGO_DB_DOCTORALIA=doctoralia

SECRET_KEY=HOL@_ESTAMOS_EN_DES4RRR0LL0
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120

# Valores válidos: groq | deepseek | gemini | minimax | ollama | lmstudio
MODELO_ACTIVO=lmstudio

LMSTUDIO_BASE_URL=http://host.docker.internal:1234
LMSTUDIO_MODEL=...
```
## Soporte para diferentes proveedores de IA 🌐

|Modelo|Nombre de la variale|Valor|
|-|-|-|
|**Groq**|`GROQ_API_KEY`|`TU_API_KEY`|
| |`GROQ_MODEL`|`llama-3.3-70b-versatile`|
|**Gemini**|`GEMINI_API_KEY`|`TU_API_KEY`|
| |`GEMINI_MODEL`|`gemini-2.5-flash`|
|**Deepseek**|`DEEPSEEK_BASE_URL_NLP`|`https://api.deepseek.com`|
| |`DEEPSEEK_API_KEY`|`TU_API_KEY`|
| |`DEEPSEEK_MODEL_NLP`|`deepseek-v4-flash`|
|**MiniMax**|`MINIMAX_API_KEY`|`TU_API_KEY`|
| |`MINIMAX_GROUP_ID`|`TU_GROUP_ID`|
| |`MINIMAX_MODEL`|`abab6.5s-chat`|
|**Ollama**|`OLLAMA_BASE_URL`|`http://localhost:11434`|
| |`OLLAMA_MODEL`|`llama3.1:8b`|
|**LMStudio**|`LMSTUDIO_BASE_URL`|`http://host.docker.internal:1234`|
| |`LMSTUDIO_MODEL`|`llama-3.2-1b-instruct`|

> ![NOTE] Para los modelos locales, primero se debe descargar el modelo en LMStudio u Ollama.

**Uso:**
Para usar otro modelo, se debe cambiar la variable `MODELO_ACTIVO` por el nombre del modelo deseado y agregar las variables correspondientes a la tabla de variables de entorno.

## Archivo .env.prod Variables 📝

```env
# MySQL DB
MYSQL_HOST=mysql_prod
MYSQL_ROOT_PASSWORD=esteb@n_27J
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_DATABASE=medicos_db

# Mongo DB
MONGO_URL_DOCTORALIA=mongodb://admin:password123@mongodb_prod:27017/doctoralia?authSource=admin
MONGO_DB_DOCTORALIA=doctoralia

# JWT
SECRET_KEY=HOL@_ESTAMOS_EN_DES4RRR0LL0
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120

# === MODELOS DE IA ===

# LM Studio corre en la máquina anfitriona (NO dentro de Docker).
# En Linux Docker usa host.docker.internal o la IP del gateway (172.17.0.1 por defecto).
# Si host.docker.internal no resuelve, usa: $(ip route | awk '/default/ { print $3 }')
LMSTUDIO_BASE_URL=http://host.docker.internal:1234
LMSTUDIO_MODEL=qwen/qwen3-1.7b

# Ollama (opcional — solo en máquinas con GPU, perfil: --profile ollama)
OLLAMA_BASE_URL=http://ollama_prod:11434
OLLAMA_MODEL=qwen2.5:14b

# Modelo activo para el pipeline de análisis masivo (distinto al chatbot)
MODELO_ACTIVO=lmstudio
```
## ¿Se puede usar un solo archivo? 💬

Sí se puede, pero no es lo más cómodo para este proyecto. El problema no es el formato `.env`, sino que desarrollo y producción necesitan valores diferentes para hostnames y puertos.

La opción más segura es mantener:

- `.env` para desarrollo con `docker-compose.yml`.
- `backend/.env.prod` para producción con `docker-compose.prod.yml`.

Si quieres usar un solo archivo, tendría que estar diseñado para Docker y evitar valores como `127.0.0.1` cuando el backend corre dentro de un contenedor. En ese caso también tendrías que apuntar `env_file` de ambos compose al mismo archivo y aceptar que producción/desarrollo compartirán credenciales.
