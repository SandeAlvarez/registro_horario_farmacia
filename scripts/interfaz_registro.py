
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
import json
import os
import subprocess
import uuid
import shutil
from pathlib import Path

# Rutas
LISTADO_TRABAJADORES = '../trabajadores/listado.json'
SCRIPT_PDF = 'generar_pdf_mensual.py'
RUTA_REGISTROS = '../registros/preparados/'

# Funciones auxiliares
def cargar_trabajadores():
    with open(LISTADO_TRABAJADORES, 'r', encoding='utf-8') as f:
        return json.load(f)

def guardar_trabajadores(trabajadores):
    with open(LISTADO_TRABAJADORES, 'w', encoding='utf-8') as f:
        json.dump(trabajadores, f, indent=4, ensure_ascii=False)

def fichar(tipo):
    pin = pin_entry.get().strip()
    if not pin:
        messagebox.showerror("Error", "Introduce el PIN")
        return

    trabajadores = cargar_trabajadores()
    trabajador = next((t for t in trabajadores if t['pin'] == pin), None)
    if not trabajador:
        nombre_var.set("PIN no válido")
        return

    nombre_var.set(f"{trabajador['nombre']} {trabajador['apellidos']}")

    if not trabajador['activo']:
        messagebox.showerror("Error", "Este trabajador no está activo")
        return

    tipo_str = "entrada" if tipo == 'entrada' else "salida"

    try:
        subprocess.run(['python', 'generar_registros.py'], check=True)
        messagebox.showinfo("Éxito", f"{trabajador['nombre']} ha fichado {tipo_str} correctamente")
    except subprocess.CalledProcessError:
        messagebox.showerror("Error", "No se pudo generar el registro")

def generar_pdf():
    trabajador_nombre = trabajador_cb.get()
    mes = mes_cb.get()
    anio = int(anio_cb.get())

    trabajadores = cargar_trabajadores()
    trabajadores_filtrados = [
        t for t in trabajadores if t['activo']
    ] if trabajador_nombre == "Todos los trabajadores" else [
        next((t for t in trabajadores if t['nombre'] == trabajador_nombre), None)
    ]

    if not trabajadores_filtrados or None in trabajadores_filtrados:
        messagebox.showerror("Error", "Trabajador no encontrado")
        return

    meses = range(1, 13) if mes == "Todos los meses" else [int(mes)]

    errores = []
    for t in trabajadores_filtrados:
        for m in meses:
            try:
                subprocess.run(
                    ['python', SCRIPT_PDF, '--trabajador', str(t['id']), '--anio', str(anio), '--mes', str(m)],
                    check=True
                )
            except subprocess.CalledProcessError:
                errores.append(f"{t['nombre']} - {m:02d}/{anio}")

    if errores:
        messagebox.showwarning("Finalizado con errores", f"Se produjeron errores con: {', '.join(errores)}")
    else:
        messagebox.showinfo("Éxito", "Todos los PDFs se han generado correctamente.")

def borrar_registros():
    fecha_inicio = simpledialog.askstring("Fecha inicio", "Introduce la fecha de inicio (AAAA-MM-DD):")
    fecha_fin = simpledialog.askstring("Fecha fin", "Introduce la fecha de fin (AAAA-MM-DD):")

    if not fecha_inicio or not fecha_fin:
        return

    try:
        inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fin = datetime.strptime(fecha_fin, "%Y-%m-%d")
    except ValueError:
        messagebox.showerror("Error", "Formato de fecha incorrecto")
        return

    if inicio > fin:
        messagebox.showerror("Error", "La fecha de inicio debe ser anterior a la de fin")
        return

    confirm = messagebox.askyesno("Confirmar", f"¿Seguro que deseas borrar todos los registros desde {fecha_inicio} hasta {fecha_fin}?")
    if not confirm:
        return

    dias_borrados = 0
    while inicio <= fin:
        carpeta_dia = Path(RUTA_REGISTROS) / inicio.strftime("%Y-%m-%d")
        if carpeta_dia.exists() and carpeta_dia.is_dir():
            shutil.rmtree(carpeta_dia)
            dias_borrados += 1
        inicio += timedelta(days=1)

    messagebox.showinfo("Finalizado", f"Se han borrado los registros de {dias_borrados} días")

# Interfaz
root = tk.Tk()
root.title("Registro Horario - Farmacia")
root.geometry("400x600")

# --- Fichar entrada/salida ---
tk.Label(root, text="Fichar entrada/salida", font=("Arial", 12, "bold")).pack(pady=10)
tk.Label(root, text="PIN del trabajador:").pack()
pin_entry = tk.Entry(root, show='*')
pin_entry.pack(pady=5)
nombre_var = tk.StringVar()
tk.Label(root, textvariable=nombre_var, fg="blue").pack()
tk.Button(root, text="Fichar entrada", command=lambda: fichar('entrada')).pack(pady=2)
tk.Button(root, text="Fichar salida", command=lambda: fichar('salida')).pack(pady=2)

# --- Generar PDF mensual ---
tk.Label(root, text="\nGenerar PDF mensual", font=("Arial", 12, "bold")).pack(pady=10)
trabajadores = cargar_trabajadores()
trabajador_cb = ttk.Combobox(root, values=["Todos los trabajadores"] + [t['nombre'] for t in trabajadores])
trabajador_cb.pack(pady=5)

mes_cb = ttk.Combobox(root, values=["Todos los meses"] + [str(i) for i in range(1, 13)])
mes_cb.set(str(datetime.now().month))
mes_cb.pack(pady=2)

anio_cb = ttk.Combobox(root, values=[str(a) for a in range(2021, datetime.now().year + 1)])
anio_cb.set(str(datetime.now().year))
anio_cb.pack(pady=2)

tk.Button(root, text="Generar PDF", command=generar_pdf).pack(pady=5)

def editar_trabajadores():
    editar = tk.Toplevel(root)
    editar.title("Editar trabajadores")
    editar.geometry("800x500")

    trabajadores = cargar_trabajadores()
    columnas = ("id", "nombre", "apellidos", "nif", "pin", "activo")
    tree = ttk.Treeview(editar, columns=columnas, show="headings")
    for col in columnas:
        tree.heading(col, text=col.capitalize())
        tree.column(col, width=100)

    for t in trabajadores:
        tree.insert('', 'end', values=(t['id'], t['nombre'], t['apellidos'], t['nif'], t['pin'], 'Sí' if t['activo'] else 'No'))

    tree.pack(expand=True, fill='both', pady=10)

    def actualizar_y_guardar():
        nuevos = []
        pins = set()
        for item_id in tree.get_children():
            values = tree.item(item_id)['values']
            trabajador = {
                "id": str(values[0]),
                "nombre": values[1],
                "apellidos": values[2],
                "nif": values[3],
                "pin": values[4],
                "activo": True if values[5] == 'Sí' else False
            }
            if trabajador['pin'] in pins:
                messagebox.showerror("Error", f"PIN duplicado: {trabajador['pin']}")
                return
            pins.add(trabajador['pin'])
            nuevos.append(trabajador)
        guardar_trabajadores(nuevos)

    def nuevo_trabajador():
        nuevo_id = str(uuid.uuid4())[:8]
        nuevo_item = tree.insert('', 'end', values=(nuevo_id, "", "", "", "", 'Sí'))
        tree.focus(nuevo_item)
        tree.selection_set(nuevo_item)
        tree.see(nuevo_item)
        actualizar_y_guardar()

    def eliminar_trabajador():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecciona un trabajador para eliminar")
            return
        item = tree.item(selected[0])
        valores = item['values']
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres eliminar al trabajador seleccionado?"):
            tree.item(selected[0], values=(valores[0], valores[1], valores[2], valores[3], valores[4], 'No'))
            actualizar_y_guardar()

    def editar_celda(event):
        item = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not item or col == '#0':
            return
        col_index = int(col[1:]) - 1
        x, y, w, h = tree.bbox(item, col)
        entry = tk.Entry(editar)
        entry.place(x=x, y=y + tree.winfo_y())
        entry.insert(0, tree.item(item)['values'][col_index])
        entry.focus()

        def guardar(event):
            tree.set(item, column=columnas[col_index], value=entry.get())
            entry.destroy()
            actualizar_y_guardar()

        entry.bind('<Return>', guardar)
        entry.bind('<FocusOut>', guardar)

    tree.bind('<Double-1>', editar_celda)

    frame_botones = tk.Frame(editar)
    frame_botones.pack(pady=5)
    tk.Button(frame_botones, text="Añadir nuevo trabajador", command=nuevo_trabajador).pack(side="left", padx=5)
    tk.Button(frame_botones, text="Eliminar trabajador", command=eliminar_trabajador).pack(side="left", padx=5)

tk.Button(root, text="Editar trabajadores", command=editar_trabajadores).pack(pady=10)
tk.Button(root, text="Borrar registros entre fechas", command=borrar_registros).pack(pady=10)

root.mainloop()
