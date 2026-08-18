# TFG Chatbot para la gestion de clinicas privadas

## Verificación Manual de instalación

Para ponerlo en marcha, necesitas ejecutar los siguientes pasos en tu máquina:

> [!NOTE]
> **Paso 1: Configurar el Token**
> Asegúrate de que en tu archivo `.env` (en la misma carpeta que el `docker-compose.yml`) tienes la variable para tu nuevo bot:
>
> ```env
> DOCTOR_BOT_TOKEN=
> PACIENTE_BOT_TOKEN=
> ```
>
> **Paso 2: Arrancar los Contenedores**
> Abre una terminal en la carpeta de tu proyecto y levanta todos los servicios:
>
> ```bash
> docker-compose up -d --build
> ```
> **Paso 3: Descargar el modelo Llama 3.1 en Ollama**
> La primera vez que corres el contenedor de Ollama, estará vacío. Debes descargar el modelo Llama 3.1. (o el modélo de tu preferencia) Ejecuta este comando (puede tardar un rato dependiendo de tu conexión):
>```bash
> docker exec -it chatbot_clinica_ollama ollama run llama3.1 
> ```

>[!TIP]
>Para la conexión de google calendar genera una aplicación y un credential.json en está carpeta.