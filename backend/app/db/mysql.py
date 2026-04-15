import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from typing import Optional
import os

_pool: Optional[MySQLConnectionPool] = None

def get_mysql_pool() -> MySQLConnectionPool:
    global _pool
    if _pool is None:
        _pool = MySQLConnectionPool(
            pool_name="medicos_pool",
            pool_size=5,
            host=os.getenv("MYSQL_HOST", "mysql"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_ROOT_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE", "medicos_db")
        )
    return _pool

def get_mysql_conn():
    return get_mysql_pool().get_connection()