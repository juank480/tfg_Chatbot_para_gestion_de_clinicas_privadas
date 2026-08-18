import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from database import db
import calendar_service

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
    
    keyboard = [
        ["📄 Ver Resúmenes Pendientes", "📅 Ver Citas de Hoy"],
        ["❓ Ayuda"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_message = (
        f"¡Hola {user_name}! 👋\n"
        "Bienvenido al sistema de gestión de clínicas privadas.\n\n"
        "Utiliza los botones del menú de abajo para interactuar con el sistema."
    )
    if update.message:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /help."""
    help_text = (
        "📌 *Comandos disponibles:*\n"
        "/start - Iniciar interacción con el bot\n"
        "/help - Mostrar este mensaje de ayuda\n"
        "/resumen <id_doctor> - Obtener el resumen de las conversaciones de un doctor\n"
        "/citas_hoy - Ver las citas programadas para el día de hoy"
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las pulsaciones de los botones del teclado interactivo."""
    if not update.message or not update.message.text:
        return
        
    text = update.message.text
    if text == "📄 Ver Resúmenes Pendientes":
        await get_resumen_command(update, context)
    elif text == "📅 Ver Citas de Hoy":
        await get_citas_hoy_command(update, context)
    elif text == "❓ Ayuda":
        await help_command(update, context)
    else:
        await update.message.reply_text(f"Comando o botón no reconocido: {text}")

async def get_resumen_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /resumen."""
    doctor_id = 1
    if context.args:
        try:
            doctor_id = int(context.args[0])
        except ValueError:
            pass # Ignoramos error y usamos doctor_id 1 por defecto

    if update.message:
        await update.message.reply_text("Consultando resúmenes de pacientes pendientes...")
    
    resumenes = await db.get_resumenes_doctor(doctor_id)
    
    if resumenes is None:
        if update.message:
            await update.message.reply_text("Ocurrió un error al consultar la base de datos.")
        return
    
    if not resumenes:
        if update.message:
            await update.message.reply_text("No hay resúmenes pendientes.")
        return

    respuesta = f" *Resúmenes de Pacientes:*\n\n"
    for r in resumenes:
        cita = r['cita_medica_fecha'].strftime('%Y-%m-%d %H:%M') if r['cita_medica_fecha'] else "Pendiente de asignar"
        icono = "🔴 (Abandono)" if r['estado'] == 'CANCELADA' else "🟢 (Completado)"
        respuesta += f"- *Paciente:* {r['paciente_nombre']} (Tel: {r['paciente_telefono']})\n"
        respuesta += f"  *Telegram ID:* `{r['paciente_telegram_id']}` | *Chat ID:* `{r['conversacion_id']}`\n"
        respuesta += f"  *Estado Triaje:* {icono}\n"
        respuesta += f"  *Cita Médica:* {cita}\n"
        respuesta += f"  *Resumen:* {r['resumen']}\n"
        respuesta += f"  *Fecha Registro:* {r['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"

    if update.message:
        await update.message.reply_text(respuesta, parse_mode="Markdown")

async def get_citas_hoy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Consulta las citas de hoy en Google Calendar."""
    if update.message:
        await update.message.reply_text("🗓️ Consultando el calendario para el día de hoy...")
    
    citas = await calendar_service.get_todays_appointments()
    
    if not citas:
        if update.message:
            await update.message.reply_text("✅ No tienes citas programadas para el día de hoy.")
        return

    respuesta = "📅 *Tus citas para hoy:*\n\n"
    for event in citas:
        summary = event.get('summary', 'Sin título')
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        # Formatear la hora
        if 'T' in start:
            start_time = start.split('T')[1][:5]
            end_time = end.split('T')[1][:5]
            respuesta += f"🔸 *{start_time} - {end_time}*: {summary}\n"
        else:
            respuesta += f"🔸 *Todo el día*: {summary}\n"
            
    if update.message:
        await update.message.reply_text(respuesta, parse_mode="Markdown")

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
    application.add_handler(CommandHandler("resumen", get_resumen_command))
    application.add_handler(CommandHandler("citas_hoy", get_citas_hoy_command))
    
    # Registrar handler de botones (mensajes de texto)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

    # Registrar manejador global de errores
    application.add_error_handler(error_handler)

    return application

def main() -> None:
    """Punto de entrada principal para iniciar el bot."""
    # Intentar cargar variables de entorno desde el archivo .env si existe
    try:
        from dotenv import load_dotenv # type: ignore
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
