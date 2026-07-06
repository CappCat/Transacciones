-- Tablas de ejemplo
CREATE TABLE IF NOT EXISTS cuentas (
    id serial PRIMARY KEY,
    titular text NOT NULL,
    saldo numeric(12,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS movimientos (
    id serial PRIMARY KEY,
    cuenta_id int NOT NULL REFERENCES cuentas(id),
    detalle text NOT NULL,
    creado_en timestamp NOT NULL DEFAULT now()
);

INSERT INTO cuentas (titular, saldo)
VALUES ('Ana', 1000.00)
ON CONFLICT DO NOTHING;

select * from cuentas;
select * from movimientos;

BEGIN;

-- Timeout 
SET LOCAL statement_timeout = '2s';

-- Paso 1
UPDATE cuentas
SET saldo = saldo - 100
WHERE titular = 'Ana';

SAVEPOINT sp_mov;

-- Paso 2
INSERT INTO movimientos (cuenta_id, detalle)
SELECT id, 'Movimiento lento'
FROM cuentas
WHERE titular = 'Ana';

SELECT pg_sleep(5);   -- dispara statement_timeout

-- Rollback:
ROLLBACK TO SAVEPOINT sp_mov;

-- Reintento correcto después del rollback al savepoint:
INSERT INTO movimientos (cuenta_id, detalle)
SELECT id, 'Movimiento correcto'
FROM cuentas
WHERE titular = 'Ana';

RELEASE SAVEPOINT sp_mov;

COMMIT;