import os
import json
import pytz
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
RUTA_CREDENCIALES = os.path.join(os.path.dirname(__file__), '..', 'credenciales', 'token.json')
RUTA_CLIENT_SECRET = os.path.join(os.path.dirname(__file__), '..', 'credenciales', 'client_secret.json')
RUTA_LISTADO = os.path.join(os.path.dirname(__file__), '..', 'trabajadores', 'listado.json')

def cargar_credenciales():
    creds = None
    if os.path.exists(RUTA_CREDENCIALES):
        creds = Credentials.from_authorized_user_file(RUTA_CREDENCIALES, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(RUTA_CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(RUTA_CREDENCIALES, 'w') as token:
            token.write(creds.to_json())
    return creds

def obtener_eventos_del_dia(servicio, fecha):
    tz = pytz.timezone("Europe/Madrid")
    fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
    inicio = tz.localize(datetime.combine(fecha_obj, datetime.min.time())).isoformat()
    fin = tz.localize(datetime.combine(fecha_obj, datetime.max.time())).isoformat()
    eventos_resultado = servicio.events().list(
        calendarId='primary',
        timeMin=inicio,
        timeMax=fin,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return eventos_resultado.get('items', [])

def normalizar_nombre(texto):
    return texto.lower().replace("á", "a").replace("é", "e").replace("í", "i") \
               .replace("ó", "o").replace("ú", "u").replace("ü", "u") \
               .replace(".", "").strip()

def obtener_trabajadores_activos():
    ruta = RUTA_LISTADO
    with open(ruta, "r", encoding="utf-8") as file:
        trabajadores = json.load(file)
    activos = {}
    for t in trabajadores:
        if t.get("activo", True):  # por compatibilidad si falta campo
            nombre_normalizado = normalizar_nombre(t["nombre"])
            alias_normalizado = normalizar_nombre(t.get("alias", "")) if t.get("alias") else ""
            activos[nombre_normalizado] = t
            if alias_normalizado:
                activos[alias_normalizado] = t
    return activos
