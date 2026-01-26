import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import re
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
import io
import dateparser # LIBRERÍA NUEVA PARA DETECTAR FECHAS

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Billi Burgers ERP", page_icon="🍔", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { color: #FFD700 !important; }
    .stButton>button { border-radius: 8px; font-weight: bold; width: 100%; }
    /* Estilo para la tarjeta de confirmación */
    .confirm-card {
        background-color: #1c1e26;
        padding: 20px;
        border-left: 5px solid #FFD700;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DATOS (ARCHIVOS) ---
FILES = {
    'ingresos': 'ingresos.csv',
    'gastos': 'gastos.csv',
    'empleados': 'config_empleados.csv',
    'proveedores': 'config_proveedores.csv'
}

# --- FUNCIONES CRUD (CREATE, READ, UPDATE, DELETE) ---
def cargar_datos(tipo):
    archivo = FILES[tipo]
    if not os.path.exists(archivo):
        if tipo == 'empleados': cols = ['Nombre', 'Cargo', 'Sueldo_Base']
        elif tipo == 'proveedores': cols = ['Empresa', 'Categoria', 'Contacto']
        elif tipo == 'ingresos': cols = ['Fecha', 'Dia', 'Monto', 'Notas']
        elif tipo == 'gastos': cols = ['Fecha', 'Categoria', 'Beneficiario', 'Detalle', 'Monto']
        else: cols = []
        return pd.DataFrame(columns=cols)
    return pd.read_csv(archivo)

def guardar_datos(df, tipo):
    df.to_csv(FILES[tipo], index=False)

# --- CEREBRO DE LA IA (NLP + FECHAS) ---
def procesar_audio(audio_bytes):
    r = sr.Recognizer()
    audio_file = io.BytesIO(audio_bytes)
    try:
        with sr.AudioFile(audio_file) as source:
            audio_data = r.record(source)
            texto = r.recognize_google(audio_data, language="es-EC") # Español Ecuador
            return texto.lower()
    except:
        return "Error"

def extraer_intencion(texto):
    """Analiza el texto y extrae: Tipo, Monto, Fecha, Detalle"""
    
    # 1. Detectar Monto
    numeros = re.findall(r'\d+[.,]?\d*', texto)
    monto = float(numeros[0].replace(',', '.')) if numeros else 0.0
    
    # 2. Detectar Tipo (Gasto vs Ingreso)
    tipo = "desconocido"
    categoria = "Varios"
    if any(p in texto for p in ['gasté', 'gasto', 'compré', 'pago', 'pagar']):
        tipo = "gasto"
        if "empleado" in texto or "sueldo" in texto: categoria = "👷 Pago de Nómina"
        elif "carne" in texto or "compra" in texto: categoria = "🛒 Compra a Proveedor"
    elif any(p in texto for p in ['vendí', 'venta', 'ingreso', 'cobré']):
        tipo = "ingreso"

    # 3. Detectar Fecha (Usando dateparser para "ayer", "20 de enero", etc.)
    fecha_detectada = datetime.today() # Por defecto hoy
    settings = {'DATE_ORDER': 'DMY', 'PREFER_DATES_FROM': 'past', 'RELATIVE_BASE': datetime.today()}
    
    # Buscamos patrones de fecha comunes en español
    match_fecha = dateparser.search.search_dates(texto, languages=['es'], settings=settings)
    if match_fecha:
        # dateparser devuelve lista de tuplas (texto_encontrado, objeto_datetime)
        # Tomamos la última fecha encontrada que suele ser la más relevante
        fecha_detectada = match_fecha[-1][1]

    fecha_str = fecha_detectada.strftime('%Y-%m-%d')
    dia_str = fecha_detectada.strftime('%A')

    return {
        "tipo": tipo,
        "monto": monto,
        "categoria": categoria,
        "fecha": fecha_str,
        "dia": dia_str,
        "detalle": texto, # Guardamos el texto completo como detalle inicial
        "texto_original": texto
    }

# --- INTERFAZ PRINCIPAL ---
st.title("🍔 Billi Burgers System AI")

# Menú
menu = st.sidebar.radio("Navegación", 
    ["🎙️ Asistente de Voz (IA)", "📊 Historial & CRUD", "💰 Registro Manual", "⚙️ Configuración"], 
    index=0
)

# ==============================================================================
# 1. ASISTENTE DE VOZ CON CONFIRMACIÓN
# ==============================================================================
if menu == "🎙️ Asistente de Voz (IA)":
    st.header("🤖 Asistente Inteligente")
    st.info("Habla natural. Ej: 'El 20 de enero pagué 50 dólares en carne'")
    
    # Variable de estado para guardar la transacción pendiente
    if 'transaccion_pendiente' not in st.session_state:
        st.session_state.transaccion_pendiente = None

    # Componente de Micrófono
    col_mic, col_info = st.columns([1, 3])
    with col_mic:
        audio = mic_recorder(start_prompt="🔴 GRABAR", stop_prompt="⏹️ PROCESAR", key='recorder')

    if audio:
        texto = procesar_audio(audio['bytes'])
        if texto != "Error":
            datos = extraer_intencion(texto)
            if datos['monto'] > 0:
                st.session_state.transaccion_pendiente = datos # Guardamos en memoria temporal
            else:
                st.error(f"Entendí: '{texto}', pero no detecté el dinero.")
        else:
            st.warning("No te entendí, intenta de nuevo.")

    # MOSTRAR TARJETA DE CONFIRMACIÓN (Si hay algo pendiente)
    if st.session_state.transaccion_pendiente:
        pend = st.session_state.transaccion_pendiente
        
        st.markdown(f"""
        <div class="confirm-card">
            <h3>📢 Confirmación Requerida</h3>
            <p>He detectado la siguiente operación:</p>
            <ul>
                <li><strong>Acción:</strong> {pend['tipo'].upper()}</li>
                <li><strong>Fecha:</strong> {pend['fecha']} ({pend['dia']})</li>
                <li><strong>Monto:</strong> ${pend['monto']}</li>
                <li><strong>Detalle:</strong> "{pend['texto_original']}"</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        if c1.button("✅ SÍ, CONFIRMAR TRANSACCIÓN", type="primary"):
            # Guardar en base de datos real
            if pend['tipo'] == 'gasto':
                df = cargar_datos('gastos')
                nuevo = pd.DataFrame([{
                    'Fecha': pend['fecha'], 'Categoria': pend['categoria'], 
                    'Beneficiario': 'Voz', 'Detalle': pend['texto_original'], 'Monto': pend['monto']
                }])
                df = pd.concat([df, nuevo], ignore_index=True)
                guardar_datos(df, 'gastos')
            
            elif pend['tipo'] == 'ingreso':
                df = cargar_datos('ingresos')
                nuevo = pd.DataFrame([{
                    'Fecha': pend['fecha'], 'Dia': pend['dia'], 
                    'Monto': pend['monto'], 'Notas': pend['texto_original']
                }])
                df = pd.concat([df, nuevo], ignore_index=True)
                guardar_datos(df, 'ingresos')
            
            st.success("¡Transacción Guardada!")
            st.session_state.transaccion_pendiente = None # Limpiar
            st.rerun()
            
        if c2.button("❌ CANCELAR / REINTENTAR"):
            st.session_state.transaccion_pendiente = None
            st.rerun()

# ==============================================================================
# 2. HISTORIAL Y CRUD (EDITAR / BORRAR)
# ==============================================================================
elif menu == "📊 Historial & CRUD":
    st.header("📂 Historial de Movimientos")
    st.caption("Aquí puedes editar celdas directamente o borrar filas. Los cambios se guardan al presionar Enter.")

    tab1, tab2 = st.tabs(["Ingresos (Ventas)", "Gastos (Compras)"])

    # --- CRUD INGRESOS ---
    with tab1:
        df_i = cargar_datos('ingresos')
        # st.data_editor permite editar. num_rows="dynamic" permite añadir/borrar filas
        df_i_editado = st.data_editor(
            df_i, 
            num_rows="dynamic", 
            key="editor_ingresos",
            use_container_width=True
        )
        
        # Botón manual para forzar guardado (aunque data_editor suele actualizar el state)
        if st.button("💾 Guardar Cambios en Ingresos"):
            guardar_datos(df_i_editado, 'ingresos')
            st.success("Base de datos de Ingresos actualizada.")

    # --- CRUD GASTOS ---
    with tab2:
        df_g = cargar_datos('gastos')
        df_g_editado = st.data_editor(
            df_g, 
            num_rows="dynamic", 
            key="editor_gastos",
            use_container_width=True
        )
        
        if st.button("💾 Guardar Cambios en Gastos"):
            guardar_datos(df_g_editado, 'gastos')
            st.success("Base de datos de Gastos actualizada.")

# ==============================================================================
# 3. REGISTRO MANUAL Y CONFIGURACIÓN (Mantenemos lo previo)
# ==============================================================================
elif menu == "💰 Registro Manual":
    # (Aquí pegas el código del módulo de registro manual del paso anterior si lo deseas conservar)
    # Por brevedad, he puesto solo un placeholder, pero puedes copiar/pegar tu código previo.
    st.header("Registro Manual Tradicional")
    st.info("Usa esta opción si no quieres usar la voz.")
    # ... Pega aquí tu código de formularios ...

elif menu == "⚙️ Configuración":
    st.header("Configuración de Maestros")
    # (Código de empleados/proveedores del paso anterior)
    # ... Pega aquí tu código de config ...
