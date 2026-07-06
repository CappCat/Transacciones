# transaccion.sql — Ejemplo de transacciones en PostgreSQL

Descripción
- Este script muestra el uso de transacciones en PostgreSQL usando `BEGIN`, `SAVEPOINT`, `ROLLBACK TO SAVEPOINT` y `COMMIT`.
- Incluye un ejemplo de `SET LOCAL statement_timeout` para forzar un tiempo de espera y cómo manejarlo con savepoints.

Contenido principal
- Crea dos tablas de ejemplo: `cuentas` y `movimientos`.
- Inserta una cuenta de prueba (`Ana`) con saldo inicial.
- Inicia una transacción, disminuye el saldo, crea un `SAVEPOINT`, e inserta un registro en `movimientos`.
- Ejecuta `pg_sleep(5)` para provocar un `statement_timeout` de 2 segundos, luego hace `ROLLBACK TO SAVEPOINT`.
- Reintenta la inserción correcta, libera el savepoint y realiza `COMMIT`.

Requisitos
- PostgreSQL (psql). El script usa tipos y funciones de PostgreSQL (`serial`, `pg_sleep`).

Cómo ejecutar
1. Con `psql` (desde el directorio que contiene `transaccion.sql`):

```bash
psql -d <DATABASE> -U <USER> -f transaccion.sql
```

2. Con Docker (ejecuta desde el directorio que contiene el archivo):

```bash
docker run --rm -v "%cd%":/scripts -w /scripts postgres:15 \
  psql -h <HOST> -U <USER> -d <DATABASE> -f transaccion.sql
```

Estructura de tablas (resumen)
- `cuentas`:
  - `id` (serial, PK)
  - `titular` (text)
  - `saldo` (numeric(12,2))
- `movimientos`:
  - `id` (serial, PK)
  - `cuenta_id` (int, FK -> cuentas.id)
  - `detalle` (text)
  - `creado_en` (timestamp, default now())

Comportamiento esperado
- Tras `UPDATE cuentas SET saldo = saldo - 100 WHERE titular = 'Ana'`, el saldo de `Ana` se reduce.
- La segunda operación inserta un movimiento pero llama a `pg_sleep(5)`. Debido a `SET LOCAL statement_timeout = '2s'`, esa instrucción excede el timeout y falla.
- El script hace `ROLLBACK TO SAVEPOINT sp_mov`, deshaciendo los cambios realizados desde el savepoint (si procede), pero preservando lo anterior a él.
- Luego se inserta un movimiento correcto y se hace `COMMIT`, aplicando la disminución de saldo y el movimiento final.
