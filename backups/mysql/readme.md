# Backup de la base de datos MySQL 

<p align="center">
<img src="../../docs/img/icons/mysql.jpeg" alt="Logo de MySQL" height="100">
</p>

**Esta base de datos contiene información sobre los usuarios del sistema.**
El diagrama entidad relación se muestra a continuación:
![MySQL](/docs/figures/db_mysql.webp)

### Usuarios disponibles dentro del backup del MySQL
|correo|contraseña|Rol|
|-|-|-|
|jose@a.com|123|ADMIN|
|jose@c.com|123|ADMIN|
|user@correo.com|123|USER|

## Restaturación de la copia de seguridad con los datos


> [!NOTE] Primero asegurarse que exista un archivo con dentro del directorio backups/mysql/ con la extension .sql.gz

#### Ejemplo: 

```bash
backups/mysql/medicos_db_2026-07-24_103857.sql.gz
```

### Si se restaurara el backup con los datos, el sistema se quedaria con los usuarios y contraseñas del backup.

**1. Limpiar la base de datos.**

> [!WARNING]
> `--drop` en MongoDB reemplaza colecciones existentes. Úsalo solo cuando quieras restaurar el backup como fuente de verdad.

```bash
docker exec -i mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "DROP DATABASE IF EXISTS medicos_db;"
docker exec -i mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE medicos_db;"
```

**2. Restaurar la copia de seguridad con los datos.**

```bash
gunzip < backups/mysql/medicos_db_YYYY-MM-DD_HHMMSS.sql.gz | docker exec -i mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD" medicos_db
```

> [!NOTE] La contraseña del backup de MySQL es: `esteb@n_27J` en caso de que el contenedor solicite la contraseña, se recomienda colocarla como variable de entorno en los archivos .env y .env.prod con el nombre `MYSQL_ROOT_PASSWORD`.


## Restaturación de la copia de seguridad sin los datos

> [!NOTE] Considere que este backup no contiene los datos del sistema, es decir, no tiene usuarios, ni roles, etc. Por lo que primero debera crear estos datos manualmente.

> [!NOTE] Primero asegurarse que exista un archivo con dentro del directorio backups/mysql/sql/ con la extension .sql

#### Ejemplo:

```bash
backups/mysql/sql/medicos_db_2026-07-24_104402_schema.sql
```

**1. Limpiar la base de datos.**

```bash
docker exec -i mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "DROP DATABASE IF EXISTS medicos_db;"
docker exec -i mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE medicos_db;"
```

**2. Restaurar la copia de seguridad con los datos.**

```bash
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "USE medicos_db; source backups/mysql/sql/medicos_db_2026-07-24_104402_schema.sql;"
```
---

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