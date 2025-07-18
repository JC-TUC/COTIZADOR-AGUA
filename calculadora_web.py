# -*- coding: utf-8 -*-
# Archivo: calculadora_web.py

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import io

IVA_FACTOR = 1.16
JSON_FILE = "productos.json"

# --- Funciones de Lógica ---
def cargar_productos():
    """Carga los productos desde el archivo JSON."""
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        st.error(f"No se pudo cargar o no existe el archivo '{JSON_FILE}'.")
        return []

def generar_pdf(nombre_cliente, cotizacion_actual, totales):
    """Genera un PDF de la cotización en memoria."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # --- DIBUJAR PDF ---
    c.setFont("Helvetica-Bold", 16)
    c.drawString(inch, height - inch, "Cotización - Distribuidora de Agua")
    
    fecha_actual = datetime.now().strftime("%d de %B de %Y")
    c.setFont("Helvetica", 10)
    c.drawString(inch, height - inch - 20, "Fecha: " + fecha_actual)
    c.drawString(inch, height - inch - 40, "Cliente: " + nombre_cliente)
    
    c.line(inch, height - inch - 60, width - inch, height - inch - 60)
    
    # Tabla de productos
    y_pos = height - inch - 90
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch, y_pos, "Producto")
    c.drawString(inch * 4.5, y_pos, "Cantidad")
    c.drawString(inch * 5.5, y_pos, "P. Unitario")
    c.drawString(inch * 6.5, y_pos, "Subtotal")
    c.setFont("Helvetica", 10)
    y_pos -= 20
    
    for item in cotizacion_actual:
        c.drawString(inch, y_pos, item["nombre"])
        c.drawString(inch * 4.5, y_pos, str(item["cantidad"]))
        c.drawString(inch * 5.5, y_pos, f"${item['precio_unitario']:,.2f}")
        c.drawString(inch * 6.5, y_pos, f"${item['subtotal']:,.2f}")
        y_pos -= 20
    
    c.line(inch, y_pos + 10, width - inch, y_pos + 10)
    
    # Totales
    y_pos -= 20
    c.setFont("Helvetica", 10)
    c.drawString(inch * 5.5, y_pos, "Subtotal:")
    c.drawString(inch * 6.5, y_pos, f"${totales['subtotal_antes_iva']:,.2f}")
    y_pos -= 20
    c.drawString(inch * 5.5, y_pos, "IVA (16%):")
    c.drawString(inch * 6.5, y_pos, f"${totales['iva']:,.2f}")
    y_pos -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(inch * 5.5, y_pos, "Total:")
    c.drawString(inch * 6.5, y_pos, f"${totales['gran_total']:,.2f}")
    
    c.save()
    buffer.seek(0)
    return buffer

# --- Interfaz de la Aplicación Web ---

st.set_page_config(page_title="Cotizador de Agua", layout="wide")

# Inicializar estado de la sesión para guardar la cotización
if 'cotizacion_actual' not in st.session_state:
    st.session_state.cotizacion_actual = []

# Cargar productos
productos = cargar_productos()

# Layout de la app en dos columnas
col1, col2 = st.columns([1, 1.5])

# --- Columna Izquierda: Controles ---
with col1:
    try:
        st.image("logo.png", width=250)
    except:
        st.title("💧 Cotizador")
    
    st.markdown("### Datos de la Cotización")
    nombre_cliente = st.text_input("Nombre del Cliente", placeholder="Escribe el nombre del cliente aquí")
    
    st.markdown("### Agregar Producto")
    
    if not productos:
        st.warning("No hay productos para seleccionar. Edita tu archivo 'productos.json'.")
    else:
        nombres_productos = [p["nombre"] for p in productos]
        producto_seleccionado_nombre = st.selectbox("Producto:", nombres_productos)
        
        cantidad = st.number_input("Cantidad (cajas):", min_value=1, value=1)
        
        tipo_precio = st.radio("Tipo de Precio:", ["Minorista", "Mayorista"], horizontal=True)
        
        precio_unitario = 0
        producto_actual = next(p for p in productos if p["nombre"] == producto_seleccionado_nombre)

        if tipo_precio == "Minorista":
            precio_unitario = producto_actual["precio_minorista_iva"]
        else:
            margen = st.number_input("Margen de Ganancia (%):", min_value=0.0, value=25.0, step=1.0)
            costo_sin_iva = producto_actual["costo_distribuidor_iva"] / IVA_FACTOR
            precio_unitario = (costo_sin_iva * (1 + margen / 100)) * IVA_FACTOR
        
        st.info(f"Precio por caja: ${precio_unitario:,.2f}")

        if st.button("Agregar a la Cotización", use_container_width=True, type="primary"):
            subtotal = cantidad * precio_unitario
            item = {
                "nombre": producto_actual["nombre"],
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "subtotal": subtotal
            }
            st.session_state.cotizacion_actual.append(item)
            st.success(f"¡{producto_actual['nombre']} agregado!")

# --- Columna Derecha: Resumen ---
with col2:
    st.markdown("### Resumen de Cotización")
    
    if not st.session_state.cotizacion_actual:
        st.info("Añade productos desde el panel de la izquierda para empezar.")
    else:
        # Usar Pandas para crear una tabla
        df = pd.DataFrame(st.session_state.cotizacion_actual)
        df_display = df.rename(columns={
            "nombre": "Producto", "cantidad": "Cantidad",
            "precio_unitario": "P. Unitario", "subtotal": "Subtotal"
        })
        # Formatear columnas de moneda
        df_display["P. Unitario"] = df_display["P. Unitario"].map("${:,.2f}".format)
        df_display["Subtotal"] = df_display["Subtotal"].map("${:,.2f}".format)
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Calcular totales
        gran_total = sum(item['subtotal'] for item in st.session_state.cotizacion_actual)
        subtotal_antes_iva = gran_total / IVA_FACTOR
        iva = gran_total - subtotal_antes_iva
        
        totales = {
            "subtotal_antes_iva": subtotal_antes_iva,
            "iva": iva,
            "gran_total": gran_total
        }

        st.markdown("---")
        
        sub_col1, sub_col2, sub_col3 = st.columns(3)
        with sub_col1:
            st.metric("Subtotal", f"${subtotal_antes_iva:,.2f}")
        with sub_col2:
            st.metric("IVA (16%)", f"${iva:,.2f}")
        with sub_col3:
            st.metric("TOTAL", f"${gran_total:,.2f}")
        
        st.markdown("---")

        # Botones de acción
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("Limpiar Cotización", use_container_width=True):
                st.session_state.cotizacion_actual = []
                st.rerun() 

        with action_col2:
            if nombre_cliente and st.session_state.cotizacion_actual:
                pdf_buffer = generar_pdf(nombre_cliente, st.session_state.cotizacion_actual, totales)
                nombre_archivo = f"cotizacion_{nombre_cliente.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
                st.download_button(
                    label="Descargar PDF",
                    data=pdf_buffer,
                    file_name=nombre_archivo,
                    mime="application/pdf",
                    use_container_width=True
                )
