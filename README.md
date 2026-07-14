# Simulacion de transacciones en un sistema de reservas

Este proyecto implementa una simulacion de transacciones en PostgreSQL usando Python con psycopg2. El objetivo es demostrar:

- Transacciones atomicas con savepoints.
- Transacciones de compensacion.
- Deadlocks en transacciones concurrentes.
- Timeouts por espera prolongada.

## 1. Introduccion teorica

### Transacciones anidadas y savepoints
En PostgreSQL no existen transacciones anidadas reales dentro de una misma transaccion, pero se puede lograr un comportamiento similar usando savepoints.

- BEGIN inicia una transaccion.
- SAVEPOINT crea un punto intermedio de recuperacion.
- ROLLBACK TO SAVEPOINT revierte solo desde ese punto hacia adelante.
- COMMIT confirma los cambios definitivos.

Esto permite controlar errores parciales sin perder todo el trabajo de la transaccion.

### Deadlocks
Un deadlock ocurre cuando dos (o mas) transacciones se bloquean mutuamente.

Ejemplo tipico:
- T1 bloquea recurso A y luego espera recurso B.
- T2 bloquea recurso B y luego espera recurso A.

Ninguna puede avanzar, por lo que PostgreSQL detecta el ciclo y aborta una de ellas.

### Timeouts
Un timeout limita cuanto tiempo puede esperar o ejecutarse una sentencia.

En PostgreSQL, statement_timeout cancela sentencias lentas. Esto evita sesiones colgadas, pero obliga a manejar errores y decidir si se revierte parcial o totalmente la transaccion.

## 2. Escenario de simulacion

El sistema simula una reserva turistica con tres pasos atomicos:

1. Compra de pasaje de avion (tabla vuelos).
2. Reserva de hotel (tabla hoteles).
3. Reserva de transporte (tabla transportes).

Regla del negocio:
Si el hotel no tiene cupo, el sistema vuelve a un savepoint y ejecuta una transaccion de compensacion para cancelar el vuelo (liberar asiento).

## 3. Estructura del proyecto

- simulacion_transacciones.py
- transaccion.sql
- requirements.txt
- .gitignore
- README.md

## 4. Requisitos previos

- Python 3.x
- PostgreSQL activo

- Se recomienda crear un enviroment con:

python -m venv .venv

- Dependencia de Python:

pip install -r requirements.txt


## 5. Configuracion de conexion

El script usa la variable DATABASE_URL y la carga automaticamente desde un archivo .env (si existe) usando python-dotenv.

Ejemplo de formato:
postgresql://usuario:password@localhost:5432/mi_basedatos

Si no se define, se usa por defecto:
postgresql://postgres:postgres@localhost:5432/postgres

Ejemplo de archivo .env en la raiz del proyecto:

DATABASE_URL=postgresql://usuario:password@localhost:5432/mi_basedatos

## 6. Ejecucion

1. Inicializar esquema y datos base con SQL:

psql -d postgres -U postgres -f transaccion.sql

2. Ejecutar la simulacion completa:

python simulacion_transacciones.py

3. Opcional: forzar fallo de hotel para ver compensacion:

python simulacion_transacciones.py --forzar-fallo-hotel

## 7. Explicacion del codigo

### create_tables(conn)
Crea las tablas vuelos, hoteles y transportes con disponibilidad.

### seed_data(conn)
Inserta 10 registros por tabla. Si ya existen, actualiza disponibilidad a un valor inicial.

### reservar_paquete(conn, flight_id, hotel_id, transporte_id, forzar_fallo_hotel=False)
Ejecuta la transaccion principal:

- Paso 1: descuenta 1 asiento en vuelos.
- Crea savepoint despues del vuelo.
- Paso 2: intenta descontar 1 habitacion en hoteles.
- Si falla hotel:
  - rollback al savepoint.
  - compensacion: suma 1 al vuelo para cancelar la compra.
  - rollback total y retorno controlado.
- Paso 3: descuenta 1 vehiculo en transportes.
- commit final si todo sale bien.

### simular_deadlock(dsn)
Lanza dos hilos con dos transacciones:

- T1 actualiza primero vuelos y luego hoteles.
- T2 actualiza primero hoteles y luego vuelos.

Con bloqueos en orden inverso se provoca deadlock; PostgreSQL aborta una transaccion.

### simular_timeout(conn)
Configura statement_timeout y ejecuta pg_sleep para causar cancelacion por timeout.

## 8. Resultados obtenidos

Al ejecutar el script se observan logs como:

- Reserva exitosa:
  - Vuelo reservado
  - Hotel reservado
  - Transporte reservado
  - Transaccion principal confirmada

- Reserva con compensacion:
  - Vuelo reservado
  - Error en hotel: sin disponibilidad
  - Rollback a savepoint
  - Compensacion aplicada: vuelo cancelado

- Deadlock:
  - Deadlock detectado en una de las transacciones

- Timeout:
  - Timeout detectado y rollback de la transaccion

Nota sobre capturas:
Agrega capturas de consola o del log de ejecucion para cada simulacion en esta seccion.

## 9. Preguntas de reflexion (5) y respuestas

1. ¿Que ventaja ofrece un savepoint frente a hacer rollback total?
Permite recuperar parcialmente la transaccion, manteniendo operaciones validas anteriores y evitando rehacer todo el flujo.

2. ¿Por que se usa una transaccion de compensacion si falla el hotel?
Porque la compra del vuelo ya se habia ejecutado. La compensacion restaura consistencia de negocio cancelando ese paso previo.

3. ¿Como se genera el deadlock en este proyecto?
Dos transacciones bloquean recursos compartidos en orden inverso, creando espera circular.

4. ¿Que diferencia hay entre deadlock y timeout?
El deadlock es una interdependencia circular de bloqueos entre transacciones; el timeout es un limite de tiempo excedido por espera o ejecucion.

5. ¿Que buenas practicas ayudan a reducir estos problemas?
Mantener transacciones cortas, ordenar accesos a recursos de forma consistente, usar niveles de aislamiento adecuados y manejar excepciones con rollback y reintentos.

## 10. Conclusion

La practica evidencia que el control transaccional va mas alla de COMMIT y ROLLBACK. El uso de savepoints permite recuperacion fina, las compensaciones preservan la logica de negocio, y el manejo de deadlocks/timeouts fortalece la robustez del sistema en escenarios concurrentes reales.
