import streamlit as st
import pandas as pd
from datetime import datetime
import os
import speech_recognition as sr
import re
from streamlit_mic_recorder import mic_recorder # LIBRERÍA NUEVA PARA WEB
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Billi Burgers App", page_icon="🍔", layout="centered")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { color: #FFD700 !important; }
    div[data-testid="stMetric"] { background-color: #262730; border: 1px solid #FFD700; border-radius: 10px; padding: 10px; }
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

# --- LÓGICA DE INTELIGENCIA ARTIFICIAL ---
def procesar_audio_web(audio_bytes):
    r = sr.Recognizer()
    
    # Guardar bytes en un archivo temporal para que speech_recognition lo lea
    audio_file = io.BytesIO(audio_bytes)
    
    try:
        with sr.AudioFile(audio_file) as source:
            audio_data = r.record(source)
            texto = r.recognize_google(audio_data, language="es-ES")
            return texto.lower()
    except Exception as e:
        return f"Error: {str(e)}"

def interpretar_comando(texto):
    numeros = re.findall(r'\d+', texto)
    if not numeros: return None, "No detecté dinero."
    monto = float(numeros[0])
    
    tipo = "desconocido"
    categoria = "Varios"
    if any(p in texto for p in ['gasté', 'gasto', 'compré', 'pago']):
        tipo = "gasto"
        if "empleado" in texto: categoria = "👷 Nómina"
        elif "carne" in texto or "papas" in texto: categoria = "🛒 Insumos"
    elif any(p in texto for p in ['vendí', 'venta', 'ingreso']):
        tipo = "ingreso"
    
    return {"tipo": tipo, "monto": monto, "categoria": categoria, "texto": texto}, "OK"

# --- INTERFAZ ---
st.title("🍔 Billi Burgers Web")
st.info("⚠️ Aviso: En esta versión Demo, los datos se pueden borrar si la app se reinicia.")

# --- BARRA DE ACCIÓN RÁPIDA (VOZ) ---
st.subheader("🎙️ Agente de Voz")
st.caption("Presiona 'Start' para grabar y habla.")

# Componente de grabación web
audio = mic_recorder(
    start_prompt="🔴 Grabar",
    stop_prompt="⏹️ Detener",
    key='recorder',
    format="wav" # Importante para speech_recognition
)

if audio:
    st.audio(audio['bytes'])
    texto_detectado = procesar_audio_web(audio['bytes'])
    
    if "Error" in texto_detectado:
        st.error("No pude entender el audio.")
    else:
        st.success(f"Escuché: '{texto_detectado}'")
        datos, msg = interpretar_comando(texto_detectado)
        
        if datos:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Monto detectado", f"${datos['monto']}")
            with col2:
                st.metric("Acción", datos['tipo'].upper())
            
            if st.button("✅ Confirmar y Guardar"):
                fecha = datetime.today().strftime('%Y-%m-%d')
                if datos['tipo'] == 'gasto':
                    df = cargar_datos(FILE_GASTOS, ['Fecha', 'Categoria', 'Detalle', 'Monto'])
                    nuevo = pd.DataFrame([{'Fecha': fecha, 'Categoria': datos['categoria'], 'Detalle': datos['texto'], 'Monto': datos['monto']}])
                    df = pd.concat([df, nuevo], ignore_index=True)
                    guardar_datos(df, FILE_GASTOS)
                elif datos['tipo'] == 'ingreso':
                    df = cargar_datos(FILE_INGRESOS, ['Fecha', 'Dia', 'Monto', 'Notas'])
                    nuevo = pd.DataFrame([{'Fecha': fecha, 'Dia': 'Voz', 'Monto': datos['monto'], 'Notas': 'Voz'}])
                    df = pd.concat([df, nuevo], ignore_index=True)
                    guardar_datos(df, FILE_INGRESOS)
                st.success("Guardado.")
                st.rerun()

st.markdown("---")

# --- DASHBOARD Y TABLAS ---
# (Mismo código de visualización de antes...)
st.subheader("📊 Resumen")
df_i = cargar_datos(FILE_INGRESOS, ['Fecha', 'Dia', 'Monto', 'Notas'])
df_g = cargar_datos(FILE_GASTOS, ['Fecha', 'Categoria', 'Detalle', 'Monto'])

total_ing = df_i['Monto'].sum() if not df_i.empty else 0.0
total_gas = df_g['Monto'].sum() if not df_g.empty else 0.0

c1, c2, c3 = st.columns(3)
c1.metric("Ingresos", f"${total_ing:,.2f}")
c2.metric("Gastos", f"${total_gas:,.2f}")
c3.metric("Ganancia", f"${total_ing-total_gas:,.2f}")

tab1, tab2 = st.tabs(["Ingresos", "Gastos"])
with tab1: st.dataframe(df_i, use_container_width=True)
with tab2: st.dataframe(df_g, use_container_width=True)