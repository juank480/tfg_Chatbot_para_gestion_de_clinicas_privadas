import os
import logging
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

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Diccionario para almacenar el historial de conversación en memoria (temporal)
user_histories = {}

SYSTEM_PROMPT = """Eres un asistente virtual para un doctor en una clínica privada.
Tu objetivo es tomar nota de los síntomas del paciente y ayudar a concertar citas.
REGLA ESTRICTA: No puedes recetar medicinas ni dar diagnósticos bajo ninguna circunstancia.
Limítate a preguntar por sus síntomas, tomar sus datos y sugerir que el doctor revisará la información o ayudarles a agendar una visita.
Sé amable, profesional y empático."""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start."""
    user_name = update.effective_user.first_name if update.effective_user else "paciente"
    user_id = update.effective_user.id
    
    # Reiniciar historial para el usuario
    user_histories[user_id] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    welcome_message = (
        f"¡Hola {user_name}!\n"
        "Soy el asistente virtual de la clínica. Estoy aquí para tomar nota de tus síntomas "
        "y ayudarte a concertar una cita con el doctor. ¿En qué te puedo ayudar hoy?"
    )
    if update.message:
        await update.message.reply_text(welcome_message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los mensajes de texto de los pacientes."""
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    user_id = update.effective_user.id

    # Si no tiene historial (no usó /start), lo inicializamos
    if user_id not in user_histories:
        user_histories[user_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
    user_histories[user_id].append({"role": "user", "content": user_text})

    # Mantener el historial acotado para no exceder contexto (ej. últimas 10 interacciones + system)
    if len(user_histories[user_id]) > 21:
        # Mantenemos el prompt del sistema y las últimas 20 interacciones
        user_histories[user_id] = [user_histories[user_id][0]] + user_histories[user_id][-20:]

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model_name = os.getenv("OLLAMA_MODEL", "llama3.1")
    
    # Enviar estado de "Escribiendo..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        client = AsyncClient(host=ollama_host)
        
        # Llamar a Ollama de forma asíncrona
        response = await client.chat(
            model=model_name,
            messages=user_histories[user_id]
        )
        
        bot_reply = response['message']['content']
        user_histories[user_id].append({"role": "assistant", "content": bot_reply})
        
        await update.message.reply_text(bot_reply)

    except Exception as e:
        logger.error(f"Error al comunicarse con Ollama: {e}")
        await update.message.reply_text(
            "Lo siento, estoy teniendo problemas técnicos en este momento. "
            "Por favor, intenta de nuevo más tarde."
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los errores ocurridos durante la ejecución del bot."""
    logger.error("Excepción ocurrida al procesar una actualización:", exc_info=context.error)

def create_application(token: str) -> Application:
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    return application

def main() -> None:
    # Intentar cargar variables de entorno desde el archivo .env si existe
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    token = os.getenv("PACIENTE_BOT_TOKEN", "NOT_FOUND")

    if token == "NOT_FOUND" or not token:
        logger.error(
            "No se ha encontrado la variable de entorno PACIENTE_BOT_TOKEN. "
            "Configura esa variable de entorno en tu archivo .env o en el sistema."
        )
        return

    logger.info("Iniciando el bot de pacientes...")
    application = create_application(token)
    
    # Inicia el bot en modo polling
    application.run_polling()

    # Para usar modo Webhook en producción/nube, desposta 'run_polling()' y comenta las siguientes líneas:
    # webhook_url = os.getenv("WEBHOOK_URL")  # Ej: https://tu-app.onrender.com
    # port = int(os.getenv("PORT", 8080))
    # application.run_webhook(
    #     listen="0.0.0.0",
    #     port=port,
    #     url_path=token,
    #     webhook_url=f"{webhook_url}/{token}"
    # )

if __name__ == '__main__':
    main()
