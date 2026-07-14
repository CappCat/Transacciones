BEGIN;

CREATE TABLE IF NOT EXISTS vuelos (
    id INT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    asientos_disponibles INT NOT NULL CHECK (asientos_disponibles >= 0)
);

CREATE TABLE IF NOT EXISTS hoteles (
    id INT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    habitaciones_disponibles INT NOT NULL CHECK (habitaciones_disponibles >= 0)
);

CREATE TABLE IF NOT EXISTS transportes (
    id INT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    vehiculos_disponibles INT NOT NULL CHECK (vehiculos_disponibles >= 0)
);

INSERT INTO vuelos (id, nombre, asientos_disponibles)
VALUES
    (1, 'Vuelo 1', 5),
    (2, 'Vuelo 2', 5),
    (3, 'Vuelo 3', 5),
    (4, 'Vuelo 4', 5),
    (5, 'Vuelo 5', 5),
    (6, 'Vuelo 6', 5),
    (7, 'Vuelo 7', 5),
    (8, 'Vuelo 8', 5),
    (9, 'Vuelo 9', 5),
    (10, 'Vuelo 10', 5)
ON CONFLICT (id) DO UPDATE
SET
    nombre = EXCLUDED.nombre,
    asientos_disponibles = EXCLUDED.asientos_disponibles;

INSERT INTO hoteles (id, nombre, habitaciones_disponibles)
VALUES
    (1, 'Hotel 1', 5),
    (2, 'Hotel 2', 5),
    (3, 'Hotel 3', 5),
    (4, 'Hotel 4', 5),
    (5, 'Hotel 5', 5),
    (6, 'Hotel 6', 5),
    (7, 'Hotel 7', 5),
    (8, 'Hotel 8', 5),
    (9, 'Hotel 9', 5),
    (10, 'Hotel 10', 5)
ON CONFLICT (id) DO UPDATE
SET
    nombre = EXCLUDED.nombre,
    habitaciones_disponibles = EXCLUDED.habitaciones_disponibles;

INSERT INTO transportes (id, nombre, vehiculos_disponibles)
VALUES
    (1, 'Transporte 1', 5),
    (2, 'Transporte 2', 5),
    (3, 'Transporte 3', 5),
    (4, 'Transporte 4', 5),
    (5, 'Transporte 5', 5),
    (6, 'Transporte 6', 5),
    (7, 'Transporte 7', 5),
    (8, 'Transporte 8', 5),
    (9, 'Transporte 9', 5),
    (10, 'Transporte 10', 5)
ON CONFLICT (id) DO UPDATE
SET
    nombre = EXCLUDED.nombre,
    vehiculos_disponibles = EXCLUDED.vehiculos_disponibles;

COMMIT;
