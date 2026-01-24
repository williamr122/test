import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA (Estilo App Móvil) ---
st.set_page_config(
    page_title="Billi Burgers Manager",
    page_icon="🍔",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- MANEJO DE ARCHIVOS ---
FILE_INGRESOS = 'ingresos.csv'
FILE_GASTOS = 'gastos.csv'

def cargar_datos(archivo, columnas):
    if not os.path.exists(archivo):
        return pd.DataFrame(columns=columnas)
    return pd.read_csv(archivo)

def guardar_datos(df, archivo):
    df.to_csv(archivo, index=False)

def agregar_fila_total(df, col_suma):
    """Función auxiliar para agregar la fila de TOTAL al final de una tabla"""
    if df.empty:
        return df
    
    # Crear una fila de totales
    total_row = {col: '' for col in df.columns}
    total_row[df.columns[0]] = 'TOTAL GLOBAL'
    total_row[col_suma] = df[col_suma].sum()
    
    # Convertir a DataFrame y concatenar
    df_total = pd.DataFrame([total_row])
    return pd.concat([df, df_total], ignore_index=True)

# --- TÍTULO PRINCIPAL ---
st.title("🍔 Billi Burgers System")
st.markdown("---")

# --- MENÚ DE NAVEGACIÓN ---
menu = st.sidebar.radio("Navegación", ["📈 Dashboard (Resumen)", "💰 Registrar Ingreso", "💸 Registrar Gasto"], index=0)

# ==========================================
# 1. REGISTRAR INGRESO (VENTAS)
# ==========================================
if menu == "💰 Registrar Ingreso":
    st.header("Nueva Venta del Día")
    st.info("Registra aquí el cierre de caja diario.")
    
    with st.form("form_ventas", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.today())
        dia = fecha.strftime("%A") 
        monto = st.number_input("Monto Total Recaudado ($)", min_value=0.0, step=0.01, format="%.2f")
        notas = st.text_area("Observaciones (Ej: Lluvia, Feriado)", height=80)
        
        # CORRECCIÓN AQUÍ: width="stretch"
        btn_guardar = st.form_submit_button("💾 Guardar Venta", width="stretch")
        
        if btn_guardar:
            if monto > 0:
                cols = ['Fecha', 'Dia', 'Monto', 'Notas']
                df = cargar_datos(FILE_INGRESOS, cols)
                nuevo = pd.DataFrame([{'Fecha': fecha, 'Dia': dia, 'Monto': monto, 'Notas': notas}])
                df = pd.concat([df, nuevo], ignore_index=True)
                guardar_datos(df, FILE_INGRESOS)
                st.success("✅ ¡Venta registrada exitosamente!")
            else:
                st.error("⚠️ El monto debe ser mayor a 0")

# ==========================================
# 2. REGISTRAR GASTO (COMPRAS/NÓMINA)
# ==========================================
elif menu == "💸 Registrar Gasto":
    st.header("Registrar Salida de Dinero")
    
    tipo_gasto = st.selectbox("¿Qué tipo de gasto es?", ["🛒 Insumos/Compras", "👷 Nómina (Empleados)", "💡 Servicios/Otros"])
    
    with st.form("form_gastos", clear_on_submit=True):
        fecha_gasto = st.date_input("Fecha", datetime.today())
        
        detalle = ""
        if tipo_gasto == "👷 Nómina (Empleados)":
            detalle = st.text_input("Nombre del Empleado")
            etiqueta_monto = "Monto a Pagar ($)"
        elif tipo_gasto == "🛒 Insumos/Compras":
            detalle = st.text_input("¿Qué se compró? (Ej: 20lbs Carne)")
            etiqueta_monto = "Costo de la Compra ($)"
        else:
            detalle = st.text_input("Descripción del Gasto")
            etiqueta_monto = "Monto ($)"
            
        monto_gasto = st.number_input(etiqueta_monto, min_value=0.0, step=0.01, format="%.2f")
        
        # CORRECCIÓN AQUÍ: width="stretch"
        btn_gasto = st.form_submit_button("🔻 Registrar Gasto", width="stretch")
        
        if btn_gasto:
            if monto_gasto > 0 and detalle != "":
                cols = ['Fecha', 'Categoria', 'Detalle', 'Monto']
                df = cargar_datos(FILE_GASTOS, cols)
                nuevo = pd.DataFrame([{'Fecha': fecha_gasto, 'Categoria': tipo_gasto, 'Detalle': detalle, 'Monto': monto_gasto}])
                df = pd.concat([df, nuevo], ignore_index=True)
                guardar_datos(df, FILE_GASTOS)
                st.success(f"✅ Gasto '{detalle}' registrado.")
            else:
                st.warning("⚠️ Completa todos los campos.")

# ==========================================
# 3. DASHBOARD (RESUMEN)
# ==========================================
elif menu == "📈 Dashboard (Resumen)":
    st.subheader("📊 Estado Financiero")
    
    cols_ing = ['Fecha', 'Dia', 'Monto', 'Notas']
    cols_gas = ['Fecha', 'Categoria', 'Detalle', 'Monto']
    
    df_i = cargar_datos(FILE_INGRESOS, cols_ing)
    df_g = cargar_datos(FILE_GASTOS, cols_gas)
    
    total_ing = df_i['Monto'].sum() if not df_i.empty else 0.0
    total_gas = df_g['Monto'].sum() if not df_g.empty else 0.0
    balance = total_ing - total_gas
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Ingresos", f"${total_ing:,.2f}")
    col2.metric("💸 Gastos", f"${total_gas:,.2f}")
    col3.metric("🏦 Ganancia Real", f"${balance:,.2f}", delta=f"{balance:,.2f}")
    
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📂 Detalle de INGRESOS", "📂 Detalle de GASTOS"])
    
    with tab1:
        if not df_i.empty:
            st.caption("Historial de ventas registradas")
            df_i_show = agregar_fila_total(df_i, 'Monto')
            # CORRECCIÓN AQUÍ: width="stretch"
            st.dataframe(df_i_show, width="stretch", hide_index=True)
        else:
            st.info("No hay ventas registradas aún.")
            
    with tab2:
        if not df_g.empty:
            st.caption("Historial de gastos registrados")
            df_g_show = agregar_fila_total(df_g, 'Monto')
            # CORRECCIÓN AQUÍ: width="stretch"
            st.dataframe(df_g_show, width="stretch", hide_index=True)
        else:
            st.info("No hay gastos registrados aún.")