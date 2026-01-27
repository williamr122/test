
# ==============================================================================
# 1. CONFIGURACIÓN Y CONEXIÓN (PON TUS CLAVES AQUÍ)
# ==============================================================================
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
import io
import plotly.express as px
from dateparser.search import search_dates
import re
from supabase import create_client, Client

# ==============================================================================
# 1. CONFIGURACIÓN Y CONEXIÓN
# ==============================================================================

SUPABASE_URL = "https://lzwwztbjregufgqvftsi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx6d3d6dGJqcmVndWZncXZmdHNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk1NDE3NDIsImV4cCI6MjA4NTExNzc0Mn0.Y95yaYPm6wm-d_6vez_HWyCo9Gy4YEwDL4EZFTD2zBk"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except:
    st.error("⚠️ Error conectando a Supabase. Revisa tus claves URL y KEY en el código.")
    st.stop()

st.set_page_config(page_title="Billi Burgers ERP", page_icon="🍔", layout="wide")

# ==============================================================================
# 2. ESTILOS CSS
# ==============================================================================
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #E0E0E0; }
    h1, h2, h3 {
        font-family: 'Segoe UI', sans-serif;
        color: #FFD700 !important;
        text-shadow: 0px 0px 10px rgba(255, 215, 0, 0.2);
    }
    .stButton>button {
        background: linear-gradient(135deg, #1F1F1F 0%, #333333 100%);
        color: #FFD700;
        border: 1px solid #FFD700;
        border-radius: 8px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background: #FFD700;
        color: #000;
    }
    div[data-testid="stMetric"] {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #FFD700;
    }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 3. FUNCIONES DE BASE DE DATOS
# ==============================================================================
def fetch_data(table, start_date=None, end_date=None):
    query = supabase.table(table).select("*")
    if start_date and end_date:
        query = query.gte("fecha", start_date).lte("fecha", end_date)
    response = query.execute()
    return pd.DataFrame(response.data)

def insert_data(table, data):
    try:
        supabase.table(table).insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def upsert_data(table, df_edited):
    records = df_edited.to_dict('records')
    try:
        supabase.table(table).upsert(records).execute()
        return True
    except Exception as e:
        st.error(f"Error al actualizar: {e}")
        return False

def delete_data(table, id_valor):
    try:
        supabase.table(table).delete().eq("id", id_valor).execute()
        return True
    except Exception as e:
        st.error(f"Error al borrar: {e}")
        return False

# ==============================================================================
# 4. INTELIGENCIA ARTIFICIAL
# ==============================================================================
def procesar_audio(audio_bytes):
    r = sr.Recognizer()
    audio_file = io.BytesIO(audio_bytes)
    try:
        with sr.AudioFile(audio_file) as source:
            audio_data = r.record(source)
            return r.recognize_google(audio_data, language="es-EC").lower()
    except: return "Error"

def interpretar_intencion(texto):
    numeros = re.findall(r'\d+[.,]?\d*', texto)
    monto = float(numeros[0].replace(',', '.')) if numeros else 0.0
    tipo = "Ingreso" if any(p in texto for p in ['vendí', 'venta', 'ingreso']) else "Gasto"
    categoria = "Varios"
    if tipo == "Gasto":
        if "empleado" in texto or "sueldo" in texto: categoria = "Sueldos"
        elif "servicio" in texto or "luz" in texto: categoria = "Servicios"
        else: categoria = "Compras"
    fecha_str = datetime.today().strftime('%Y-%m-%d')
    try:
        settings = {'DATE_ORDER': 'DMY', 'PREFER_DATES_FROM': 'past'}
        match = search_dates(texto, languages=['es'], settings=settings)
        if match: fecha_str = match[-1][1].strftime('%Y-%m-%d')
    except: pass
    return {"tipo": tipo, "categoria": categoria, "monto": monto, "fecha": fecha_str, "detalle": texto}

# ==============================================================================
# 5. INTERFAZ PRINCIPAL
# ==============================================================================
def main():
    with st.sidebar:
        st.header("🍔 MENÚ PRINCIPAL")
        st.markdown("---")
        # CORRECCIÓN 1: Agregamos etiqueta "Navegación" y usamos label_visibility="collapsed"
        menu = st.radio("Navegación", ["📊 Dashboard Ejecutivo", "💰 Transacciones", "⚙️ Configuración (CRUD)", "🎙️ Asistente IA"], label_visibility="collapsed")
        st.markdown("---")
        st.caption("Sistema v3.0 - Cloud Connect")

    # 1. DASHBOARD
    if menu == "📊 Dashboard Ejecutivo":
        st.title("Tablero de Control Financiero")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: f_ini = st.date_input("📅 Desde", datetime.today().replace(day=1))
        with c2: f_fin = st.date_input("📅 Hasta", datetime.today())
        
        df = fetch_data("movimientos", f_ini, f_fin)
        
        if not df.empty:
            ing = df[df['tipo'] == 'Ingreso']['monto'].sum()
            gas = df[df['tipo'] == 'Gasto']['monto'].sum()
            bal = ing - gas
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Ingresos Totales", f"${ing:,.2f}", "Ventas")
            m2.metric("Gastos Totales", f"${gas:,.2f}", "-Salidas", delta_color="inverse")
            m3.metric("Utilidad Neta", f"${bal:,.2f}", "Ganancia")
            
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("Evolución Financiera")
                df_trend = df.groupby(['fecha', 'tipo'])['monto'].sum().reset_index()
                fig = px.bar(df_trend, x='fecha', y='monto', color='tipo', 
                             color_discrete_map={'Ingreso':'#00CC96', 'Gasto':'#EF553B'},
                             barmode='group', template="plotly_dark")
                # CORRECCIÓN 2: width="stretch" (Aunque plotly a veces usa use_container_width, lo dejaremos para evitar el warning específico si streamlit lo intercepta)
                st.plotly_chart(fig, use_container_width=True) 
            
            with g2:
                st.subheader("Desglose de Gastos")
                df_g = df[df['tipo'] == 'Gasto']
                if not df_g.empty:
                    fig2 = px.pie(df_g, values='monto', names='categoria', hole=0.4, 
                                  template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("No hay gastos registrados.")
        else:
            st.info("No hay datos para las fechas seleccionadas.")

    # 2. TRANSACCIONES
    elif menu == "💰 Transacciones":
        st.title("Gestión de Operaciones")
        tab_reg, tab_ver = st.tabs(["➕ Nueva Transacción", "📂 Historial"])
        
        with tab_reg:
            st.subheader("Registrar Nuevo Movimiento")
            tipo_trx = st.radio("Tipo de Operación", ["Ingreso", "Gasto"], horizontal=True)
            
            with st.form("form_trx"):
                c1, c2 = st.columns(2)
                fecha = c1.date_input("Fecha", datetime.today())
                monto = c2.number_input("Monto ($)", min_value=0.01)
                
                cat = "General"
                ben = "General"
                det = ""
                
                if tipo_trx == "Ingreso":
                    cat = "Venta"
                    det = st.text_input("Detalle")
                else:
                    subtipo = st.selectbox("Clasificación", ["Compras (Insumos)", "Servicios", "Sueldos"])
                    cat = subtipo
                    if subtipo == "Compras (Insumos)":
                        df_p = fetch_data("proveedores")
                        l_p = df_p['empresa'].tolist() if not df_p.empty else []
                        if st.radio("Prov", ["Existente", "Nuevo"], horizontal=True, label_visibility="collapsed") == "Existente":
                            ben = st.selectbox("Proveedor", l_p) if l_p else st.warning("Crea proveedores primero")
                        else:
                            ben = st.text_input("Nuevo Proveedor")
                        det = st.text_input("Detalle Compra")
                    elif subtipo == "Sueldos":
                        df_e = fetch_data("empleados")
                        l_e = df_e['nombre'].tolist() if not df_e.empty else []
                        if st.radio("Emp", ["Existente", "Nuevo"], horizontal=True, label_visibility="collapsed") == "Existente":
                            ben = st.selectbox("Empleado", l_e) if l_e else st.warning("Crea empleados primero")
                        else:
                            ben = st.text_input("Nuevo Empleado")
                        det = st.text_input("Concepto")
                    else:
                        ben = st.text_input("Entidad")
                        det = st.text_input("Descripción")

                # CORRECCIÓN 3: width="stretch" en botón
                if st.form_submit_button("💾 Guardar Transacción", width="stretch"):
                    datos = {"fecha": str(fecha), "tipo": tipo_trx, "categoria": cat, "beneficiario": str(ben), "detalle": det, "monto": monto}
                    if insert_data("movimientos", datos):
                        st.success("Registrado.")
                        st.rerun()

        with tab_ver:
            df_hist = fetch_data("movimientos")
            if not df_hist.empty:
                df_hist = df_hist.sort_values(by="fecha", ascending=False)
                s1, s2, s3 = st.tabs(["🟢 Ingresos", "🔴 Gastos", "📑 Todo"])
                # CORRECCIÓN 4: width="stretch" en dataframes
                with s1: st.dataframe(df_hist[df_hist['tipo'] == 'Ingreso'], width="stretch", hide_index=True)
                with s2: st.dataframe(df_hist[df_hist['tipo'] == 'Gasto'], width="stretch", hide_index=True)
                with s3: st.dataframe(df_hist, width="stretch", hide_index=True)

    # 3. CONFIGURACIÓN
    elif menu == "⚙️ Configuración (CRUD)":
        st.title("Maestros del Sistema")
        t_e, t_p = st.tabs(["👥 Empleados", "🚚 Proveedores"])
        
        with t_e:
            df_e = fetch_data("empleados")
            # CORRECCIÓN 5: width="stretch" en editor
            df_e_ed = st.data_editor(df_e, num_rows="dynamic", key="ed_emp", width="stretch")
            if st.button("💾 Guardar Empleados", width="stretch"):
                if upsert_data("empleados", df_e_ed): st.success("Guardado."); st.rerun()
            
            with st.expander("Borrar Empleado"):
                bid = st.number_input("ID Empleado", min_value=0, step=1)
                if st.button("Borrar ID", key="del_emp"):
                    if delete_data("empleados", bid): st.success("Borrado."); st.rerun()

        with t_p:
            df_p = fetch_data("proveedores")
            # CORRECCIÓN 6: width="stretch" en editor
            df_p_ed = st.data_editor(df_p, num_rows="dynamic", key="ed_prov", width="stretch")
            if st.button("💾 Guardar Proveedores", width="stretch"):
                if upsert_data("proveedores", df_p_ed): st.success("Guardado."); st.rerun()
            
            with st.expander("Borrar Proveedor"):
                pid = st.number_input("ID Proveedor", min_value=0, step=1)
                if st.button("Borrar ID", key="del_prov"):
                    if delete_data("proveedores", pid): st.success("Borrado."); st.rerun()

    # 4. IA
    elif menu == "🎙️ Asistente IA":
        st.title("Asistente de Voz")
        c_mic, _ = st.columns([1, 3])
        with c_mic:
            audio = mic_recorder(start_prompt="🔴 HABLAR", stop_prompt="⏹️ PROCESAR", format="wav", key="ia_mic")
        
        if audio:
            txt = procesar_audio(audio['bytes'])
            if txt != "Error":
                d = interpretar_intencion(txt)
                st.markdown(f"""
                <div style="padding:15px; background:#1E1E1E; border-left:5px solid #FFD700;">
                    <h3>Confirmar</h3>
                    <p>"{d['detalle']}"</p>
                    <hr>
                    <b>{d['tipo']}</b> | ${d['monto']}
                </div>
                """, unsafe_allow_html=True)
                if st.button("✅ Confirmar", width="stretch"):
                    dt = {"fecha": d['fecha'], "tipo": d['tipo'], "categoria": d['categoria'], "beneficiario": "Voz IA", "detalle": d['detalle'], "monto": d['monto']}
                    if insert_data("movimientos", dt): st.success("Guardado en Nube.")
            else: st.warning("No entendí.")

if __name__ == "__main__":
    main()