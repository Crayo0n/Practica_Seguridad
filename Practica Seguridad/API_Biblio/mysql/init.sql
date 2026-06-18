CREATE DATABASE IF NOT EXISTS biblioteca_api
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE biblioteca_api;

DROP TABLE IF EXISTS prestamos;
DROP TABLE IF EXISTS libros;
DROP TABLE IF EXISTS usuarios;

CREATE TABLE libros (
    id_libro INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    anio_publicacion INT NOT NULL,
    paginas INT NOT NULL,
    estado ENUM('disponible', 'prestado') NOT NULL DEFAULT 'disponible'
);

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol ENUM('usuario', 'admin') NOT NULL DEFAULT 'usuario'
);

CREATE TABLE prestamos (
    id_prestamo INT AUTO_INCREMENT PRIMARY KEY,
    id_libro INT NOT NULL,
    usuario_id INT NOT NULL,

    CONSTRAINT fk_prestamos_libro
        FOREIGN KEY (id_libro)
        REFERENCES libros(id_libro)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_prestamos_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- Datos iniciales para libros
INSERT INTO libros (id_libro, nombre, anio_publicacion, paginas, estado) VALUES
(1, 'El Quijote', 1605, 500, 'prestado'),
(2, 'Cien años de soledad', 1967, 450, 'disponible'),
(3, '1984', 1949, 328, 'disponible');

-- Datos iniciales para usuarios
INSERT INTO usuarios (id, nombre, email, password, rol) VALUES
(1, 'Mauricio', 'mauricio@email.com', '$2y$14$UXmxexs.20ECHwup3yFafexN6w0OPKpJoPZ2TDAoY1xwP.FL5aHXC', 'admin'),
(2, 'Lector1', 'lector1@email.com', '$2y$14$UXmxexs.20ECHwup3yFafexN6w0OPKpJoPZ2TDAoY1xwP.FL5aHXC', 'usuario');

-- Datos iniciales para prestamos
INSERT INTO prestamos (id_prestamo, id_libro, usuario_id) VALUES
(1, 1, 2);
