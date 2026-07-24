# Carga y respaldo de bases de datos

Las copias incluidas fueron preparadas para restaurarse dentro de contenedores Docker. Para cargar el proyecto por primera vez, levanta primero las bases, copia la copia de seguridad al contenedor y después arranca backend/frontend.

## Backups incluidos

| Motor | Archivo | Contenido |
|---|---|---|
| MongoDB | `backups/mongo/v2/doctoralia_backup_v2_2.gz` | Backup comprimido de la base Doctoralia. |
| MongoDB | `backups/mongo/v2/doctoralia_backup_v2_1.gz` | Backup alternativo v2. |
| MySQL | `backups/mysql/medicos_db_2026-07-02_235402.sql.gz` | Backup completo comprimido con datos. |
| MySQL | `backups/mysql/sql/medicos_db_2026-07-02_235445_schema.sql` | Solo estructura, sin datos. |

Para una restauración funcional del sistema se recomienda usar MongoDB v2 y el backup MySQL completo `.sql.gz`.

## Restaurar MongoDB

Desarrollo:

```bash
docker compose up -d mongodb
docker cp backups/mongo/v2/doctoralia_backup_v2_2.gz mongodb:/dump.gz
docker exec -it mongodb mongorestore \
  --archive=/dump.gz \
  --gzip \
  --uri="mongodb://admin:password123@localhost:27017/doctoralia?authSource=admin" \
  --nsExclude="admin.*" \
  --nsExclude="local.*"
```

Producción:

```bash
docker compose -f docker-compose.prod.yml up -d mongodb
docker cp backups/mongo/v2/doctoralia_backup_v2_2.gz mongodb_prod:/dump.gz
docker exec -it mongodb_prod mongorestore \
  --archive=/dump.gz \
  --gzip \
  --uri="mongodb://admin:password123@localhost:27017/doctoralia?authSource=admin" \
  --nsExclude="admin.*" \
  --nsExclude="local.*"
```

Validación:

```bash
docker exec -it mongodb mongosh \
  "mongodb://admin:password123@localhost:27017/?authSource=admin" \
  --eval "db.getSiblingDB('doctoralia').getCollectionNames()"
```

## Restaurar MySQL

Linux:

```bash
docker compose up -d mysql
gunzip < backups/mysql/medicos_db_2026-07-02_235402.sql.gz | \
  docker exec -i mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD" medicos_db
```

Producción en Linux:

```bash
docker compose -f docker-compose.prod.yml up -d mysql
gunzip < backups/mysql/medicos_db_2026-07-02_235402.sql.gz | \
  docker exec -i mysql_prod mysql -u root -p"$MYSQL_ROOT_PASSWORD" medicos_db
```

Windows PowerShell:

```powershell
docker compose up -d mysql
gzip -dc backups/mysql/medicos_db_2026-07-02_235402.sql.gz | docker exec -i mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" medicos_db
```

Si PowerShell no tiene `gzip`, usa WSL, Git Bash o descomprime el archivo primero:

```powershell
docker exec -i mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" medicos_db < backups/mysql/medicos_db_2026-07-02_235402.sql
```

Validación:

```bash
docker exec -it mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD" \
  -e "SHOW TABLES FROM medicos_db;"
```

## Exportar nuevas copias

La nomenclatura recomendada mantiene el patrón actual:

```text
backups/mysql/medicos_db_YYYY-MM-DD_HHMMSS.sql.gz
backups/mysql/sql/medicos_db_YYYY-MM-DD_HHMMSS_schema.sql
backups/mongo/v2/doctoralia_backup_v2_N.gz
```

### MySQL con datos

Conviene conservar el backup completo comprimido como `backups/mysql/medicos_db_YYYY-MM-DD_HHMMSS.sql.gz`. Es más portable, pesa menos y contiene datos. El archivo plano `backups/mysql/sql/..._schema.sql` es útil para revisar estructura o versionar cambios de esquema, pero no sustituye una copia completa porque no trae datos.

Linux:

```bash
mkdir -p backups/mysql backups/mysql/sql
docker exec -i mysql mysqldump \
  -u root -p"$MYSQL_ROOT_PASSWORD" \
  --single-transaction --routines --triggers --events \
  medicos_db | gzip > backups/mysql/medicos_db_$(date +%F_%H%M%S).sql.gz
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force backups/mysql | Out-Null
docker exec -i mysql mysqldump -u root -p"$env:MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers --events medicos_db | gzip > backups/mysql/medicos_db_$(Get-Date -Format "yyyy-MM-dd_HHmmss").sql.gz
```

Exportar solo estructura:

```bash
docker exec -i mysql mysqldump \
  -u root -p"$MYSQL_ROOT_PASSWORD" \
  --no-data --routines --triggers --events \
  medicos_db > backups/mysql/sql/medicos_db_$(date +%F_%H%M%S)_schema.sql
```

### MongoDB con datos

Linux:

```bash
mkdir -p backups/mongo/v2
docker exec -T mongodb mongodump \
  --archive \
  --gzip \
  --uri="mongodb://admin:password123@localhost:27017/doctoralia?authSource=admin" \
  > backups/mongo/v2/doctoralia_backup_v2_$(date +%F_%H%M%S).gz
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force backups/mongo/v2 | Out-Null
docker exec -T mongodb mongodump --archive --gzip --uri="mongodb://admin:password123@localhost:27017/doctoralia?authSource=admin" > "backups/mongo/v2/doctoralia_backup_v2_$(Get-Date -Format "yyyy-MM-dd_HHmmss").gz"
```

## Restaurar copias recién exportadas

MongoDB:

```bash
docker cp backups/mongo/v2/doctoralia_backup_v2_YYYY-MM-DD_HHMMSS.gz mongodb:/dump.gz
docker exec -it mongodb mongorestore \
  --archive=/dump.gz \
  --gzip \
  --drop \
  --uri="mongodb://admin:password123@localhost:27017/doctoralia?authSource=admin"
```

MySQL:

```bash
gunzip < backups/mysql/medicos_db_YYYY-MM-DD_HHMMSS.sql.gz | \
  docker exec -i mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD" medicos_db
```

> [!WARNING]
> `--drop` en MongoDB reemplaza colecciones existentes. Úsalo solo cuando quieras restaurar el backup como fuente de verdad.
