# Arranque y verificación

Los comandos están escritos para Linux. En Windows se recomienda usar WSL, Git Bash o buscar equivalencias de PowerShell, especialmente para redirecciones, `gzip`, `gunzip`, `date` y rutas.

## Primera carga recomendada

Como los backups están preparados para restaurarse en contenedores Docker, el flujo recomendado es:

1. Preparar variables de entorno.
2. Levantar solo las bases de datos.
3. Copiar/restaurar backups dentro de los contenedores.
4. Levantar backend y frontend.
5. Verificar API, frontend y datos.

## Desarrollo con Docker

```bash
# Desde la raiz del proyecto
docker compose up -d mongodb mysql
docker compose ps
```

Restaura las bases con los comandos de [Carga y respaldo de bases de datos](./base-datos.md). Después levanta todo:

```bash
docker compose up -d
docker compose ps
```

Servicios esperados:

| Servicio | URL |
|---|---|
| Frontend | `http://localhost:5173` |
| API | `http://localhost:8000` |
| Swagger | `http://localhost:8000/docs` |
| Health check | `http://localhost:8000/health` |

## Producción con Docker

```bash
cp backend/.env backend/.env.prod
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d mongodb mysql
```

Restaura las bases y luego levanta el resto:

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

En producción, el frontend se sirve por Nginx:

```text
http://localhost
```

## Verificación básica

```bash
docker compose ps
docker compose logs --tail=50 backend
docker compose logs --tail=50 frontend
```

Valida la API:

```bash
curl http://localhost:8000/health
```

Respuesta esperada:

```json
{
  "api": "ok",
  "mysql": "ok",
  "mongodb": "ok"
}
```

Valida datos mínimos:

```bash
docker exec -it mongodb mongosh \
  "mongodb://admin:password123@localhost:27017/?authSource=admin" \
  --eval "db.getSiblingDB('doctoralia').getCollectionNames()"

docker exec -it mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD" \
  -e "SHOW TABLES FROM medicos_db;"
```

## Problemas frecuentes

| Síntoma | Revisión |
|---|---|
| El backend no conecta con MySQL | Revisa `MYSQL_HOST`, `MYSQL_PORT` y que MySQL esté saludable. |
| El backend no conecta con MongoDB | Revisa `MONGO_URL_DOCTORALIA` y que el hostname sea `mongodb` o `mongodb_prod`, no `127.0.0.1` dentro de Docker. |
| El frontend carga pero la API falla | Revisa CORS en desarrollo o el proxy `/api/` de Nginx en producción. |
| El análisis IA no responde | Verifica `MODELO_ACTIVO`, API keys o que LM Studio/Ollama estén levantados. |
| No aparecen médicos | Restaura primero MongoDB Doctoralia y verifica colecciones como `doctor_profiles`, `doctor_opinions` y `analisis_especialistas`. |
