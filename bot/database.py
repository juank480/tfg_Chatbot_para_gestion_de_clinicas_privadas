import os
import asyncpg
import logging

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

    async def get_resumenes_doctor(self, doctor_id: int):
        """
        Obtiene los resúmenes de las conversaciones de un doctor específico.
        :param doctor_id: ID del doctor (persona_id)
        :return: Lista de registros con la información del resumen
        """
        if not self.pool:
            await self.connect()

        try:
            async with self.pool.acquire() as connection:
                query = """
                    SELECT 
                        paciente_nombre, 
                        paciente_telefono, 
                        resumen, 
                        created_at
                    FROM 
                        vista_resumenes_doctor
                    WHERE 
                        doctor_id = $1
                    ORDER BY 
                        created_at DESC;
                """
                records = await connection.fetch(query, doctor_id)
                return records
        except Exception as e:
            logger.error(f"Error al obtener resúmenes del doctor {doctor_id}: {e}")
            return None

# Instancia global de la base de datos
db = Database()
