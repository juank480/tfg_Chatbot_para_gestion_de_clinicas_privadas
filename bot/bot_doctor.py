import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
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

# Estados para la conversación de Login
TELEFONO, PASSWORD = range(2)

# --- Handlers de Comandos Básico ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start."""
    user_name = update.effective_user.first_name if update.effective_user else "usuario"
    
    # Si ya está logueado, le mostramos el menú directamente
    if context.user_data.get('doctor_id'):
        keyboard = [
            ["Ver Resúmenes Pendientes", "📅 Ver Citas de Hoy"],
            ["Ayuda"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        welcome_message = f"¡Hola de nuevo {user_name}! 👋\nUsa los botones para interactuar."
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
        return

    welcome_message = (
        f"¡Hola {user_name}! 👋\n"
        "Bienvenido al sistema de gestión de clínicas privadas.\n\n"
        "Por favor, inicia sesión usando el comando /login para continuar."
    )
    if update.message:
        await update.message.reply_text(welcome_message, reply_markup=ReplyKeyboardRemove())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /help."""
    help_text = (
        "*Comandos disponibles:*\n"
        "/start - Iniciar interacción con el bot\n"
        "/login - Iniciar sesión con tu teléfono y contraseña\n"
        "/logout - Cerrar sesión\n"
        "/help - Mostrar este mensaje de ayuda\n"
        "/resumen - Obtener el resumen de tus conversaciones\n"
        "/citas_hoy - Ver las citas programadas para el día de hoy"
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode="Markdown")

# --- Flujo de Login ---

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el flujo de login pidiendo el teléfono."""
    if context.user_data.get('doctor_id'):
        await update.message.reply_text("Ya has iniciado sesión. Usa /logout si quieres salir.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Por favor, introduce tu número de teléfono registrado:\n"
        "(Puedes usar /cancelar para abortar el login)",
        reply_markup=ReplyKeyboardRemove()
    )
    return TELEFONO

async def login_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el teléfono y pide la contraseña."""
    telefono = update.message.text.strip()
    context.user_data['temp_telefono'] = telefono
    
    await update.message.reply_text("Ahora, introduce tu contraseña:")
    return PASSWORD

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Verifica el teléfono y la contraseña."""
    password = update.message.text.strip()
    telefono = context.user_data.get('temp_telefono')
    
    # Borrar temporal por seguridad
    if 'temp_telefono' in context.user_data:
        del context.user_data['temp_telefono']
        
    await update.message.reply_text("Verificando credenciales...")
    
    doctor_id = await db.autenticar_doctor(telefono, password)
    
    if doctor_id:
        context.user_data['doctor_id'] = doctor_id
        
        keyboard = [
            ["Ver Resúmenes Pendientes", "Ver Citas de Hoy"],
            ["Ayuda"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "¡Inicio de sesión exitoso!\nYa puedes acceder a las funcionalidades del bot.",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("Teléfono o contraseña incorrectos. Usa /login para volver a intentarlo.")
        
    return ConversationHandler.END

async def login_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela el flujo de login."""
    if 'temp_telefono' in context.user_data:
        del context.user_data['temp_telefono']
    await update.message.reply_text("Inicio de sesión cancelado.")
    return ConversationHandler.END

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cierra la sesión del doctor."""
    context.user_data.clear()
    await update.message.reply_text("Has cerrado sesión correctamente. Usa /login para volver a entrar.", reply_markup=ReplyKeyboardRemove())

# --- Comandos Protegidos ---

def require_login(func):
    """Decorador para requerir login antes de ejecutar un comando."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not context.user_data.get('doctor_id'):
            await update.message.reply_text("Debes iniciar sesión con /login para usar esta función.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

@require_login
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las pulsaciones de los botones del teclado interactivo."""
    if not update.message or not update.message.text:
        return
        
    text = update.message.text
    if text == "Ver Resúmenes de hoy":
        await get_resumen_command(update, context)
    elif text == "Ver Citas de Hoy":
        await get_citas_hoy_command(update, context)
    elif text == "Ayuda":
        await help_command(update, context)
    else:
        await update.message.reply_text(f"Comando o botón no reconocido: {text}")

@require_login
async def get_resumen_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /resumen."""
    doctor_id = context.user_data.get('doctor_id')

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

@require_login
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
    application = ApplicationBuilder().token(token).build()

    # Handlers básicos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("logout", logout_command))
    
    # Comandos que requieren login
    application.add_handler(CommandHandler("resumen", get_resumen_command))
    application.add_handler(CommandHandler("citas_hoy", get_citas_hoy_command))

    # ConversationHandler para login
    login_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('login', login_start)],
        states={
            TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_telefono)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[CommandHandler('cancelar', login_cancel)]
    )
    application.add_handler(login_conv_handler)
    
    # Botones (fallback tras los comandos)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

    application.add_error_handler(error_handler)

    return application

def main() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    token = os.getenv("DOCTOR_BOT_TOKEN", "NOT_FOUND")

    if token == "NOT_FOUND" or not token:
        logger.error(
            "No se ha encontrado la variable de entorno DOCTOR_BOT_TOKEN. "
            "Configura esa variable de entorno en tu archivo .env o en el sistema."
        )
        return

    logger.info("Iniciando el bot de Telegram para doctores (con autenticación)...")
    application = create_application(token)
    
    application.run_polling()

if __name__ == '__main__':
    main()
