from fpdf import FPDF
import json
from pathlib import Path
from datetime import datetime
import calendar
import unicodedata
import os

RUTA_REGISTROS = Path("../registros/preparados/")
RUTA_TRABAJADORES = Path("../trabajadores/listado.json")
RUTA_PDFS = Path("../pdfs")

NOMBRE_EMPRESA = "Juan Sande Álvarez"
NIF_EMPRESA = "32816331T"

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, self.titulo, ln=True, align="C")
        self.ln(5)

    def footer(self):
        pass

def normalizar(s):
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    ).replace(" ", "")

def cargar_trabajadores():
    with open(RUTA_TRABAJADORES, encoding="utf-8") as f:
        return json.load(f)

def obtener_nombre_dia(fecha):
    dias = ["L", "M", "X", "J", "V", "S", "D"]
    return dias[fecha.weekday()]

def horas_str_a_float(horas_str):
    h, m = map(int, horas_str.split(":"))
    return h + m / 60

def generar_pdf(trabajador_id, anio, mes):
    trabajadores = cargar_trabajadores()
    trabajador = next((t for t in trabajadores if str(t['id']) == str(trabajador_id)), None)
    if not trabajador:
        print(f"⚠️ Trabajador con ID {trabajador_id} no encontrado.")
        return

    registros_mes = []
    total_horas = 0.0
    total_extras = 0.0

    for dia in range(1, calendar.monthrange(anio, mes)[1] + 1):
        fecha = datetime(anio, mes, dia)
        fecha_str = fecha.strftime("%Y-%m-%d")
        carpeta = RUTA_REGISTROS / fecha_str
        archivo = carpeta / f"{trabajador_id}.json"
        if archivo.exists():
            with open(archivo, encoding="utf-8") as f:
                data = json.load(f)
                registros_mes.append(data)
                if data.get("estado") == "trabajado" and "horas" in data:
                    horas = horas_str_a_float(data["horas"])
                    total_horas += horas
                    if horas > 8:
                        total_extras += horas - 8

    if not registros_mes:
        print(f"⚠️ No hay registros para {trabajador['nombre']} en {mes:02d}/{anio}")
        return

    nombre_archivo_base = f"{anio}_{mes:02d}_RH_{normalizar(trabajador['nombre'])}{normalizar(trabajador['apellidos'])}.pdf"
    carpeta_salida = RUTA_PDFS / str(anio) / f"{normalizar(trabajador['nombre'])}{normalizar(trabajador['apellidos'])}"
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    nombre_archivo = carpeta_salida / nombre_archivo_base
    contador = 2
    while nombre_archivo.exists():
        nombre_archivo = carpeta_salida / f"{nombre_archivo_base[:-4]} ({contador}).pdf"
        contador += 1

    pdf = PDF()
    pdf.titulo = f"Registro horario - {mes:02d}/{anio}"
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    pdf.cell(0, 10, f"Empresa: {NOMBRE_EMPRESA} - NIF: {NIF_EMPRESA}", ln=True)
    pdf.cell(0, 10, f"Trabajador: {trabajador['nombre']} {trabajador['apellidos']} - NIF: {trabajador['nif']}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 9)
    pdf.cell(28, 8, "Fecha", 1)
    pdf.cell(20, 8, "Entrada", 1)
    pdf.cell(15, 8, "Firma", 1)
    pdf.cell(20, 8, "Salida", 1)
    pdf.cell(15, 8, "Firma", 1)
    pdf.cell(20, 8, "Horas", 1)
    pdf.cell(40, 8, "Estado", 1)
    pdf.ln()

    pdf.set_font("Arial", size=9)
    for r in registros_mes:
        fecha_dt = datetime.strptime(r["fecha"], "%Y-%m-%d")
        dia = fecha_dt.strftime("%d-%m-%Y")
        dia_semana = obtener_nombre_dia(fecha_dt)
        entrada = r.get("entrada", "")
        salida = r.get("salida", "")
        firma_e = "S" if entrada and r.get("firmado_por_pin") else ""
        firma_s = "S" if salida and r.get("firmado_por_pin") else ""
        horas = r.get("horas", "")
        estado = r.get("estado", "")

        pdf.cell(28, 7, f"{dia} ({dia_semana})", 1)
        pdf.cell(20, 7, entrada, 1)
        pdf.cell(15, 7, firma_e, 1)
        pdf.cell(20, 7, salida, 1)
        pdf.cell(15, 7, firma_s, 1)
        pdf.cell(20, 7, horas, 1)
        pdf.cell(40, 7, estado, 1)
        pdf.ln()

    pdf.ln(3)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 8, f"Total horas trabajadas: {round(total_horas, 2)} h", ln=True)
    if total_extras > 0:
        pdf.cell(0, 8, f"Total horas extra: {round(total_extras, 2)} h", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", size=8)
    pdf.multi_cell(0, 6, "Este documento ha sido generado automáticamente a partir del registro horario firmado con PIN personal por el trabajador/a. Conservar durante 4 años según normativa laboral vigente.")

    pdf.output(str(nombre_archivo))
    print(f"✅ PDF generado: {nombre_archivo}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--trabajador", required=True, help="ID del trabajador")
    parser.add_argument("--anio", type=int, required=True)
    parser.add_argument("--mes", type=int, required=True)
    args = parser.parse_args()
    generar_pdf(args.trabajador, args.anio, args.mes)
