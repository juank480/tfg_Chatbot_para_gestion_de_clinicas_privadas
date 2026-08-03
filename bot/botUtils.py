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

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- Handlers de Comandos Básico ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start."""
    user_name = update.effective_user.first_name if update.effective_user else "usuario"
    welcome_message = (
        f"¡Hola {user_name}! 👋\n"
        "Bienvenido al sistema de gestión de clínicas privadas.\n\n"
        "Escribe /help para ver los comandos disponibles."
    )
    if update.message:
        await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /help."""
    help_text = (
        "📌 *Comandos disponibles:*\n"
        "/start - Iniciar interacción con el bot\n"
        "/help - Mostrar este mensaje de ayuda"
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode="Markdown")

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a los mensajes de texto habituales del usuario."""
    if update.message and update.message.text:
        await update.message.reply_text(f"Has dicho: {update.message.text}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los errores ocurridos durante la ejecución del bot."""
    logger.error("Excepción ocurrida al procesar una actualización:", exc_info=context.error)


# --- Funciones de Configuración y Ejecución ---

def create_application(token: str) -> Application:
    """
    Crea y configura la instancia del bot de Telegram con sus manejadores.
    
    :param token: Token de autenticación de Telegram Bot API.
    :return: Instancia configurada de Application.
    """
    application = ApplicationBuilder().token(token).build()

    # Registrar handlers de comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Registrar handler de mensajes de texto
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))

    # Registrar manejador global de errores
    application.add_error_handler(error_handler)

    return application

def main() -> None:
    """Punto de entrada principal para iniciar el bot."""
    # Intentar cargar variables de entorno desde el archivo .env si existe
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # El token se obtiene prioritariamente de las variables de entorno
    token = os.getenv("DOCTOR_BOT_TOKEN", "NOT_FOUND")

    if token == "NOT_FOUND" or not token:
        logger.error(
            "No se ha encontrado la variable de entorno DOCTOR_BOT_TOKEN. "
            "Configura esa variable de entorno en tu archivo .env o en el sistema."
        )
        return

    logger.info("Iniciando el bot de Telegram...")
    application = create_application(token)
    
    # Inicia el bot en modo polling
    application.run_polling()


if __name__ == '__main__':
    main()
