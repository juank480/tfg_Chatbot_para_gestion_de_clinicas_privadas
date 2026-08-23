import os
import asyncpg
import logging
import bcrypt

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                # Use environment variables, fallback to localhost if not found
                # (e.g. if running locally outside docker, use POSTGRES_HOST=localhost)
                host = os.getenv("POSTGRES_HOST", "localhost")
                port = os.getenv("POSTGRES_PORT", "5432")
                user = os.getenv("POSTGRES_USER", "clinica_user")
                password = os.getenv("POSTGRES_PASSWORD", "clinica_password")
                database = os.getenv("POSTGRES_DB", "clinica_db")

                self.pool = await asyncpg.create_pool(
                    user=user,
                    password=password,
                    database=database,
                    host=host,
                    port=port
                )
                logger.info("Conexión a la base de datos PostgreSQL establecida.")
            except Exception as e:
                logger.error(f"Error al conectar con la base de datos: {e}")

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("Conexión a la base de datos cerrada.")

    async def get_or_create_persona(self, telegram_id: int, nombre: str, telefono: str = None) -> int:
        if not self.pool: await self.connect()
        try:
            async with self.pool.acquire() as conn:
                query = """
                    INSERT INTO persona (id, nombre, telefono)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (id) DO UPDATE 
                    SET nombre = EXCLUDED.nombre,
                        telefono = COALESCE(EXCLUDED.telefono, persona.telefono)
                    RETURNING id;
                """
                record = await conn.fetchrow(query, telegram_id, nombre, telefono)
                return record['id']
        except Exception as e:
            logger.error(f"Error en get_or_create_persona: {e}")
            return None

    async def get_or_create_conversacion(self, persona_id: int) -> int:
        if not self.pool: await self.connect()
        try:
            async with self.pool.acquire() as conn:
                query_find = "SELECT id FROM conversacion WHERE persona_id = $1 AND estado = 'ABIERTA' ORDER BY created_at DESC LIMIT 1"
                record = await conn.fetchrow(query_find, persona_id)
                if record:
                    return record['id']
                
                query_create = """
                    INSERT INTO conversacion (persona_id, doctor_id, estado)
                    VALUES ($1, NULL, 'ABIERTA')
                    RETURNING id;
                """
                record = await conn.fetchrow(query_create, persona_id)
                return record['id']
        except Exception as e:
            logger.error(f"Error en get_or_create_conversacion: {e}")
            return None

    async def guardar_mensaje(self, conversacion_id: int, emisor_id: int | None, texto: str):
        if not self.pool: await self.connect()
        try:
            async with self.pool.acquire() as conn:
                query = """
                    INSERT INTO mensaje (conversacion_id, emisor_id, texto)
                    VALUES ($1, $2, $3);
                """
                await conn.execute(query, conversacion_id, emisor_id, texto)
        except Exception as e:
            logger.error(f"Error en guardar_mensaje: {e}")

    async def obtener_historial_mensajes(self, conversacion_id: int, limite: int = 20) -> list:
        if not self.pool: await self.connect()
        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT emisor_id, texto 
                    FROM mensaje 
                    WHERE conversacion_id = $1 
                    ORDER BY fecha ASC 
                    LIMIT $2;
                """
                records = await conn.fetch(query, conversacion_id, limite)
                return records
        except Exception as e:
            logger.error(f"Error en obtener_historial_mensajes: {e}")
            return []

    async def cerrar_conversacion(self, conversacion_id: int, resumen: str, estado: str = 'CERRADA'):
        if not self.pool: await self.connect()
        try:
            async with self.pool.acquire() as conn:
                query = """
                    UPDATE conversacion 
                    SET resumen = $1, estado = $2, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $3;
                """
                await conn.execute(query, resumen, estado, conversacion_id)
        except Exception as e:
            logger.error(f"Error en cerrar_conversacion: {e}")

    async def cancelar_conversaciones_abiertas(self, persona_id: int):
        """Cancela cualquier conversación que estuviera a medias para este usuario."""
        if not self.pool: await self.connect()
        try:
            async with self.pool.acquire() as conn:
                query = """
                    UPDATE conversacion 
                    SET estado = 'CANCELADA', updated_at = CURRENT_TIMESTAMP
                    WHERE persona_id = $1 AND estado = 'ABIERTA';
                """
                await conn.execute(query, persona_id)
        except Exception as e:
            logger.error(f"Error al cancelar conversaciones abiertas: {e}")

    async def get_resumenes_doctor(self, doctor_id: int):
        """
        Obtiene los resúmenes de las conversaciones cerradas.
        Ignoramos el doctor_id por ahora para que el doctor vea todos los triajes pendientes.
        """
        if not self.pool: await self.connect()
        try:
            async with self.pool.acquire() as conn:
                # Usamos una query directa en vez de la vista para poder ver a pacientes sin doctor_id asignado
                query = """
                    SELECT 
                        c.id AS conversacion_id,
                        p.id AS paciente_telegram_id,
                        p.nombre AS paciente_nombre, 
                        COALESCE(p.telefono, 'No facilitado') AS paciente_telefono, 
                        c.resumen, 
                        c.estado,
                        c.cita_medica_fecha,
                        c.created_at
                    FROM 
                        conversacion c
                    JOIN 
                        persona p ON c.persona_id = p.id
                    WHERE 
                        c.estado IN ('CERRADA', 'CANCELADA') 
                        AND c.resumen IS NOT NULL
                        AND c.updated_at >= CURRENT_DATE
                    ORDER BY 
                        c.updated_at DESC;
                """
                records = await conn.fetch(query)
                return records
        except Exception as e:
            logger.error(f"Error al obtener resúmenes: {e}")
            return None

    async def autenticar_doctor(self, telefono: str, password: str) -> int | None:
        if not self.pool: await self.connect()
        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT persona_id, password_hash
                    FROM doctor
                    WHERE telefono = $1;
                """
                record = await conn.fetchrow(query, telefono)
                
                if record and record['password_hash']:
                    # Verificar contraseña
                    if bcrypt.checkpw(password.encode('utf-8'), record['password_hash'].encode('utf-8')):
                        return record['persona_id']
                return None
        except Exception as e:
            logger.error(f"Error en autenticar_doctor: {e}")
            return None

# Instancia global de la base de datos
db = Database()
