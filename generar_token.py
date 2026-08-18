import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar']

def main():
    if not os.path.exists('credentials.json'):
        print("Error: No se ha encontrado credentials.json.")
        print("Por favor, descárgalo de Google Cloud Console y ponlo en esta carpeta primero.")
        return

    print("Iniciando flujo de autenticación...")
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
        

if __name__ == '__main__':
    main()
