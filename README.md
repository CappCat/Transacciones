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
Crea las tablas `vuelos`, `hoteles` y `transportes` si no existen. Cada una controla disponibilidad con una restriccion `CHECK` para evitar valores negativos.

### seed_data(conn)
Inserta o actualiza 10 filas por tabla con disponibilidad inicial de 5. Esto permite volver a ejecutar la practica sin limpiar manualmente la base.

### reservar_paquete(conn, flight_id, hotel_id, transporte_id, forzar_fallo_hotel=False)
Ejecuta la transaccion principal de reserva turistica:

- `BEGIN` abre la transaccion.
- Se descuenta un asiento del vuelo.
- `SAVEPOINT sp_despues_vuelo` deja un punto de recuperacion si el hotel falla.
- Se intenta reservar el hotel.
- Si el hotel no tiene cupo, el flujo hace `ROLLBACK TO SAVEPOINT`, cancela el vuelo con una compensacion y confirma ese cambio con `COMMIT`.
- Si el hotel si tiene cupo, se reserva el transporte y se hace `COMMIT` de toda la compra.

Este flujo refleja una reserva real: primero se confirma el recurso mas escaso y luego se compensa si el siguiente paso no puede completarse.

### simular_deadlock(dsn)
Lanza dos hilos con dos transacciones y usa `threading.Barrier` para que ambas lleguen al segundo bloqueo al mismo tiempo:

- T1 bloquea primero `vuelos` y despues intenta `hoteles`.
- T2 bloquea primero `hoteles` y despues intenta `vuelos`.

Como cada hilo toma un recurso distinto primero y luego intenta el recurso del otro hilo, se forma una espera circular. PostgreSQL detecta el ciclo y aborta una de las transacciones con `DeadlockDetected`.

### simular_timeout(dsn)
Abre una conexion aislada, configura `statement_timeout` y ejecuta `pg_sleep` para forzar la cancelacion de la sentencia. La simulacion captura `QueryCanceled` y hace `ROLLBACK` para dejar la conexion limpia.

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
  - Rollback a savepoint sp_despues_vuelo
  - Compensacion aplicada: vuelo cancelado

- Deadlock:
  - T1 bloquea vuelos y T2 bloquea hoteles
  - Ambos intentan tomar el recurso restante
  - PostgreSQL detecta el deadlock y aborta una transaccion

- Timeout:
  - statement_timeout interrumpe la consulta lenta
  - Se ejecuta rollback de la conexion de timeout

### Capturas de pantalla

Deja aqui tus capturas reales de la ejecucion:

- Captura 1: reserva exitosa

  [Espacio para pegar captura]

- Captura 2: reserva con savepoint y compensacion

  [Espacio para pegar captura]

- Captura 3: deadlock con hilos

  [Espacio para pegar captura]

- Captura 4: timeout de transaccion

  [Espacio para pegar captura]

### Logs reales de ejecucion

Pega aqui la salida real de consola para cada caso:

- Log reserva exitosa

  ![Log](imagenes/image1.png)

- Log deadlock

  ![Log](imagenes/image3.png)

- Log timeout

  ![Log](imagenes/image2.png)

## 9. Preguntas de reflexion

1. ¿Por que es importante usar savepoints en transacciones largas? ¿Que problema resuelven?
Los savepoints permiten deshacer solo la parte defectuosa de una transaccion larga sin perder el trabajo anterior. Resuelven el problema de tener que hacer rollback total cuando solo falla un paso intermedio.

2. En el escenario de reserva, ¿que pasaria si no usariamos savepoints y el hotel no tuviera cupo? ¿Como afectaria a la consistencia de los datos?
Sin savepoints, el fallo del hotel obligaria a revertir toda la transaccion, incluido el vuelo ya reservado. Eso dejaria inconsistente la logica del negocio porque se perderia el progreso valido del flujo y se tendria que repetir todo desde cero.

3. ¿Como se produce un deadlock en una base de datos? Explica el ejemplo que implementaste y como lo resolviste.
Un deadlock aparece cuando dos transacciones se quedan esperando recursos que la otra ya bloqueo. En este proyecto, un hilo bloquea primero `vuelos` y luego intenta `hoteles`, mientras el otro hace lo contrario. Para hacerlo reproducible, ambos hilos se sincronizan con un `Barrier`. La mitigacion del ejemplo consiste en observar el bloqueo circular y dejar que PostgreSQL aborta una de las transacciones; en sistemas reales, ademas se recomienda ordenar los accesos a los recursos siempre en el mismo orden.

4. ¿Que estrategias de mitigacion existen para evitar deadlocks en sistemas concurrentes?
Las principales estrategias son mantener un orden consistente de acceso a tablas o filas, hacer transacciones mas cortas, reducir el tiempo de bloqueo, crear los indices adecuados para que las consultas tarden menos y agregar reintentos controlados cuando la base devuelva un deadlock.

5. ¿Que sucede cuando una transaccion alcanza el timeout? ¿Como afecta al usuario final y que mecanismos se pueden implementar para manejar esta situacion?
Cuando la transaccion supera el tiempo limite, PostgreSQL cancela la consulta y revierte el trabajo pendiente con rollback. Para el usuario final esto se ve como una operacion fallida o demorada. Para manejarlo mejor se pueden mostrar mensajes claros, reintentar solo cuando tenga sentido, usar tiempos maximos razonables, mover procesos largos a segundo plano y registrar el error para diagnostico.

## 10. Conclusion

La practica evidencia que el control transaccional va mas alla de COMMIT y ROLLBACK. El uso de savepoints permite recuperacion fina, las compensaciones preservan la logica de negocio, y el manejo de deadlocks/timeouts fortalece la robustez del sistema en escenarios concurrentes reales.
