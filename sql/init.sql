-- Esquema de base de datos para Gestión de Clínicas Privadas (Chatbot)

CREATE TABLE IF NOT EXISTS persona (
    id BIGINT PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    telefono VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Doctor hereda de Persona mediante Class Table Inheritance (Clave foránea como PK)
CREATE TABLE IF NOT EXISTS doctor (
    persona_id BIGINT PRIMARY KEY REFERENCES persona(id) ON DELETE CASCADE,
    especialidad VARCHAR(255),
    telefono VARCHAR(50) UNIQUE,
    password_hash VARCHAR(255)
);


CREATE TABLE IF NOT EXISTS conversacion (
    id BIGSERIAL PRIMARY KEY,
    persona_id BIGINT NOT NULL REFERENCES persona(id) ON DELETE CASCADE,
    doctor_id BIGINT REFERENCES doctor(persona_id) ON DELETE SET NULL,
    resumen TEXT,
    estado VARCHAR(20) DEFAULT 'ABIERTA',
    cita_medica_fecha TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mensaje (
    id BIGSERIAL PRIMARY KEY,
    conversacion_id BIGINT NOT NULL REFERENCES conversacion(id) ON DELETE CASCADE,
    emisor_id BIGINT REFERENCES persona(id) ON DELETE SET NULL,
    texto TEXT NOT NULL,
    fecha TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Índices para mejorar el rendimiento de las consultas
CREATE INDEX IF NOT EXISTS idx_conversacion_persona ON conversacion(persona_id);
CREATE INDEX IF NOT EXISTS idx_conversacion_doctor ON conversacion(doctor_id);
CREATE INDEX IF NOT EXISTS idx_mensaje_conversacion ON mensaje(conversacion_id);

-- Vista para obtener fácilmente el resumen de un doctor Doctor.getResumen()
CREATE OR REPLACE VIEW vista_resumenes_doctor AS
SELECT 
    c.doctor_id,
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
    c.doctor_id IS NOT NULL;
