# -*- coding: utf-8 -*-
import sys
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, # <-- AÑADE QGridLayout Y QFrame AQUÍ
    QLabel, QComboBox, QRadioButton, QLineEdit, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout
)
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtCore import Qt, QSize

# --- Importaciones para PDF ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

IVA_FACTOR = 1.16
JSON_FILE = "productos.json"

# --- VENTANA DE CONFIGURACIÓN DE PRODUCTOS (Sin cambios visuales mayores) ---
class ConfiguracionDialog(QDialog):
    def __init__(self, productos, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Productos")
        self.setMinimumSize(600, 500)
        self.productos = productos
        
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Piezas", "Costo", "P. Minorista", "PVPS Caja"])
        self.table.selectionModel().selectionChanged.connect(self.fila_seleccionada)
        layout.addWidget(self.table)

        form_layout = QFormLayout()
        self.id_input = QLineEdit()
        self.id_input.setReadOnly(True)
        self.nombre_input = QLineEdit()
        self.piezas_input = QSpinBox()
        self.costo_input = QLineEdit()
        self.minorista_input = QLineEdit()
        self.pvps_input = QLineEdit()

        form_layout.addRow("ID:", self.id_input)
        form_layout.addRow("Nombre:", self.nombre_input)
        form_layout.addRow("Piezas/Caja:", self.piezas_input)
        form_layout.addRow("Costo Distribuidor:", self.costo_input)
        form_layout.addRow("Precio Minorista:", self.minorista_input)
        form_layout.addRow("PVPS Caja:", self.pvps_input)
        layout.addLayout(form_layout)
        
        buttons_layout = QHBoxLayout()
        self.add_update_button = QPushButton("Añadir/Actualizar")
        self.delete_button = QPushButton("Eliminar Seleccionado")
        self.clear_button = QPushButton("Limpiar Campos")
        buttons_layout.addWidget(self.add_update_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addWidget(self.clear_button)
        layout.addLayout(buttons_layout)

        self.add_update_button.clicked.connect(self.guardar_producto)
        self.delete_button.clicked.connect(self.eliminar_producto)
        self.clear_button.clicked.connect(self.limpiar_campos)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        self.cargar_tabla()

    def cargar_tabla(self):
        self.table.setRowCount(0)
        for p in self.productos:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(p["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(p["nombre"]))
            self.table.setItem(row, 2, QTableWidgetItem(str(p["piezas_por_caja"])))
            self.table.setItem(row, 3, QTableWidgetItem(str(p["costo_distribuidor_iva"])))
            self.table.setItem(row, 4, QTableWidgetItem(str(p["precio_minorista_iva"])))
            self.table.setItem(row, 5, QTableWidgetItem(str(p["pvps_caja"])))

    def fila_seleccionada(self, selected, deselected):
        if not selected.indexes(): return
        row = selected.indexes()[0].row()
        self.id_input.setText(self.table.item(row, 0).text())
        self.nombre_input.setText(self.table.item(row, 1).text())
        self.piezas_input.setValue(int(self.table.item(row, 2).text()))
        self.costo_input.setText(self.table.item(row, 3).text())
        self.minorista_input.setText(self.table.item(row, 4).text())
        self.pvps_input.setText(self.table.item(row, 5).text())

    def limpiar_campos(self):
        self.id_input.clear()
        self.nombre_input.clear()
        self.piezas_input.setValue(0)
        self.costo_input.clear()
        self.minorista_input.clear()
        self.pvps_input.clear()
        self.table.clearSelection()

    def guardar_producto(self):
        try:
            prod_id = self.id_input.text()
            nuevo_prod = {
                "nombre": self.nombre_input.text(),
                "piezas_por_caja": int(self.piezas_input.value()),
                "costo_distribuidor_iva": float(self.costo_input.text()),
                "precio_minorista_iva": float(self.minorista_input.text()),
                "pvps_caja": float(self.pvps_input.text())
            }
            if not nuevo_prod["nombre"]:
                QMessageBox.warning(self, "Error", "El nombre no puede estar vacío.")
                return

            if prod_id: # Actualizar
                prod_id = int(prod_id)
                for i, p in enumerate(self.productos):
                    if p["id"] == prod_id:
                        self.productos[i] = {"id": prod_id, **nuevo_prod}
                        break
            else: # Añadir nuevo
                new_id = max([p["id"] for p in self.productos] or [0]) + 1
                self.productos.append({"id": new_id, **nuevo_prod})
            
            self.cargar_tabla()
            self.limpiar_campos()
        except ValueError:
            QMessageBox.warning(self, "Error de Formato", "Asegúrese de que los campos de precio y costo sean números válidos.")

    def eliminar_producto(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Error", "Seleccione una fila para eliminar.")
            return
        
        row_index = selected_rows[0].row()
        prod_id = int(self.table.item(row_index, 0).text())
        self.productos = [p for p in self.productos if p["id"] != prod_id]
        self.cargar_tabla()
        self.limpiar_campos()


# --- VENTANA PRINCIPAL (CON DISEÑO MEJORADO) ---
class CalculadoraPreciosApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cotizacion_actual = []
        self.productos = self.cargar_productos()

        self.setWindowTitle("Sistema de Cotizaciones - Agua de Lourdes")
        self.setMinimumSize(850, 750)
        
        try:
            self.setWindowIcon(QIcon("app_icon.ico"))
        except FileNotFoundError:
            print("Advertencia: No se encontró 'app_icon.ico'.")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- Columna Izquierda: Controles ---
        controles_layout = QVBoxLayout()
        controles_layout.setSpacing(15)

        # Logo
        self.logo_label = QLabel()
        try:
            pixmap = QPixmap("logo.png")
            self.logo_label.setPixmap(pixmap.scaled(250, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except FileNotFoundError:
            print("Advertencia: No se encontró 'logo.png'.")
            self.logo_label.setText("Distribuidora de Agua")
            self.logo_label.setObjectName("logoTexto")
        
        controles_layout.addWidget(self.logo_label)

        # Botón de Configuración
        self.config_button = QPushButton(" Configurar Productos")
        try:
            self.config_button.setIcon(QIcon("config_icon.png"))
        except FileNotFoundError:
            print("Advertencia: No se encontró 'config_icon.png'.")
        self.config_button.setIconSize(QSize(20, 20))
        self.config_button.clicked.connect(self.abrir_configuracion)
        controles_layout.addWidget(self.config_button)

        # Resto de los controles...
        cliente_label = QLabel("Datos de la Cotización")
        cliente_label.setObjectName("titulo")
        self.nombre_cliente_input = QLineEdit()
        self.nombre_cliente_input.setPlaceholderText("Nombre del Cliente")
        
        product_label = QLabel("Agregar Producto")
        product_label.setObjectName("titulo")
        self.product_combo = QComboBox()
        self.actualizar_combo_productos()
        
        cantidad_layout = QHBoxLayout()
        cantidad_label = QLabel("Cantidad:")
        self.cantidad_spinbox = QSpinBox()
        self.cantidad_spinbox.setMinimum(1)
        self.cantidad_spinbox.setMaximum(999)
        cantidad_layout.addWidget(cantidad_label)
        cantidad_layout.addWidget(self.cantidad_spinbox)

        tipo_precio_label = QLabel("Tipo de Precio:")
        tipo_precio_label.setObjectName("subtitulo")
        self.minorista_radio = QRadioButton("Minorista")
        self.mayorista_radio = QRadioButton("Mayorista")
        self.minorista_radio.setChecked(True)
        self.mayorista_radio.toggled.connect(lambda: self.margen_container.setVisible(self.mayorista_radio.isChecked()))

        self.margen_container = QWidget()
        margen_layout = QHBoxLayout(self.margen_container)
        margen_layout.setContentsMargins(0, 5, 0, 5)
        margen_label = QLabel("Margen (%):")
        self.margen_input = QLineEdit()
        self.margen_input.setPlaceholderText("Ej. 25")
        margen_layout.addWidget(margen_label)
        margen_layout.addWidget(self.margen_input)
        self.margen_container.setVisible(False)

        self.add_to_quote_button = QPushButton(" Agregar a la Cotización")
        try:
            self.add_to_quote_button.setIcon(QIcon("add_icon.png"))
        except FileNotFoundError:
            print("Advertencia: No se encontró 'add_icon.png'.")
        self.add_to_quote_button.setIconSize(QSize(18, 18))
        self.add_to_quote_button.clicked.connect(self.agregar_a_cotizacion)

        controles_layout.addWidget(cliente_label)
        controles_layout.addWidget(self.nombre_cliente_input)
        controles_layout.addSpacing(15)
        controles_layout.addWidget(product_label)
        controles_layout.addWidget(self.product_combo)
        controles_layout.addLayout(cantidad_layout)
        controles_layout.addWidget(tipo_precio_label)
        controles_layout.addWidget(self.minorista_radio)
        controles_layout.addWidget(self.mayorista_radio)
        controles_layout.addWidget(self.margen_container)
        controles_layout.addSpacing(10)
        controles_layout.addWidget(self.add_to_quote_button)
        controles_layout.addStretch()

        # Columna Derecha (Tabla y Totales)
        cotizacion_layout = QVBoxLayout()
        tabla_label = QLabel("Resumen de Cotización")
        tabla_label.setObjectName("titulo")
        self.quote_table = QTableWidget()
        self.quote_table.setColumnCount(4)
        self.quote_table.setHorizontalHeaderLabels(["Producto", "Cantidad", "P. Unitario", "Subtotal"])
        self.quote_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.quote_table.verticalHeader().setVisible(False)
        self.quote_table.setShowGrid(False)
        
        totales_frame = QFrame()
        totales_frame.setObjectName("totalesFrame")
        totales_layout = QGridLayout(totales_frame)
        self.subtotal_label = QLabel("Subtotal:")
        self.subtotal_valor = QLabel("$0.00")
        self.iva_label = QLabel("IVA (16%):")
        self.iva_valor = QLabel("$0.00")
        self.total_label = QLabel("Total:")
        self.total_label.setObjectName("totalLabel")
        self.total_valor = QLabel("$0.00")
        self.total_valor.setObjectName("totalValor")
        
        totales_layout.addWidget(self.subtotal_label, 0, 0, Qt.AlignmentFlag.AlignRight)
        totales_layout.addWidget(self.subtotal_valor, 0, 1)
        totales_layout.addWidget(self.iva_label, 1, 0, Qt.AlignmentFlag.AlignRight)
        totales_layout.addWidget(self.iva_valor, 1, 1)
        totales_layout.addWidget(self.total_label, 2, 0, Qt.AlignmentFlag.AlignRight)
        totales_layout.addWidget(self.total_valor, 2, 1)

        final_buttons_layout = QHBoxLayout()
        self.clear_quote_button = QPushButton(" Limpiar")
        try:
            self.clear_quote_button.setIcon(QIcon("clear_icon.png"))
        except FileNotFoundError:
            print("Advertencia: No se encontró 'clear_icon.png'.")
        self.clear_quote_button.setIconSize(QSize(18, 18))
        self.generate_pdf_button = QPushButton(" Generar PDF")
        try:
            self.generate_pdf_button.setIcon(QIcon("pdf_icon.png"))
        except FileNotFoundError:
            print("Advertencia: No se encontró 'pdf_icon.png'.")
        self.generate_pdf_button.setIconSize(QSize(18, 18))
        self.generate_pdf_button.setObjectName("primaryButton")
        self.clear_quote_button.clicked.connect(self.limpiar_cotizacion)
        self.generate_pdf_button.clicked.connect(self.generar_pdf)
        final_buttons_layout.addWidget(self.clear_quote_button)
        final_buttons_layout.addWidget(self.generate_pdf_button)

        cotizacion_layout.addWidget(tabla_label)
        cotizacion_layout.addWidget(self.quote_table)
        cotizacion_layout.addWidget(totales_frame)
        cotizacion_layout.addLayout(final_buttons_layout)

        main_layout.addLayout(controles_layout, 1)
        main_layout.addLayout(cotizacion_layout, 2)
        
        self.set_stylesheet()
    
    def cargar_productos(self):
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            QMessageBox.warning(self, "Error", f"No se pudo cargar '{JSON_FILE}'. Se usará una lista vacía.")
            return []

    def guardar_productos_a_json(self):
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.productos, f, indent=4, ensure_ascii=False)

    def actualizar_combo_productos(self):
        self.product_combo.clear()
        for p in self.productos:
            self.product_combo.addItem(p["nombre"], userData=p)

    def abrir_configuracion(self):
        dialog = ConfiguracionDialog(self.productos.copy(), self)
        if dialog.exec():
            self.productos = dialog.productos
            self.guardar_productos_a_json() # <-- LÍNEA CORRECTA
            self.actualizar_combo_productos()
            QMessageBox.information(self, "Éxito", "La lista de productos ha sido actualizada.")
        
    def agregar_a_cotizacion(self):
        producto = self.product_combo.currentData()
        if not producto: return
        
        cantidad = self.cantidad_spinbox.value()
        precio_unitario = 0
        
        if self.minorista_radio.isChecked():
            precio_unitario = producto["precio_minorista_iva"]
        else: # Mayorista
            try:
                margen = float(self.margen_input.text())
                costo_sin_iva = producto["costo_distribuidor_iva"] / IVA_FACTOR
                precio_unitario = (costo_sin_iva * (1 + margen / 100)) * IVA_FACTOR
            except ValueError:
                QMessageBox.warning(self, "Error", "El margen debe ser un número válido.")
                return

        subtotal = cantidad * precio_unitario
        item = { "nombre": producto["nombre"], "cantidad": cantidad, "precio_unitario": precio_unitario, "subtotal": subtotal }
        self.cotizacion_actual.append(item)
        self.actualizar_tabla_y_totales()

    def actualizar_tabla_y_totales(self):
        self.quote_table.setRowCount(0)
        gran_total = sum(item['subtotal'] for item in self.cotizacion_actual)
        
        for item in self.cotizacion_actual:
            row = self.quote_table.rowCount()
            self.quote_table.insertRow(row)
            self.quote_table.setItem(row, 0, QTableWidgetItem(item["nombre"]))
            self.quote_table.setItem(row, 1, QTableWidgetItem(str(item["cantidad"])))
            self.quote_table.setItem(row, 2, QTableWidgetItem(f"${item['precio_unitario']:,.2f}"))
            self.quote_table.setItem(row, 3, QTableWidgetItem(f"${item['subtotal']:,.2f}"))

        subtotal_antes_iva = gran_total / IVA_FACTOR
        iva = gran_total - subtotal_antes_iva
        self.subtotal_valor.setText(f"${subtotal_antes_iva:,.2f}")
        self.iva_valor.setText(f"${iva:,.2f}")
        self.total_valor.setText(f"${gran_total:,.2f}")

    def limpiar_cotizacion(self):
        self.cotizacion_actual = []
        self.nombre_cliente_input.clear()
        self.actualizar_tabla_y_totales()
        
    def generar_pdf(self):
        if not self.cotizacion_actual:
            QMessageBox.warning(self, "Cotización Vacía", "No hay productos para generar un PDF.")
            return
        nombre_cliente = self.nombre_cliente_input.text()
        if not nombre_cliente:
            QMessageBox.warning(self, "Falta Cliente", "Por favor, ingrese el nombre del cliente.")
            return

        fecha_actual = datetime.now().strftime("%d de %B de %Y")
        nombre_archivo = f"cotizacion_{nombre_cliente.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        c = canvas.Canvas(nombre_archivo, pagesize=letter)
        # (El código para dibujar el PDF es igual al de la versión anterior)
        width, height = letter
        c.setFont("Helvetica-Bold", 16)
        c.drawString(inch, height - inch, "Cotización - Distribuidora de Agua")
        c.setFont("Helvetica", 10)
        c.drawString(inch, height - inch - 20, "Fecha: " + fecha_actual)
        c.drawString(inch, height - inch - 40, "Cliente: " + nombre_cliente)
        c.line(inch, height - inch - 60, width - inch, height - inch - 60)
        
        y_pos = height - inch - 90
        c.setFont("Helvetica-Bold", 10)
        c.drawString(inch, y_pos, "Producto")
        c.drawString(inch * 4.5, y_pos, "Cantidad")
        c.drawString(inch * 5.5, y_pos, "Precio Unit.")
        c.drawString(inch * 6.5, y_pos, "Subtotal")
        c.setFont("Helvetica", 10)
        y_pos -= 20
        
        for item in self.cotizacion_actual:
            c.drawString(inch, y_pos, item["nombre"])
            c.drawString(inch * 4.5, y_pos, str(item["cantidad"]))
            c.drawString(inch * 5.5, y_pos, f"${item['precio_unitario']:,.2f}")
            c.drawString(inch * 6.5, y_pos, f"${item['subtotal']:,.2f}")
            y_pos -= 20
        
        c.line(inch, y_pos + 10, width - inch, y_pos + 10)
        
        total_final = float(self.total_valor.text().replace("$", "").replace(",", ""))
        subtotal_final = float(self.subtotal_valor.text().replace("$", "").replace(",", ""))
        iva_final = float(self.iva_valor.text().replace("$", "").replace(",", ""))
        
        y_pos -= 20
        c.setFont("Helvetica", 10)
        c.drawString(inch * 5.5, y_pos, "Subtotal:")
        c.drawString(inch * 6.5, y_pos, f"${subtotal_final:,.2f}")
        y_pos -= 20
        c.drawString(inch * 5.5, y_pos, "IVA (16%):")
        c.drawString(inch * 6.5, y_pos, f"${iva_final:,.2f}")
        y_pos -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(inch * 5.5, y_pos, "Total:")
        c.drawString(inch * 6.5, y_pos, f"${total_final:,.2f}")
        
        c.save()
        QMessageBox.information(self, "PDF Generado", f"El archivo '{nombre_archivo}' se ha guardado exitosamente.")


    def set_stylesheet(self):
        self.setStyleSheet("""
            QWidget { 
                font-family: 'Segoe UI', Arial, sans-serif; 
                font-size: 10pt; 
            }
            QMainWindow { background-color: #2c3e50; }
            
            /* --- Títulos y Labels --- */
            QLabel#titulo { 
                font-weight: bold; 
                font-size: 14pt; 
                color: #1a5276; 
                margin-bottom: 5px;
            }
            QLabel#subtitulo {
                font-size: 9pt;
                font-weight: bold;
                color: #566573;
                margin-top: 8px;
            }
            QLabel#logoTexto {
                font-size: 20pt;
                font-weight: bold;
                color: #1a5276;
            }

            /* --- Controles de Entrada --- */
            QLineEdit, QComboBox, QSpinBox { 
                padding: 10px; 
                border: 0.5px solid #DDE1E6; 
                border-radius: 8px; 
                background-color: #2c3e50;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus { 
                border: 1px solid #3498db; 
            }
            QComboBox::drop-down { border: none; }
            
            /* --- Botones --- */
            QPushButton { 
                background-color: #FFFFFF; 
                color: #2c3e50;
                border: 1px solid #DDE1E6; 
                padding: 10px; 
                border-radius: 8px;
                text-align: left;
                padding-left: 12px;
            }
            QPushButton:hover { background-color: #EAECEE; }

            /* Botón principal con nuevo estilo de alto contraste */
            QPushButton#primaryButton { 
                background-color: #D5F5E3; /* Un verde claro y llamativo */
                color: #186A3B; /* Texto verde oscuro */
                border: 1px solid #ABEBC6;
                font-weight: bold;
            }
            QPushButton#primaryButton:hover { 
                background-color: #ABEBC6; /* Versión más oscura para el hover */
            }

            /* --- Tabla --- */
            QTableWidget { 
                border: 1px solid #DDE1E6;
                border-radius: 8px;
                gridline-color: #EAECEE;
                background-color: #2c3e50;
            }
            QHeaderView::section {
                background-color: #EAECEE;
                padding: 8px;
                border: none;
                font-weight: bold;
                color: #566573;
            }

            /* --- Totales --- */
            QFrame#totalesFrame {
                border: none;
            }
            QLabel#totalLabel { font-weight: bold; font-size: 13pt; color: #2c3e50;}
            QLabel#totalValor { font-weight: bold; font-size: 16pt; color: #16a085;}
        """)

    def cargar_productos(self):
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            QMessageBox.warning(self, "Error", f"No se pudo cargar '{JSON_FILE}'. Se usará una lista vacía.")
            return []

    def guardar_productos_a_json(self, productos):
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(productos, f, indent=4, ensure_ascii=False)

    def actualizar_combo_productos(self):
        self.product_combo.clear()
        for p in self.productos:
            self.product_combo.addItem(p["nombre"], userData=p)

    def abrir_configuracion(self):
        dialog = ConfiguracionDialog(self.productos.copy(), self) # Pasamos una copia
        if dialog.exec():
            self.productos = dialog.productos
            self.guardar_productos_a_json(self.productos)
            self.actualizar_combo_productos()
            QMessageBox.information(self, "Éxito", "La lista de productos ha sido actualizada.")
    
    def agregar_a_cotizacion(self):
        producto = self.product_combo.currentData()
        if not producto: return
        
        cantidad = self.cantidad_spinbox.value()
        precio_unitario = 0
        
        if self.minorista_radio.isChecked():
            precio_unitario = producto["precio_minorista_iva"]
        else: # Mayorista
            try:
                margen = float(self.margen_input.text())
                costo_sin_iva = producto["costo_distribuidor_iva"] / IVA_FACTOR
                precio_unitario = (costo_sin_iva * (1 + margen / 100)) * IVA_FACTOR
            except (ValueError, TypeError):
                QMessageBox.warning(self, "Error de Margen", "El margen para precio mayorista debe ser un número válido.")
                return

        subtotal = cantidad * precio_unitario
        item = { "nombre": producto["nombre"], "cantidad": cantidad, "precio_unitario": precio_unitario, "subtotal": subtotal }
        self.cotizacion_actual.append(item)
        self.actualizar_tabla_y_totales()

    def actualizar_tabla_y_totales(self):
        self.quote_table.setRowCount(0)
        gran_total = sum(item['subtotal'] for item in self.cotizacion_actual)
        
        for item in self.cotizacion_actual:
            row = self.quote_table.rowCount()
            self.quote_table.insertRow(row)
            self.quote_table.setItem(row, 0, QTableWidgetItem(item["nombre"]))
            self.quote_table.setItem(row, 1, QTableWidgetItem(str(item["cantidad"])))
            self.quote_table.setItem(row, 2, QTableWidgetItem(f"${item['precio_unitario']:,.2f}"))
            self.quote_table.setItem(row, 3, QTableWidgetItem(f"${item['subtotal']:,.2f}"))

        subtotal_antes_iva = gran_total / IVA_FACTOR
        iva = gran_total - subtotal_antes_iva
        self.subtotal_valor.setText(f"${subtotal_antes_iva:,.2f}")
        self.iva_valor.setText(f"${iva:,.2f}")
        self.total_valor.setText(f"${gran_total:,.2f}")

    def limpiar_cotizacion(self):
        self.cotizacion_actual = []
        self.nombre_cliente_input.clear()
        self.actualizar_tabla_y_totales()
        
    def generar_pdf(self):
        if not self.cotizacion_actual:
            QMessageBox.warning(self, "Cotización Vacía", "No hay productos para generar un PDF.")
            return
        nombre_cliente = self.nombre_cliente_input.text()
        if not nombre_cliente:
            QMessageBox.warning(self, "Falta Cliente", "Por favor, ingrese el nombre del cliente.")
            return

        fecha_actual = datetime.now().strftime("%d de %B de %Y")
        nombre_archivo = f"cotizacion_{nombre_cliente.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        c = canvas.Canvas(nombre_archivo, pagesize=letter)
        width, height = letter
        
        # --- DIBUJAR PDF ---
        c.setFont("Helvetica-Bold", 16)
        c.drawString(inch, height - inch, "Cotización - Distribuidora de Agua")
        c.setFont("Helvetica", 10)
        c.drawString(inch, height - inch - 20, "Fecha: " + fecha_actual)
        c.drawString(inch, height - inch - 40, "Cliente: " + nombre_cliente)
        c.line(inch, height - inch - 60, width - inch, height - inch - 60)
        
        y_pos = height - inch - 90
        c.setFont("Helvetica-Bold", 10)
        c.drawString(inch, y_pos, "Producto")
        c.drawString(inch * 4.5, y_pos, "Cantidad")
        c.drawString(inch * 5.5, y_pos, "P. Unitario")
        c.drawString(inch * 6.5, y_pos, "Subtotal")
        c.setFont("Helvetica", 10)
        y_pos -= 20
        
        for item in self.cotizacion_actual:
            c.drawString(inch, y_pos, item["nombre"])
            c.drawString(inch * 4.5, y_pos, str(item["cantidad"]))
            c.drawString(inch * 5.5, y_pos, f"${item['precio_unitario']:,.2f}")
            c.drawString(inch * 6.5, y_pos, f"${item['subtotal']:,.2f}")
            y_pos -= 20
        
        c.line(inch, y_pos + 10, width - inch, y_pos + 10)
        
        total_final = float(self.total_valor.text().replace("$", "").replace(",", ""))
        subtotal_final = float(self.subtotal_valor.text().replace("$", "").replace(",", ""))
        iva_final = float(self.iva_valor.text().replace("$", "").replace(",", ""))
        
        y_pos -= 20
        c.setFont("Helvetica", 10)
        c.drawString(inch * 5.5, y_pos, "Subtotal:")
        c.drawString(inch * 6.5, y_pos, f"${subtotal_final:,.2f}")
        y_pos -= 20
        c.drawString(inch * 5.5, y_pos, "IVA (16%):")
        c.drawString(inch * 6.5, y_pos, f"${iva_final:,.2f}")
        y_pos -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(inch * 5.5, y_pos, "Total:")
        c.drawString(inch * 6.5, y_pos, f"${total_final:,.2f}")
        
        c.save()
        QMessageBox.information(self, "PDF Generado", f"El archivo '{nombre_archivo}' se ha guardado exitosamente.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalculadoraPreciosApp()
    window.show()
    sys.exit(app.exec())