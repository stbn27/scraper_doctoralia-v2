# Backup de la base de MongoDB

<p align="center">
<img src="../../docs/img/icons/mongodb.webp" alt="Logo de MongoDB" height="100">
</p>

**Esta copia de seguridad contiene toda la información extraida del proceso de scraping realizado en python.
Aunque mongodb no tenga un diagrama entidad relación como sql, se puede representar de la siguiente manera:**
![MySQL](/docs/figures/db_mongo.jpg)



## Restaturación de la copia de seguridad con los datos


> [!NOTE] Primero asegurarse que exista un archivo con dentro del directorio backups/mysql/ con la extension .sql.gz

#### Ejemplo: 

```bash
backups/mongo/v2/doctoralia_2026-07-24_105819.gz
```

**1. Restaturación de las colecciones**

```bash
docker cp backups/mongo/v2/doctoralia_YYYY-MM-DD_HHMMSS.gz mongodb:/dump.gz
docker exec -it mongodb mongorestore \
  --archive=/dump.gz \
  --gzip \
  --drop \
  --uri="mongodb://admin:password123@localhost:27017/doctoralia?authSource=admin"
```

> [!NOTE] Reemplazar las letras en mayusculas por la fecha correspondiente al nombre del archivo de la copia de seguridad.

---
![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![Bash](https://img.shields.io/badge/Bash-black?style=for-the-badge&logo=bash&logoColor=white)
![PowerShell](https://img.shields.io/badge/PowerShell-5391FB?style=for-the-badge&logo=powershell&logoColor=white)

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





















# Mongo - Doctoralia

```bash
docker compose up -d mongodb
docker compose ps
docker compose logs -f mongodb
``` 

## Generación de la copia de seguridad

### v1
> Esta base fue eliminada

```bash
docker compose exec -T mongodb mongodump --archive --gzip > ./backups/mongo/v1/doctoralia_v1_$(date +%F_%H%M%S).gz
```

### v2
> Base del proyecto de node con npm

```bash
docker exec -T mongodb_container mongodump --archive --gzip \
    --uri="mongodb://admin:password123@localhost:27017/?authSource=admin" \
    > ./backups/mongo/v2/doctoralia_v2_$(date +%F_%H%M%S).gz
```

## Restauracion
```bash
# Copiar la copia de seguridad dentro del contenedor
docker cp backups/mongo/v2/doctoralia_backup_v2_2.gz mongodb:/dump.gz

# Carga la copia
docker exec -it mongodb mongorestore \
  --archive=/dump.gz \
  --gzip \
  --uri="mongodb://admin:password123@localhost:27017/doctoralia?authSource=admin" \
  --nsExclude="admin.*" \
  --nsExclude="local.*"
```

## Validación

```bash
docker exec -it mongodb mongosh \
  "mongodb://admin:password123@localhost:27017/?authSource=admin" \
  --eval "db.adminCommand('listDatabases')"
```