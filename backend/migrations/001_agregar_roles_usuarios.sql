-- ============================================================
-- Migración: Tabla de roles para usuarios
-- Base de datos: medicos_db (MySQL)
-- Ejecutar en orden. Seguro de correr varias veces (idempotente).
-- ============================================================

-- 1. Crear tabla de roles
CREATE TABLE IF NOT EXISTS roles (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  nombre      VARCHAR(50)  NOT NULL UNIQUE COMMENT 'Identificador del rol: USER, ADMIN',
  descripcion VARCHAR(255)          COMMENT 'Descripción del rol',
  created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Roles de usuario del sistema';

-- 2. Insertar roles base (ignora si ya existen)
INSERT IGNORE INTO roles (nombre, descripcion) VALUES
  ('USER',  'Usuario estándar con acceso de lectura y búsqueda'),
  ('ADMIN', 'Administrador con acceso completo al sistema');

-- 3. Agregar columna rol_id a la tabla usuarios
--    (ignorar error si la columna ya existe)
ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS rol_id INT NOT NULL DEFAULT 1
    COMMENT 'FK al rol del usuario. 1=USER por defecto'
    AFTER email;

-- 4. Agregar llave foránea (ejecutar solo si no existe)
-- Si da error porque ya existe la constraint, omitir este paso.
ALTER TABLE usuarios
  ADD CONSTRAINT fk_usuario_rol
    FOREIGN KEY (rol_id)
    REFERENCES roles(id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT;

-- 5. Asignar rol USER a todos los usuarios existentes sin rol
UPDATE usuarios SET rol_id = 1 WHERE rol_id IS NULL OR rol_id = 0;

-- 6. Vista opcional: usuarios con nombre de rol
CREATE OR REPLACE VIEW v_usuarios_con_rol AS
SELECT
  u.id,
  u.email,
  u.nombre,
  u.apellido,
  u.telefono,
  u.avatar_url,
  r.nombre AS rol,
  u.created_at
FROM usuarios u
JOIN roles r ON u.rol_id = r.id;

-- Verificación
SELECT 'Roles creados:' AS info, COUNT(*) AS total FROM roles;
SELECT 'Usuarios con rol:' AS info, COUNT(*) AS total FROM usuarios WHERE rol_id IS NOT NULL;
