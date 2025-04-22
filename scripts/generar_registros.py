import os
import json
from datetime import datetime, timedelta
import random
from googleapiclient.discovery import build
from leer_calendario import cargar_credenciales, obtener_eventos_del_dia, normalizar_nombre, obtener_trabajadores_activos

def calcular_horas(entrada, salida):
    fmt = "%H:%M"
    h1 = datetime.strptime(entrada, fmt)
    h2 = datetime.strptime(salida, fmt)
    return round((h2 - h1).total_seconds() / 3600, 2)

def obtener_ruta_registro(nombre_archivos, fecha, trabajador_id):
    año = fecha[:4]
    mes = fecha[5:7]
    carpeta = os.path.join("..", "registros", año, mes)
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, f"{trabajador_id}.json")

def main():
    print("\n🕓 Generando registros recientes...")

    servicio = build('calendar', 'v3', credentials=cargar_credenciales())
    trabajadores = obtener_trabajadores_activos()

    hoy = datetime.now().date()
    for i in range(3):  # Días recientes: hoy, ayer, anteayer
        dia = hoy - timedelta(days=i)
        fecha_str = dia.strftime("%Y-%m-%d")
        eventos = obtener_eventos_del_dia(servicio, fecha=fecha_str)

        registros_creados = 0
        nombres_procesados = []

        for evento in eventos:
            resumen = evento.get("summary", "")
            if "-" not in resumen:
                continue

            nombre_evento = resumen.split("-")[0].strip()
            nombre_normalizado = normalizar_nombre(nombre_evento)

            trabajador = trabajadores.get(nombre_normalizado)
            if not trabajador:
                print(f"{fecha_str}: ⚠️  Trabajador no encontrado o inactivo para evento '{resumen}' (analizado como '{nombre_normalizado}')")
                continue

            id_trabajador = trabajador["id"]
            ruta_archivo = obtener_ruta_registro("registros", fecha_str, id_trabajador)

            # Obtener hora de inicio y fin si están disponibles
            try:
                inicio = evento["start"]["dateTime"]
                fin = evento["end"]["dateTime"]
            except KeyError:
                print(f"{fecha_str}: ⚠️  Evento sin hora definida: '{resumen}'")
                continue

            # Verifica si ya ha empezado o terminado el turno
            dt_inicio = datetime.fromisoformat(inicio)
            dt_fin = datetime.fromisoformat(fin)
            ahora = datetime.now(dt_inicio.tzinfo)

            if dt_inicio > ahora:
                continue  # Aún no ha empezado el turno

            if os.path.exists(ruta_archivo):
                with open(ruta_archivo, "r", encoding="utf-8") as f:
                    registro = json.load(f)
            else:
                registro = {
                    "id": id_trabajador,
                    "nombre": trabajador["nombre"],
                    "apellidos": trabajador["apellidos"],
                    "nif": trabajador["nif"],
                    "fecha": fecha_str,
                    "estado": "trabajado",
                    "firmado_por_pin": False
                }

            # Añadir entrada si no existe
            if "entrada" not in registro:
                hora_entrada = dt_inicio - timedelta(minutes=random.randint(0, 5))
                registro["entrada"] = hora_entrada.strftime("%H:%M")

            # Añadir salida si ha terminado y no se había registrado
            if dt_fin <= ahora and "salida" not in registro:
                hora_salida = dt_fin + timedelta(minutes=random.randint(0, 8))
                registro["salida"] = hora_salida.strftime("%H:%M")

            # Calcular horas si ambas existen
            if "entrada" in registro and "salida" in registro and "horas" not in registro:
                registro["horas"] = f"{calcular_horas(registro['entrada'], registro['salida']):.2f}"

            with open(ruta_archivo, "w", encoding="utf-8") as f:
                json.dump(registro, f, indent=4, ensure_ascii=False)

            registros_creados += 1
            nombres_procesados.append(trabajador["nombre"])

        print(f"{fecha_str}: ✅ {registros_creados} registros generados.")


if __name__ == "__main__":
    main()
