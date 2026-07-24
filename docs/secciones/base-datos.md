# Carga y respaldo de bases de datos

Las copias incluidas fueron preparadas para restaurarse dentro de contenedores Docker. Para cargar el proyecto por primera vez, levanta primero las bases, copia la copia de seguridad al contenedor y después arranca backend/frontend.

## Backups incluidos

| Motor | Archivo | Contenido |
|---|---|---|
| MongoDB | `backups/mongo/v2/doctoralia_backup_v2_2.gz` | Backup comprimido de la base Doctoralia. |
| MySQL | `backups/mysql/medicos_db_2026-07-02_235402.sql.gz` | Backup completo comprimido con datos. |
| MySQL | `backups/mysql/sql/medicos_db_2026-07-02_235445_schema.sql` | Solo estructura, sin datos. |

Para una restauración funcional del sistema se recomienda usar MongoDB v2 y el backup MySQL completo `.sql.gz`.

> ![NOTA] En caso de que el directorio `backups/` no exista, se puede descargar desde el siguiente enlace:
> 
> https://drive.google.com/drive/folders/1lo7FJg6OHFf7AMqMWW5HknIXzlC03RdD?usp=sharing
>
> Contiene las copias de MongoDB y MySQL. Asegúrate de extraer el archivo ZIP antes de continuar.

## Restaurar MongoDB ⬇️

<p align="center">
<img src="../../docs/img/icons/mongodb.webp" alt="Descripción de la imagen" height="100">
</p>

**Desarrollo:**

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

**Producción:**

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

**Validación:**

```bash
docker exec -it mongodb mongosh \
  "mongodb://admin:password123@localhost:27017/?authSource=admin" \
  --eval "db.getSiblingDB('doctoralia').getCollectionNames()"
```

## Restaurar MySQL ⬇️

<p align="center">
<img src="../../docs/img/icons/mysql.jpeg" alt="Descripción de la imagen" height="100">
</p>

**Ambientes con Linux:**

![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)

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

**Ambientes con Windows PowerShell:**

![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)

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

### Usuarios disponibles dentro del backup del MySQL
|correo|contraseña|Rol|
|-|-|-|
|jose@a.com|123|ADMIN|
|jose@c.com|123|ADMIN|
|user@correo.com|123|USER|

## Exportar nuevas copias ⬆️

La nomenclatura recomendada mantiene el patrón actual:

```text
backups/mysql/medicos_db_YYYY-MM-DD_HHMMSS.sql.gz
backups/mysql/sql/medicos_db_YYYY-MM-DD_HHMMSS_schema.sql
backups/mongo/v2/doctoralia_YYYY-MM-DD_HHMMSS.gz
```

### MySQL con datos

![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)

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

![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white)

Linux:

```bash
mkdir -p backups/mongo/v2
docker compose exec -T mongodb mongodump \
  --archive \
  --gzip \
  --uri="mongodb://admin:password123@localhost:27017/doctoralia?authSource=admin" \
  > backups/mongo/v2/doctoralia_$(date +%F_%H%M%S).gz
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force backups/mongo/v2 | Out-Null
docker exec -T mongodb mongodump --archive --gzip --uri="mongodb://admin:password123@localhost:27017/doctoralia?authSource=admin" > "backups/mongo/v2/doctoralia_$(Get-Date -Format "yyyy-MM-dd_HHmmss").gz"
```

## Restaurar copias recién exportadas

MongoDB:

```bash
docker cp backups/mongo/v2/doctoralia_YYYY-MM-DD_HHMMSS.gz mongodb:/dump.gz
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


## Código abierto y contribuciones ✏️

Este proyecto es de código abierto. Puedes revisarlo, adaptarlo y proponer mejoras mediante issues o pull requests si encuentras errores, mejoras de documentación, nuevas integraciones, optimizaciones o ajustes de despliegue.

Antes de contribuir, revisa la estructura del proyecto y procura que los cambios sean claros, reproducibles y acompañados de una explicación breve del problema que resuelven.

## Autor

> Esteban Nuñez José Julian 🇲🇽

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/estebanjose27)
[![TikTok](https://img.shields.io/badge/TikTok-000000?style=for-the-badge&logo=tiktok&logoColor=white)](http://tiktok.com/@stbn27)
[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/@stbn27)
[![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white)](https://github.com/stbn27/stbn27)

Me ayudarías dejando una ⭐ si te gustó el proyecto.