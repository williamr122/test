
# ==============================================================================
# 1. CONFIGURACIÓN Y CONEXIÓN
# ==============================================================================
import streamlit as st
import pandas as pd
from datetime import datetime
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
import io
import plotly.express as px
from dateparser.search import search_dates
import re
from supabase import create_client, Client
import telebot
import threading
import time

# ==============================================================================
# 1. CONFIGURACIÓN Y CREDENCIALES (¡LLENA ESTO!)
# ==============================================================================

SUPABASE_URL = "https://lzwwztbjregufgqvftsi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx6d3d6dGJqcmVndWZncXZmdHNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk1NDE3NDIsImV4cCI6MjA4NTExNzc0Mn0.Y95yaYPm6wm-d_6vez_HWyCo9Gy4YEwDL4EZFTD2zBk"

TELEGRAM_TOKEN = "8387488883:AAGHuw40CtSSx6XVFimW8uZcF6V_kdmEtkQ"

# Inicializar Supabase
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except:
    st.error("⚠️ Error conectando a Supabase.")
    st.stop()

# Inicializar Bot de Telegram (Solo una vez)
if 'bot_active' not in st.session_state:
    st.session_state.bot_active = False

def run_telegram_bot():
    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    
    @bot.message_handler(func=lambda m: True)
    def echo_all(message):
        try:
            # Reutilizamos la lógica de interpretación
            txt = message.text
            d = interpretar_intencion(txt)
            if d['monto'] > 0:
                datos = {
                    "fecha": d['fecha'], "tipo": d['tipo'], "categoria": d['categoria'],
                    "beneficiario": "Telegram", "detalle": d['detalle'], "monto": d['monto']
                }
                supabase.table("movimientos").insert(datos).execute()
                bot.reply_to(message, f"✅ Guardado: {d['tipo']} de ${d['monto']} ({d['fecha']})")
            else:
                bot.reply_to(message, "⚠️ No detecté monto. Di: 'Gaste 5 en pan'")
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")

    # Loop infinito del bot
    bot.infinity_polling()

# Arrancar el bot en un hilo separado (Segundo Plano)
if not st.session_state.bot_active:
    t = threading.Thread(target=run_telegram_bot, daemon=True)
    t.start()
    st.session_state.bot_active = True
    print("🤖 Bot de Telegram INICIADO en segundo plano.")

# Config Page
st.set_page_config(page_title="Billi Burgers ERP", page_icon="🍔", layout="wide")

# ==============================================================================
# 2. ESTILOS VISUALES
# ==============================================================================
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #E0E0E0; }
    h1, h2, h3 { font-family: 'Segoe UI'; color: #FFD700 !important; }
    .stButton>button {
        background: linear-gradient(135deg, #1F1F1F 0%, #333333 100%);
        color: #FFD700; border: 1px solid #FFD700; border-radius: 8px; font-weight: bold;
    }
    div[data-testid="stMetric"] { background-color: #1E1E1E; border-left: 5px solid #FFD700; border-radius: 10px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 3. FUNCIONES CRUD
# ==============================================================================
def fetch_data(table, start_date=None, end_date=None):
    query = supabase.table(table).select("*")
    if start_date and end_date:
        query = query.gte("fecha", start_date).lte("fecha", end_date)
    return pd.DataFrame(query.execute().data)

def insert_data(table, data):
    try: supabase.table(table).insert(data).execute(); return True
    except Exception as e: st.error(f"Error: {e}"); return False

def upsert_data(table, df_edited):
    records = df_edited.to_dict('records')
    try: supabase.table(table).upsert(records).execute(); return True
    except Exception as e: st.error(f"Error update: {e}"); return False

def delete_data(table, id_valor):
    try: supabase.table(table).delete().eq("id", id_valor).execute(); return True
    except Exception as e: st.error(f"Error delete: {e}"); return False

# ==============================================================================
# 4. LÓGICA INTELIGENTE (NLP)
# ==============================================================================
def procesar_audio(audio_bytes):
    r = sr.Recognizer()
    audio_file = io.BytesIO(audio_bytes)
    try:
        with sr.AudioFile(audio_file) as source:
            return r.recognize_google(r.record(source), language="es-EC").lower()
    except: return "Error"

def interpretar_intencion(texto):
    numeros = re.findall(r'\d+[.,]?\d*', texto)
    monto = float(numeros[0].replace(',', '.')) if numeros else 0.0
    tipo = "Ingreso" if any(p in texto.lower() for p in ['vendí', 'venta', 'ingreso']) else "Gasto"
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
# 5. APP PRINCIPAL
# ==============================================================================
def main():
    with st.sidebar:
        st.header("🍔 MENÚ")
        st.markdown("---")
        menu = st.radio("Nav", ["📊 Dashboard", "💰 Transacciones (CRUD)", "⚙️ Configuración", "🎙️ IA Voz"], label_visibility="collapsed")
        st.caption("Bot Telegram: ACTIVO 🟢")

    # 1. DASHBOARD
    if menu == "📊 Dashboard":
        st.title("Tablero Ejecutivo")
        c1, c2 = st.columns([1, 1])
        f_ini = c1.date_input("Desde", datetime.today().replace(day=1))
        f_fin = c2.date_input("Hasta", datetime.today())
        
        df = fetch_data("movimientos", f_ini, f_fin)
        if not df.empty:
            ing = df[df['tipo']=='Ingreso']['monto'].sum()
            gas = df[df['tipo']=='Gasto']['monto'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Ingresos", f"${ing:,.2f}")
            m2.metric("Gastos", f"${gas:,.2f}")
            m3.metric("Utilidad", f"${ing-gas:,.2f}")
            
            # Gráficos
            g1, g2 = st.columns(2)
            fig = px.bar(df, x='fecha', y='monto', color='tipo', barmode='group', template="plotly_dark", color_discrete_map={'Ingreso':'#00CC96', 'Gasto':'#EF553B'})
            g1.plotly_chart(fig, use_container_width=True)
            
            df_g = df[df['tipo']=='Gasto']
            if not df_g.empty:
                fig2 = px.pie(df_g, values='monto', names='categoria', hole=0.4, template="plotly_dark")
                g2.plotly_chart(fig2, use_container_width=True)
        else: st.info("Sin datos en este rango.")

    # 2. TRANSACCIONES (CRUD TOTAL)
    elif menu == "💰 Transacciones (CRUD)":
        st.title("Gestión de Movimientos")
        tab_new, tab_edit = st.tabs(["➕ Nuevo", "✏️ Editar / Borrar Historial"])
        
        with tab_new:
            st.subheader("Registrar")
            tipo = st.radio("Tipo", ["Ingreso", "Gasto"], horizontal=True)
            with st.form("trx"):
                c1, c2 = st.columns(2)
                fecha = c1.date_input("Fecha", datetime.today())
                monto = c2.number_input("Monto", min_value=0.01)
                
                cat, ben, det = "General", "General", ""
                if tipo == "Ingreso":
                    cat = "Venta"
                    det = st.text_input("Detalle Venta")
                else:
                    cat = st.selectbox("Categoría", ["Compras", "Servicios", "Sueldos"])
                    # Lógica de listas
                    if cat == "Compras":
                        provs = fetch_data("proveedores")['empresa'].tolist() if not fetch_data("proveedores").empty else []
                        ben = st.selectbox("Proveedor", provs) if provs else st.text_input("Proveedor")
                    elif cat == "Sueldos":
                        emps = fetch_data("empleados")['nombre'].tolist() if not fetch_data("empleados").empty else []
                        ben = st.selectbox("Empleado", emps) if emps else st.text_input("Empleado")
                    else: ben = st.text_input("Beneficiario")
                    det = st.text_input("Detalle Gasto")

                if st.form_submit_button("Guardar", use_container_width=True):
                    if insert_data("movimientos", {"fecha": str(fecha), "tipo": tipo, "categoria": cat, "beneficiario": str(ben), "detalle": det, "monto": monto}):
                        st.success("Guardado."); st.rerun()

        with tab_edit:
            st.subheader("Base de Datos Editable")
            st.info("💡 Haz doble clic en una celda para editar. Presiona 'Guardar Cambios' al finalizar.")
            
            df = fetch_data("movimientos")
            if not df.empty:
                df = df.sort_values(by="fecha", ascending=False)
                # EDITOR DE DATOS (CRUD)
                # disabled=['id'] para proteger la llave primaria
                df_edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor_movs", disabled=["id", "created_at"])
                
                c_sav, c_del = st.columns([4, 1])
                
                # BOTÓN GUARDAR (UPDATE)
                if c_sav.button("💾 Guardar Cambios en Movimientos", use_container_width=True):
                    if upsert_data("movimientos", df_edited):
                        st.success("Base de datos actualizada.")
                        st.rerun()
                
                # BOTÓN BORRAR (DELETE)
                with st.expander("🗑️ Borrar una Transacción"):
                    id_del = st.number_input("ID a eliminar", min_value=0, step=1)
                    if st.button("Confirmar Borrado"):
                        if delete_data("movimientos", id_del):
                            st.success("Transacción eliminada.")
                            st.rerun()

    # 3. CONFIGURACIÓN (CRUD)
    elif menu == "⚙️ Configuración":
        st.title("Maestros (CRUD)")
        t_e, t_p = st.tabs(["Empleados", "Proveedores"])
        
        with t_e:
            df_e = fetch_data("empleados")
            df_e_ed = st.data_editor(df_e, num_rows="dynamic", use_container_width=True, key="ed_emp")
            if st.button("💾 Guardar Empleados", key="btn_e"):
                if upsert_data("empleados", df_e_ed): st.success("Listo."); st.rerun()
            with st.expander("Borrar Empleado"):
                if st.button("Borrar por ID", key="del_e"): 
                    bid = st.number_input("ID", key="n_e"); delete_data("empleados", bid)

        with t_p:
            df_p = fetch_data("proveedores")
            df_p_ed = st.data_editor(df_p, num_rows="dynamic", use_container_width=True, key="ed_prov")
            if st.button("💾 Guardar Proveedores", key="btn_p"):
                if upsert_data("proveedores", df_p_ed): st.success("Listo."); st.rerun()
            with st.expander("Borrar Proveedor"):
                if st.button("Borrar por ID", key="del_p"): 
                    pid = st.number_input("ID", key="n_p"); delete_data("proveedores", pid)

    # 4. IA
    elif menu == "🎙️ IA Voz":
        st.title("Dictado Inteligente")
        col_mic, _ = st.columns([1, 3])
        with col_mic: audio = mic_recorder(start_prompt="🔴 HABLAR", stop_prompt="⏹️", format="wav", key="ia_mic")
        if audio:
            txt = procesar_audio(audio['bytes'])
            if txt != "Error":
                d = interpretar_intencion(txt)
                st.info(f"Detectado: {d['tipo']} | ${d['monto']} | {d['detalle']}")
                if st.button("Confirmar"):
                    insert_data("movimientos", {"fecha": d['fecha'], "tipo": d['tipo'], "categoria": d['categoria'], "beneficiario": "Voz IA", "detalle": d['detalle'], "monto": d['monto']})
                    st.success("Guardado.")

if __name__ == "__main__":
    main()