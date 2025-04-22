from __future__ import print_function
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pytz

# Cargar variables de entorno desde .env
load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
GOOGLE_TOKEN_URI = os.getenv("GOOGLE_TOKEN_URI")

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CALENDAR_ID = os.getenv("CALENDAR_ID")

def cargar_credenciales():
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=creds)

def obtener_eventos_del_dia(servicio, fecha=None):
    if fecha is None:
        fecha = datetime.now().date().isoformat()
    zona_horaria = 'Europe/Madrid'
    tz = pytz.timezone(zona_horaria)
    inicio = tz.localize(datetime.fromisoformat(fecha))
    fin = inicio + timedelta(days=1)

    eventos_resultado = servicio.events().list(
        calendarId=CALENDAR_ID,
        timeMin=inicio.isoformat(),
        timeMax=fin.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return eventos_resultado.get('items', [])

def normalizar_nombre(nombre):
    return nombre.strip().lower().lstrip('.')

def obtener_trabajadores_activos():
    ruta = os.path.join("trabajadores", "listado.json")
    with open(ruta, "r", encoding="utf-8") as file:
        trabajadores = json.load(file)
    activos = {}
    for t in trabajadores:
        if t.get("activo", True):
            nombre_clave = normalizar_nombre(t["nombre"])
            activos[nombre_clave] = t
            if "alias" in t:
                for a in t["alias"]:
                    activos[normalizar_nombre(a)] = t
    return activos
