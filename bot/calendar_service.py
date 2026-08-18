import os
import datetime
import asyncio
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

# Si cambias los alcances (scopes), elimina el archivo token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Muestra la autenticación básica de la API de Google Calendar."""
    creds = None
    # El archivo token.json almacena los tokens de acceso y actualización del usuario, y se
    # crea automáticamente cuando el flujo de autorización se completa por primera vez.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Si no hay credenciales válidas (o no existen), permite al usuario iniciar sesión.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("No se encontró el archivo credentials.json. Por favor, descárgalo de Google Cloud Console.")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Guarda las credenciales para la próxima vez
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

async def check_availability(date_str: str) -> str:
    """
    Comprueba las citas existentes para un día específico y devuelve la disponibilidad.
    date_str: Fecha en formato YYYY-MM-DD
    """
    return await asyncio.to_thread(_check_availability_sync, date_str)

def _check_availability_sync(date_str: str) -> str:
    try:
        service = get_calendar_service()
        # Parseamos la fecha para obtener el inicio y fin del día
        start_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        end_date = start_date + datetime.timedelta(days=1)
        
        # Ajustamos timezone si es necesario, pero simplificaremos asumiendo la hora local
        time_min = start_date.astimezone().isoformat()
        time_max = end_date.astimezone().isoformat()

        logger.info(f"Buscando citas entre {time_min} y {time_max}")
        events_result = service.events().list(calendarId='primary', timeMin=time_min,
                                              timeMax=time_max, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return f"No hay citas programadas para el {date_str}. Todo el día está disponible."
        
        respuesta = f"Citas ocupadas para el {date_str}:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            # Format to simpler string
            if 'T' in start:
                start_time = start.split('T')[1][:5]
                end_time = end.split('T')[1][:5]
                respuesta += f"- De {start_time} a {end_time} (Ocupado)\n"
            else:
                respuesta += f"- Todo el día (Ocupado)\n"
                
        return respuesta
    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        return f"Hubo un error al comprobar la disponibilidad: {str(e)}"

async def create_appointment(summary: str, date_str: str, time_str: str) -> str:
    """
    Crea una nueva cita en el calendario.
    summary: Título o descripción corta (ej. "Cita con Juan Pérez - Dolor de cabeza")
    date_str: Fecha en formato YYYY-MM-DD
    time_str: Hora de inicio en formato HH:MM (asumimos duración de 30 min)
    """
    return await asyncio.to_thread(_create_appointment_sync, summary, date_str, time_str)

def _create_appointment_sync(summary: str, date_str: str, time_str: str) -> str:
    try:
        service = get_calendar_service()
        
        start_datetime = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_datetime = start_datetime + datetime.timedelta(minutes=30)
        
        event = {
          'summary': summary,
          'start': {
            'dateTime': start_datetime.astimezone().isoformat(),
          },
          'end': {
            'dateTime': end_datetime.astimezone().isoformat(),
          },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        logger.info(f"Cita creada: {event.get('htmlLink')}")
        return f"La cita '{summary}' ha sido programada con éxito para el {date_str} a las {time_str}."
    except Exception as e:
        logger.error(f"Error creating appointment: {e}")
        return f"Hubo un error al crear la cita: {str(e)}"

async def get_todays_appointments() -> list:
    """Devuelve las citas de hoy (útil para el bot del doctor)."""
    return await asyncio.to_thread(_get_todays_appointments_sync)

def _get_todays_appointments_sync() -> list:
    try:
        service = get_calendar_service()
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + datetime.timedelta(days=1)
        
        time_min = today.astimezone().isoformat()
        time_max = tomorrow.astimezone().isoformat()
        
        events_result = service.events().list(calendarId='primary', timeMin=time_min,
                                              timeMax=time_max, singleEvents=True,
                                              orderBy='startTime').execute()
        return events_result.get('items', [])
    except Exception as e:
        logger.error(f"Error getting today's appointments: {e}")
        return []
