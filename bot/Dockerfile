# Usar una imagen oficial de Python ligera
FROM python:3.11-slim

# Evitar la creación de archivos .pyc y forzar el salida directa de stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Definir el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar e instalar dependencias
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . /app/

# Comando para ejecutar el bot de Telegram
CMD ["python", "bot_doctor.py"]
