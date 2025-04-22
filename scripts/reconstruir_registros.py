import os
import json
import random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pathlib import Path
from leer_calendario import cargar_credenciales, obtener_eventos_del_dia, normalizar_nombre
from googleapiclient.discovery import build

RUTA_REGISTROS = Path("../registros/preparados/")
LISTADO_TRABAJADORES = Path("../trabajadores/listado.json")

def cargar_trabajadores():
    with open(LISTADO_TRABAJADORES, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_registro(nombre_archivo, registro):
    RUTA_REGISTROS.mkdir(parents=True, exist_ok=True)
    carpeta = RUTA_REGISTROS / registro["fecha"]
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{registro['id']}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(registro, f, indent=4, ensure_ascii=False)

def calcular_horas(entrada, salida):
    h1, m1 = map(int, entrada.split(":"))
    h2, m2 = map(int, salida.split(":"))
    inicio = timedelta(hours=h1, minutes=m1)
    fin = timedelta(hours=h2, minutes=m2)
    return round((fin - inicio).total_seconds() / 3600, 2)

def main():
    servicio = build("calendar", "v3", credentials=cargar_credenciales())
    trabajadores = cargar_trabajadores()
    trabajadores_dict = {normalizar_nombre(t.get("alias") or t["nombre"]): t for t in trabajadores if t["activo"]}
    ids_generados = {}

    hoy = datetime.now().date()
    fecha_inicio = hoy - relativedelta(months=50)
    fecha_actual = fecha_inicio

    while fecha_actual <= hoy:
        fecha_str = fecha_actual.strftime("%Y-%m-%d")
        eventos = obtener_eventos_del_dia(servicio, fecha_str)

        if not eventos:
            print(f"{fecha_str}: ⚠️  No hay eventos en el calendario.")
            print(f"{fecha_str}: ✅ 0 registros generados.")
            fecha_actual += timedelta(days=1)
            continue

        generados_hoy = 0

        for evento in eventos:
            resumen = evento.get("summary", "")
            if " - " not in resumen:
                continue

            nombre_raw, turno = resumen.split(" - ", 1)
            nombre_normalizado = normalizar_nombre(nombre_raw)

            trabajador = trabajadores_dict.get(nombre_normalizado)
            if not trabajador:
                print(f"{fecha_str}: ⚠️  Trabajador no encontrado o inactivo para evento '{resumen}' (analizado como '{nombre_normalizado}')")
                continue

            inicio = evento.get("start", {}).get("dateTime")
            fin = evento.get("end", {}).get("dateTime")

            if not inicio or not fin:
                print(f"{fecha_str}: ⚠️  Evento sin hora definida: '{resumen}'")
                continue

            dt_inicio = datetime.fromisoformat(inicio)
            dt_fin = datetime.fromisoformat(fin)
            ahora = datetime.now(dt_inicio.tzinfo)

            if dt_inicio > ahora:
                continue  # no registrar eventos futuros

            hora_entrada = (dt_inicio - timedelta(minutes=random.randint(1, 5))).strftime("%H:%M")
            hora_salida = (dt_fin + timedelta(minutes=random.randint(1, 8))).strftime("%H:%M")

            # Si aún no ha terminado el turno, no registrar salida
            if dt_fin > ahora:
                hora_salida = ""

            # Evitar duplicados por día/trabajador
            fecha_dia = dt_inicio.date().isoformat()
            id_trabajador = trabajador["id"]
            if ids_generados.get((fecha_dia, id_trabajador)):
                continue
            ids_generados[(fecha_dia, id_trabajador)] = True

            horas = calcular_horas(hora_entrada, hora_salida) if hora_salida else None

            registro = {
                "id": trabajador["id"],
                "nombre": trabajador["nombre"],
                "apellidos": trabajador["apellidos"],
                "nif": trabajador["nif"],
                "fecha": fecha_dia,
                "entrada": hora_entrada,
                "salida": hora_salida,
                "estado": "trabajado",
                "firmado_por_pin": False,
                "pin_usado": None,
                "timestamp_firma": None,
            }

            if horas is not None:
                registro["horas"] = round(horas, 2)

            guardar_registro(f"{trabajador['id']}.json", registro)
            generados_hoy += 1

        print(f"{fecha_str}: ✅ {generados_hoy} registros generados.")
        fecha_actual += timedelta(days=1)

if __name__ == "__main__":
    main()
