import asyncio
import bcrypt
import os
from database import db

async def create_test_doctor():
    await db.connect()
    
    telefono = "600123456"
    password = "password123"
    
    # 1. Crear persona si no existe (usamos un ID falso de Telegram para el doctor)
    telegram_id = 9999999
    persona_id = await db.get_or_create_persona(telegram_id, "Doctor Prueba", telefono)
    
    # 2. Encriptar contraseña
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    # 3. Insertar doctor (o actualizar si ya existe)
    try:
        async with db.pool.acquire() as conn:
            query = """
                INSERT INTO doctor (persona_id, especialidad, telefono, password_hash)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (persona_id) DO UPDATE 
                SET password_hash = EXCLUDED.password_hash,
                    telefono = EXCLUDED.telefono;
            """
            await conn.execute(query, persona_id, "Medicina General", telefono, hashed)
            print(f"Doctor de prueba creado exitosamente.")
            print(f"Teléfono: {telefono}")
            print(f"Contraseña: {password}")
    except Exception as e:
        print(f"Error al crear doctor: {e}")
        
    await db.close()

if __name__ == "__main__":
    asyncio.run(create_test_doctor())
