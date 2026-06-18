CREATE DATABASE IF NOT EXISTS escuela_api
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE escuela_api;

DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS alumnos;
DROP TABLE IF EXISTS maestros;

CREATE TABLE alumnos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    matricula VARCHAR(20) NOT NULL UNIQUE,
    carrera VARCHAR(20) NOT NULL,
    semestre TINYINT UNSIGNED NOT NULL
);

CREATE TABLE maestros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    numero_empleado VARCHAR(20) NOT NULL UNIQUE,
    materia VARCHAR(50) NOT NULL
);

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol ENUM('alumno', 'maestro', 'admin') NOT NULL,
    alumno_id INT NULL,
    maestro_id INT NULL,

    CONSTRAINT fk_usuarios_alumno
        FOREIGN KEY (alumno_id)
        REFERENCES alumnos(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT fk_usuarios_maestro
        FOREIGN KEY (maestro_id)
        REFERENCES maestros(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

INSERT INTO alumnos (id, nombre, matricula, carrera, semestre) VALUES
(1, 'Isabel', 'A001', 'ISC', 3),
(2, 'Samantha', 'A002', 'TIID', 5),
(3, 'Jesús', 'A003', 'IM', 2);

INSERT INTO maestros (id, nombre, numero_empleado, materia) VALUES
(1, 'Luis Custodio', 'M001', 'ISC'),
(2, 'Alejandra Briones', 'M002', 'ITIID'),
(3, 'Fred Urbina', 'M003', 'IM');

INSERT INTO usuarios (
    id,
    nombre,
    email,
    password,
    rol,
    alumno_id,
    maestro_id
) VALUES
(
    1,
    'Isabel',
    'isabel@email.com',
    '$2y$14$UXmxexs.20ECHwup3yFafexN6w0OPKpJoPZ2TDAoY1xwP.FL5aHXC',
    'alumno',
    1,
    NULL
),
(
    2,
    'Samantha',
    'samantha@email.com',
    '$2y$14$UXmxexs.20ECHwup3yFafexN6w0OPKpJoPZ2TDAoY1xwP.FL5aHXC',
    'alumno',
    2,
    NULL
),
(
    3,
    'Luis Custodio',
    'luis@email.com',
    '$2y$14$efE0iN558hzRkztVbBdIw.Sm8F8P/Luo8dT.t9pVSIX/usLmAkCgO',
    'maestro',
    NULL,
    1
),
(
    4,
    'Administrador',
    'admin@escuela.com',
    '$2y$14$efE0iN558hzRkztVbBdIw.Sm8F8P/Luo8dT.t9pVSIX/usLmAkCgO',
    'admin',
    NULL,
    NULL
);