import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Billi Burgers ERP",
    page_icon="🍔",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { color: #FFD700 !important; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .success-box { padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIÓN DE ARCHIVOS (BASE DE DATOS) ---
FILES = {
    'ingresos': 'ingresos.csv',
    'gastos': 'gastos.csv',
    'empleados': 'config_empleados.csv',
    'proveedores': 'config_proveedores.csv'
}

def cargar_datos(tipo):
    archivo = FILES[tipo]
    if not os.path.exists(archivo):
        # Estructuras iniciales según el tipo de archivo
        if tipo == 'empleados': return pd.DataFrame(columns=['Nombre', 'Cargo', 'Sueldo_Base'])
        if tipo == 'proveedores': return pd.DataFrame(columns=['Empresa', 'Categoria', 'Contacto'])
        if tipo == 'ingresos': return pd.DataFrame(columns=['Fecha', 'Dia', 'Monto', 'Notas'])
        if tipo == 'gastos': return pd.DataFrame(columns=['Fecha', 'Categoria', 'Beneficiario', 'Detalle', 'Monto', 'Evidencia'])
        return pd.DataFrame()
    return pd.read_csv(archivo)

def guardar_datos(df, tipo):
    df.to_csv(FILES[tipo], index=False)

# --- INTERFAZ PRINCIPAL ---
st.title("🍔 Billi Burgers System")
st.caption("Sistema Integrado de Gestión Financiera v2.0")

# --- MENÚ LATERAL ---
menu = st.sidebar.radio("Menú Principal", 
    ["📊 Dashboard", "💰 Registrar Movimiento", "⚙️ Configuración (Admin)"], 
    index=0
)

# ==============================================================================
# 1. MÓDULO DE CONFIGURACIÓN (EMPLEADOS Y PROVEEDORES)
# ==============================================================================
if menu == "⚙️ Configuración (Admin)":
    st.header("⚙️ Maestros del Sistema")
    
    tab_emp, tab_prov = st.tabs(["👥 Gestionar Empleados", "truck: Gestionar Proveedores"])
    
    # --- PESTAÑA EMPLEADOS ---
    with tab_emp:
        st.subheader("Alta de Personal")
        with st.form("form_empleado", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nombre_emp = col1.text_input("Nombre Completo")
            cargo_emp = col2.selectbox("Cargo", ["Cocinero", "Mesero", "Cajero", "Limpieza", "Administrador"])
            sueldo_emp = st.number_input("Sueldo Base ($)", min_value=0.0, step=10.0)
            
            if st.form_submit_button("Guardar Empleado"):
                if nombre_emp:
                    df = cargar_datos('empleados')
                    nuevo = pd.DataFrame([{'Nombre': nombre_emp, 'Cargo': cargo_emp, 'Sueldo_Base': sueldo_emp}])
                    df = pd.concat([df, nuevo], ignore_index=True)
                    guardar_datos(df, 'empleados')
                    st.success(f"Empleado {nombre_emp} registrado.")
                else:
                    st.error("El nombre es obligatorio.")
        
        st.divider()
        st.write("📋 **Nómina Actual:**")
        st.dataframe(cargar_datos('empleados'), use_container_width=True)

    # --- PESTAÑA PROVEEDORES ---
    with tab_prov:
        st.subheader("Alta de Proveedores")
        with st.form("form_prov", clear_on_submit=True):
            empresa = st.text_input("Nombre del Local/Empresa (Ej: Carnicería Don Pepe)")
            cat_prov = st.selectbox("Categoría Principal", ["Carnes", "Lácteos/Quesos", "Verduras", "Bebidas", "Insumos Varios", "Servicios"])
            contacto = st.text_input("Teléfono/Contacto (Opcional)")
            
            if st.form_submit_button("Guardar Proveedor"):
                if empresa:
                    df = cargar_datos('proveedores')
                    nuevo = pd.DataFrame([{'Empresa': empresa, 'Categoria': cat_prov, 'Contacto': contacto}])
                    df = pd.concat([df, nuevo], ignore_index=True)
                    guardar_datos(df, 'proveedores')
                    st.success(f"Proveedor {empresa} registrado.")
        
        st.divider()
        st.write("📋 **Directorio de Proveedores:**")
        st.dataframe(cargar_datos('proveedores'), use_container_width=True)

# ==============================================================================
# 2. MÓDULO DE REGISTRO (OPERACIONES)
# ==============================================================================
elif menu == "💰 Registrar Movimiento":
    st.header("Operaciones Diarias")
    tipo_operacion = st.selectbox("¿Qué deseas registrar?", ["🟢 Ingreso (Venta)", "🔴 Gasto (Compra/Nómina)"])
    
    # --- REGISTRO DE VENTAS ---
    if "Ingreso" in tipo_operacion:
        with st.form("form_ingreso", clear_on_submit=True):
            fecha = st.date_input("Fecha", datetime.today())
            monto = st.number_input("Total Venta del Día ($)", min_value=0.0, format="%.2f")
            notas = st.text_area("Observaciones")
            
            if st.form_submit_button("Registrar Venta", use_container_width=True):
                df = cargar_datos('ingresos')
                nuevo = pd.DataFrame([{'Fecha': fecha, 'Dia': fecha.strftime("%A"), 'Monto': monto, 'Notas': notas}])
                df = pd.concat([df, nuevo], ignore_index=True)
                guardar_datos(df, 'ingresos')
                st.balloons()
                st.success("Venta registrada correctamente.")

    # --- REGISTRO DE GASTOS INTELIGENTE ---
    else:
        # Cargar listas para los selectbox
        df_emp = cargar_datos('empleados')
        lista_empleados = df_emp['Nombre'].tolist() if not df_emp.empty else []
        
        df_prov = cargar_datos('proveedores')
        lista_proveedores = df_prov['Empresa'].tolist() if not df_prov.empty else []
        
        categoria_gasto = st.radio("Tipo de Gasto", ["🛒 Compra a Proveedor", "👷 Pago de Nómina", "💡 Otros Gastos"], horizontal=True)
        
        with st.form("form_gasto", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            fecha_gasto = col_a.date_input("Fecha", datetime.today())
            
            beneficiario = "General"
            detalle = ""
            monto_sugerido = 0.0
            
            # Lógica Dinámica según Tipo
            if categoria_gasto == "👷 Pago de Nómina":
                if not lista_empleados:
                    st.error("⚠️ No hay empleados registrados. Ve a Configuración.")
                else:
                    beneficiario = st.selectbox("Seleccionar Empleado", lista_empleados)
                    # Buscar sueldo base automáticamente
                    sueldo_base = df_emp[df_emp['Nombre'] == beneficiario]['Sueldo_Base'].values[0]
                    st.info(f"Sueldo base registrado: ${sueldo_base}")
                    monto_sugerido = float(sueldo_base)
                    detalle = st.text_input("Detalle (Ej: Quincena 1, Bono)", value="Pago de Nómina")

            elif categoria_gasto == "🛒 Compra a Proveedor":
                if not lista_proveedores:
                    st.error("⚠️ No hay proveedores registrados. Ve a Configuración.")
                else:
                    beneficiario = st.selectbox("Seleccionar Proveedor", lista_proveedores)
                    # Mostrar categoría del proveedor
                    cat_prov = df_prov[df_prov['Empresa'] == beneficiario]['Categoria'].values[0]
                    st.caption(f"Categoría: {cat_prov}")
                    detalle = st.text_input("¿Qué se compró? (Ej: 20kg Lomo)", placeholder="Detalle de productos")

            else:
                beneficiario = st.text_input("Beneficiario/Lugar")
                detalle = st.text_input("Descripción")

            monto_final = col_b.number_input("Monto a Pagar ($)", min_value=0.0, value=monto_sugerido, step=0.01, format="%.2f")
            
            # EXTRA: Subida de Foto (Simulada para guardar nombre de archivo)
            archivo_evidencia = st.file_uploader("📷 Subir Foto de Recibo/Factura", type=['png', 'jpg', 'jpeg', 'pdf'])
            nombre_archivo = archivo_evidencia.name if archivo_evidencia else "No evidencia"

            if st.form_submit_button("Registrar Salida de Dinero", use_container_width=True):
                df = cargar_datos('gastos')
                nuevo = pd.DataFrame([{
                    'Fecha': fecha_gasto, 
                    'Categoria': categoria_gasto, 
                    'Beneficiario': beneficiario, 
                    'Detalle': detalle, 
                    'Monto': monto_final,
                    'Evidencia': nombre_archivo
                }])
                df = pd.concat([df, nuevo], ignore_index=True)
                guardar_datos(df, 'gastos')
                st.success(f"Gasto registrado: ${monto_final} a {beneficiario}")

# ==============================================================================
# 3. DASHBOARD ANALÍTICO
# ==============================================================================
elif menu == "📊 Dashboard":
    st.header("Estado Financiero Billi Burgers")
    
    df_i = cargar_datos('ingresos')
    df_g = cargar_datos('gastos')
    
    total_ing = df_i['Monto'].sum() if not df_i.empty else 0.0
    total_gas = df_g['Monto'].sum() if not df_g.empty else 0.0
    balance = total_ing - total_gas
    
    # KPIs Principales
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Ingresos Totales", f"${total_ing:,.2f}", delta="Ventas")
    kpi2.metric("Gastos Totales", f"${total_gas:,.2f}", delta="-Salidas", delta_color="inverse")
    kpi3.metric("Utilidad Neta", f"${balance:,.2f}", delta="Ganancia")
    
    st.divider()
    
    # Gráficas y Tablas
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Desglose de Gastos")
        if not df_g.empty:
            # Gráfica por Tipo de Gasto
            gastos_por_tipo = df_g.groupby("Categoria")["Monto"].sum()
            st.bar_chart(gastos_por_tipo, color="#FF4B4B")
            
            # Gráfica por Proveedor/Empleado (Top 5)
            st.caption("Top 5 Destinos del dinero:")
            top_beneficiarios = df_g.groupby("Beneficiario")["Monto"].sum().sort_values(ascending=False).head(5)
            st.bar_chart(top_beneficiarios)
        else:
            st.info("Registra gastos para ver gráficas.")
            
    with c2:
        st.subheader("Últimos Movimientos")
        if not df_g.empty:
            st.dataframe(df_g[['Fecha', 'Beneficiario', 'Monto']].tail(10).sort_index(ascending=False), hide_index=True)