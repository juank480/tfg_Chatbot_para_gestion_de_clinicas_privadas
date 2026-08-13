import os
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from ollama import AsyncClient
from database import db

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres un asistente virtual para un doctor en una clínica privada.
Tu objetivo es tomar nota de los síntomas del paciente y ayudar a concertar citas.
REGLA ESTRICTA: No puedes recetar medicinas ni dar diagnósticos bajo ninguna circunstancia.
Limítate a preguntar por sus síntomas, tomar sus datos y sugerir que el doctor revisará la información o ayudarles a agendar una visita.
Sé amable, profesional y empático.

INSTRUCCIÓN CRÍTICA: Cuando consideres que ya tienes todos los síntomas y datos necesarios para el doctor, despídete del paciente y añade AL FINAL de tu respuesta exactamente este texto: [FIN_TOMA_DATOS]."""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start."""
    user_name = update.effective_user.first_name if update.effective_user else "paciente"
    user_id = update.effective_user.id
    
    await db.get_or_create_persona(user_id, user_name)
    
    welcome_message = (
        f"¡Hola {user_name}!\n"
        "Soy el asistente virtual de la clínica. Estoy aquí para tomar nota de tus síntomas "
        "y ayudarte a concertar una cita con el doctor. ¿En qué te puedo ayudar hoy?"
    )
    if update.message:
        await update.message.reply_text(welcome_message)

async def generar_resumen(conversacion_id: int):
    logger.info(f"Generando resumen para la conversación {conversacion_id}...")
    historial = await db.obtener_historial_mensajes(conversacion_id, 30)
    
    if not historial:
        return
        
    messages = [{"role": "system", "content": "Resume los síntomas médicos descritos por el paciente en esta conversación de forma breve y concisa. Actúa como si le estuvieras pasando el reporte a un médico."}]
    for msg in historial:
        role = "user" if msg['emisor_id'] is not None else "assistant"
        messages.append({"role": role, "content": msg['texto']})
    
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model_name = os.getenv("OLLAMA_MODEL", "llama3.1")
    client = AsyncClient(host=ollama_host)
    
    try:
        response = await client.chat(model=model_name, messages=messages)
        resumen = response['message']['content']
        await db.cerrar_conversacion(conversacion_id, resumen)
        logger.info(f"Resumen guardado exitosamente para conversación {conversacion_id}")
    except Exception as e:
        logger.error(f"Error generando resumen: {e}")

async def timeout_conversacion(context: ContextTypes.DEFAULT_TYPE):
    conversacion_id = context.job.data
    logger.info(f"Timeout disparado por inactividad en conversación {conversacion_id}")
    await generar_resumen(conversacion_id)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los mensajes de texto de los pacientes."""
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name if update.effective_user else "paciente"

    # Persistencia
    persona_id = await db.get_or_create_persona(user_id, user_name)
    conversacion_id = await db.get_or_create_conversacion(persona_id)
    
    await db.guardar_mensaje(conversacion_id, persona_id, user_text)

    # Reiniciar temporizador de inactividad (Timeout)
    job_name = f"timeout_{conversacion_id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()
    # 900 segundos = 15 minutos
    context.job_queue.run_once(timeout_conversacion, 900, data=conversacion_id, name=job_name)

    # Construir historial para Llama 3.1
    historial_db = await db.obtener_historial_mensajes(conversacion_id, 20)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    for msg in historial_db:
        role = "user" if msg['emisor_id'] is not None else "assistant"
        messages.append({"role": role, "content": msg['texto']})

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model_name = os.getenv("OLLAMA_MODEL", "llama3.1")
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        client = AsyncClient(host=ollama_host)
        
        response = await client.chat(
            model=model_name,
            messages=messages
        )
        
        bot_reply = response['message']['content']
        
        # Detección de Fin de Triage
        terminado = False
        if "[FIN_TOMA_DATOS]" in bot_reply:
            bot_reply = bot_reply.replace("[FIN_TOMA_DATOS]", "").strip()
            terminado = True
        
        await db.guardar_mensaje(conversacion_id, None, bot_reply)
        
        if bot_reply:
            await update.message.reply_text(bot_reply)
        
        if terminado:
            # Cancelar timeout porque la IA ya cerró la conversación
            current_jobs = context.job_queue.get_jobs_by_name(job_name)
            for job in current_jobs:
                job.schedule_removal()
            # Lanzar resumen en segundo plano
            asyncio.create_task(generar_resumen(conversacion_id))

    except Exception as e:
        logger.error(f"Error al comunicarse con Ollama: {e}")
        await update.message.reply_text(
            "Lo siento, estoy teniendo problemas técnicos en este momento. "
            "Por favor, intenta de nuevo más tarde."
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Excepción ocurrida al procesar una actualización:", exc_info=context.error)

def create_application(token: str) -> Application:
    # Se necesita JobQueue para los timeouts
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    return application

def main() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    token = os.getenv("PACIENTE_BOT_TOKEN", "NOT_FOUND")

    if token == "NOT_FOUND" or not token:
        logger.error("Configura PACIENTE_BOT_TOKEN en tu archivo .env o en el sistema.")
        return

    logger.info("Iniciando el bot de pacientes...")
    application = create_application(token)
    
    # Inicia el bot en modo polling
    application.run_polling()

if __name__ == '__main__':
    main()
