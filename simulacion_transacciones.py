import argparse
import os
import threading
from typing import Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2 import errors


load_dotenv()


DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5432/postgres"


def get_dsn() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DSN)


def get_connection(dsn: Optional[str] = None):
    return psycopg2.connect(dsn or get_dsn())


def create_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS vuelos (
                id INT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                asientos_disponibles INT NOT NULL CHECK (asientos_disponibles >= 0)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS hoteles (
                id INT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                habitaciones_disponibles INT NOT NULL CHECK (habitaciones_disponibles >= 0)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transportes (
                id INT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                vehiculos_disponibles INT NOT NULL CHECK (vehiculos_disponibles >= 0)
            )
            """
        )
    conn.commit()


def seed_data(conn) -> None:
    with conn.cursor() as cur:
        for i in range(1, 11):
            cur.execute(
                """
                INSERT INTO vuelos (id, nombre, asientos_disponibles)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET nombre = EXCLUDED.nombre,
                    asientos_disponibles = EXCLUDED.asientos_disponibles
                """,
                (i, f"Vuelo {i}", 5),
            )
            cur.execute(
                """
                INSERT INTO hoteles (id, nombre, habitaciones_disponibles)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET nombre = EXCLUDED.nombre,
                    habitaciones_disponibles = EXCLUDED.habitaciones_disponibles
                """,
                (i, f"Hotel {i}", 5),
            )
            cur.execute(
                """
                INSERT INTO transportes (id, nombre, vehiculos_disponibles)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET nombre = EXCLUDED.nombre,
                    vehiculos_disponibles = EXCLUDED.vehiculos_disponibles
                """,
                (i, f"Transporte {i}", 5),
            )
    conn.commit()


def reservar_paquete(
    conn,
    flight_id: int,
    hotel_id: int,
    transporte_id: int,
    forzar_fallo_hotel: bool = False,
) -> bool:
    """Reserva vuelo + hotel + transporte usando savepoint y compensacion."""
    try:
        with conn.cursor() as cur:
            print("\n[RESERVA] Iniciando transaccion principal")
            cur.execute("BEGIN")

            cur.execute(
                """
                UPDATE vuelos
                SET asientos_disponibles = asientos_disponibles - 1
                WHERE id = %s AND asientos_disponibles > 0
                RETURNING asientos_disponibles
                """,
                (flight_id,),
            )
            vuelo_row = cur.fetchone()
            if not vuelo_row:
                raise ValueError("No hay asientos disponibles en vuelo")
            print(f"[RESERVA] Vuelo reservado. Asientos restantes: {vuelo_row[0]}")

            cur.execute("SAVEPOINT sp_despues_vuelo")

            if forzar_fallo_hotel:
                cur.execute(
                    "UPDATE hoteles SET habitaciones_disponibles = 0 WHERE id = %s",
                    (hotel_id,),
                )

            cur.execute(
                """
                UPDATE hoteles
                SET habitaciones_disponibles = habitaciones_disponibles - 1
                WHERE id = %s AND habitaciones_disponibles > 0
                RETURNING habitaciones_disponibles
                """,
                (hotel_id,),
            )
            hotel_row = cur.fetchone()
            if not hotel_row:
                print(f"[RESERVA] Error en hotel {hotel_id}: sin disponibilidad")
                print("[RESERVA] Rollback al savepoint sp_despues_vuelo")
                cur.execute("ROLLBACK TO SAVEPOINT sp_despues_vuelo")

                print("[RESERVA] Ejecutando transaccion de compensacion: cancelar vuelo")
                cur.execute(
                    """
                    UPDATE vuelos
                    SET asientos_disponibles = asientos_disponibles + 1
                    WHERE id = %s
                    """,
                    (flight_id,),
                )
                conn.commit()
                print("[RESERVA] Compensacion aplicada. Vuelo cancelado y confirmado.")
                return False

            print(f"[RESERVA] Hotel reservado. Habitaciones restantes: {hotel_row[0]}")

            cur.execute(
                """
                UPDATE transportes
                SET vehiculos_disponibles = vehiculos_disponibles - 1
                WHERE id = %s AND vehiculos_disponibles > 0
                RETURNING vehiculos_disponibles
                """,
                (transporte_id,),
            )
            transporte_row = cur.fetchone()
            if not transporte_row:
                raise ValueError("No hay vehiculos disponibles en transporte")

            print(
                f"[RESERVA] Transporte reservado. Vehiculos restantes: {transporte_row[0]}"
            )
            conn.commit()
            print("[RESERVA] Transaccion principal confirmada")
            return True

    except (errors.InsufficientPrivilege, errors.SerializationFailure, errors.DatabaseError) as exc:
        conn.rollback()
        print(f"[RESERVA] Error transaccional especifico: {exc}")
        return False
    except Exception as exc:
        conn.rollback()
        print(f"[RESERVA] Error general. Rollback total: {exc}")
        return False


def _bloquear_recurso(cur, tabla: str, campo: str, resource_id: int) -> None:
    cur.execute(
        f"UPDATE {tabla} SET {campo} = {campo} WHERE id = %s",
        (resource_id,),
    )


def deadlock_worker_1(dsn: str, barrier: threading.Barrier) -> None:
    conn = get_connection(dsn)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("BEGIN")
            print("[DEADLOCK][T1] Bloqueando vuelo 1")
            _bloquear_recurso(cur, "vuelos", "asientos_disponibles", 1)
            print("[DEADLOCK][T1] Vuelo 1 bloqueado; esperando a T2")
            barrier.wait()
            print("[DEADLOCK][T1] Intentando bloquear hotel 1")
            _bloquear_recurso(cur, "hoteles", "habitaciones_disponibles", 1)
            conn.commit()
            print("[DEADLOCK][T1] Commit exitoso")
    except errors.DeadlockDetected as exc:
        conn.rollback()
        print(f"[DEADLOCK][T1] Deadlock detectado: {exc}")
    except threading.BrokenBarrierError as exc:
        conn.rollback()
        print(f"[DEADLOCK][T1] Sincronizacion interrumpida: {exc}")
    except Exception as exc:
        conn.rollback()
        print(f"[DEADLOCK][T1] Error: {exc}")
    finally:
        conn.close()


def deadlock_worker_2(dsn: str, barrier: threading.Barrier) -> None:
    conn = get_connection(dsn)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("BEGIN")
            print("[DEADLOCK][T2] Bloqueando hotel 1")
            _bloquear_recurso(cur, "hoteles", "habitaciones_disponibles", 1)
            print("[DEADLOCK][T2] Hotel 1 bloqueado; esperando a T1")
            barrier.wait()
            print("[DEADLOCK][T2] Intentando bloquear vuelo 1")
            _bloquear_recurso(cur, "vuelos", "asientos_disponibles", 1)
            conn.commit()
            print("[DEADLOCK][T2] Commit exitoso")
    except errors.DeadlockDetected as exc:
        conn.rollback()
        print(f"[DEADLOCK][T2] Deadlock detectado: {exc}")
    except threading.BrokenBarrierError as exc:
        conn.rollback()
        print(f"[DEADLOCK][T2] Sincronizacion interrumpida: {exc}")
    except Exception as exc:
        conn.rollback()
        print(f"[DEADLOCK][T2] Error: {exc}")
    finally:
        conn.close()


def simular_deadlock(dsn: str) -> None:
    print("\n[DEADLOCK] Iniciando simulacion de deadlock")
    barrier = threading.Barrier(2)
    t1 = threading.Thread(target=deadlock_worker_1, args=(dsn, barrier))
    t2 = threading.Thread(target=deadlock_worker_2, args=(dsn, barrier))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print("[DEADLOCK] Simulacion finalizada")


def simular_timeout(dsn: str) -> None:
    print("\n[TIMEOUT] Iniciando simulacion de timeout")
    timeout_conn = get_connection(dsn)
    try:
        with timeout_conn.cursor() as cur:
            cur.execute("BEGIN")
            cur.execute("SET LOCAL statement_timeout = '1500ms'")
            cur.execute("SELECT pg_sleep(3)")
            timeout_conn.commit()
            print("[TIMEOUT] No se produjo timeout (inesperado)")
    except errors.QueryCanceled as exc:
        timeout_conn.rollback()
        print(f"[TIMEOUT] Timeout detectado y rollback aplicado: {exc}")
    except Exception as exc:
        timeout_conn.rollback()
        print(f"[TIMEOUT] Error inesperado durante la simulacion: {exc}")
    finally:
        timeout_conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulacion de transacciones: reserva, deadlock y timeout"
    )
    parser.add_argument(
        "--forzar-fallo-hotel",
        action="store_true",
        help="Fuerza falta de cupo en hotel para probar savepoint y compensacion",
    )
    args = parser.parse_args()

    dsn = get_dsn()
    print(f"Conectando a la base de datos con DSN: {dsn}")
    conn = get_connection(dsn)

    try:
        create_tables(conn)
        seed_data(conn)

        reservar_paquete(
            conn,
            flight_id=1,
            hotel_id=1,
            transporte_id=1,
            forzar_fallo_hotel=args.forzar_fallo_hotel,
        )

        simular_deadlock(dsn)
        simular_timeout(dsn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
