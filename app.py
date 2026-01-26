import streamlit as st
import pandas as pd
from datetime import datetime
import os
import re
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
import io
import dateparser # Asegúrate de tener: pip install dateparser

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Billi Burgers ERP", page_icon="🍔", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { color: #FFD700 !important; }
    /* Ajuste para botones */
    .stButton>button { border-radius: 8px; font-weight: bold; }
    /* Tarjeta de confirmación */
    .confirm-card {
        background-color: #1c1e26;
        padding: 20px;
        border-left: 5px solid #FFD700;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIÓN DE ARCHIVOS ---
FILES = {
    'ingresos': 'ingresos.csv',
    'gastos': 'gastos.csv',
    'empleados': 'config_empleados.csv',
    'proveedores': 'config_proveedores.csv'
}

def cargar_datos(tipo):
    archivo = FILES[tipo]
    if not os.path.exists(archivo):
        # Estructuras base
        if tipo == 'empleados': return pd.DataFrame(columns=['Nombre', 'Cargo', 'Sueldo_Base'])
        if tipo == 'proveedores': return pd.DataFrame(columns=['Empresa', 'Categoria', 'Contacto'])
        if tipo == 'ingresos': return pd.DataFrame(columns=['Fecha', 'Dia', 'Monto', 'Notas'])
        if tipo == 'gastos': return pd.DataFrame(columns=['Fecha', 'Categoria', 'Beneficiario', 'Detalle', 'Monto'])
        return pd.DataFrame()
    return pd.read_csv(archivo)

def guardar_datos(df, tipo):
    df.to_csv(FILES[tipo], index=False)

# --- CEREBRO IA (AUDIO + FECHAS) ---
def procesar_audio(audio_bytes):
    r = sr.Recognizer()
    audio_file = io.BytesIO(audio_bytes)
    try:
        with sr.AudioFile(audio_file) as source:
            audio_data = r.record(source)
            # Intentamos español de Ecuador o general
            texto = r.recognize_google(audio_data, language="es-EC")
            return texto.lower()
    except:
        return "Error"

def extraer_intencion(texto):
    # 1. Monto
    numeros = re.findall(r'\d+[.,]?\d*', texto)
    monto = float(numeros[0].replace(',', '.')) if numeros else 0.0
    
    # 2. Tipo
    tipo = "desconocido"
    categoria = "Varios"
    if any(p in texto for p in ['gasté', 'gasto', 'compré', 'pago', 'pagar']):
        tipo = "gasto"
        if "empleado" in texto or "sueldo" in texto: categoria = "👷 Pago de Nómina"
        elif "carne" in texto or "compra" in texto: categoria = "🛒 Compra a Proveedor"
    elif any(p in texto for p in ['vendí', 'venta', 'ingreso', 'cobré']):
        tipo = "ingreso"

    # 3. Fecha (dateparser)
    fecha_detectada = datetime.today()
    settings = {'DATE_ORDER': 'DMY', 'PREFER_DATES_FROM': 'past'}
    match_fecha = dateparser.search.search_dates(texto, languages=['es'], settings=settings)
    if match_fecha:
        fecha_detectada = match_fecha[-1][1]

    return {
        "tipo": tipo, "monto": monto, "categoria": categoria,
        "fecha": fecha_detectada.strftime('%Y-%m-%d'),
        "dia": fecha_detectada.strftime('%A'),
        "texto_original": texto
    }

# --- INTERFAZ PRINCIPAL ---
st.title("🍔 Billi Burgers System AI")

menu = st.sidebar.radio("Navegación", 
    ["🎙️ Asistente IA", "📊 Historial (CRUD)", "💰 Registro Manual", "⚙️ Configuración"], 
    index=0
)

# ==============================================================================
# 1. ASISTENTE IA (VOZ)
# ==============================================================================
if menu == "🎙️ Asistente IA":
    st.header("🤖 Asistente de Voz Inteligente")
    st.info("Ejemplo: 'Ayer gasté 45 dólares en papas'")

    if 'transaccion_pendiente' not in st.session_state:
        st.session_state.transaccion_pendiente = None

    col_mic, col_x = st.columns([1, 4])
    with col_mic:
        # Componente de micrófono web
        audio = mic_recorder(start_prompt="🔴 GRABAR", stop_prompt="⏹️ LISTO", key='recorder')

    if audio:
        texto = procesar_audio(audio['bytes'])
        if texto != "Error":
            datos = extraer_intencion(texto)
            if datos['monto'] > 0:
                st.session_state.transaccion_pendiente = datos
            else:
                st.error(f"Entendí: '{texto}', pero no escuché el dinero.")
        else:
            st.warning("No pude entender el audio.")

    # TARJETA DE CONFIRMACIÓN
    if st.session_state.transaccion_pendiente:
        pend = st.session_state.transaccion_pendiente
        
        st.markdown(f"""
        <div class="confirm-card">
            <h3>📢 Confirmar Transacción</h3>
            <ul>
                <li><strong>Acción:</strong> {pend['tipo'].upper()}</li>
                <li><strong>Fecha:</strong> {pend['fecha']} ({pend['dia']})</li>
                <li><strong>Monto:</strong> ${pend['monto']}</li>
                <li><strong>Nota:</strong> "{pend['texto_original']}"</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        # Fix: width="stretch" en lugar de use_container_width
        if c1.button("✅ CONFIRMAR Y GUARDAR", type="primary"):
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
            
            st.success("Guardado correctamente.")
            st.session_state.transaccion_pendiente = None
            st.rerun()
            
        if c2.button("❌ DESCARTAR"):
            st.session_state.transaccion_pendiente = None
            st.rerun()

# ==============================================================================
# 2. HISTORIAL CRUD (EDITABLE)
# ==============================================================================
elif menu == "📊 Historial (CRUD)":
    st.header("📂 Base de Datos Interactiva")
    tab1, tab2 = st.tabs(["Ingresos", "Gastos"])

    with tab1:
        df_i = cargar_datos('ingresos')
        # Fix: width="stretch" para data_editor
        df_i_edit = st.data_editor(df_i, num_rows="dynamic", key="edit_ing", use_container_width=True)
        if st.button("💾 Guardar Cambios Ingresos"):
            guardar_datos(df_i_edit, 'ingresos')
            st.success("Actualizado.")

    with tab2:
        df_g = cargar_datos('gastos')
        # Fix: width="stretch" para data_editor
        df_g_edit = st.data_editor(df_g, num_rows="dynamic", key="edit_gas", use_container_width=True)
        if st.button("💾 Guardar Cambios Gastos"):
            guardar_datos(df_g_edit, 'gastos')
            st.success("Actualizado.")

# ==============================================================================
# 3. REGISTRO MANUAL (CON MAESTROS)
# ==============================================================================
elif menu == "💰 Registro Manual":
    st.header("Registro Manual Detallado")
    tipo = st.radio("Tipo", ["Ingreso", "Gasto"], horizontal=True)
    
    if tipo == "Ingreso":
        with st.form("form_ing"):
            fecha = st.date_input("Fecha", datetime.today())
            monto = st.number_input("Monto ($)", min_value=0.0)
            notas = st.text_area("Notas")
            if st.form_submit_button("Guardar"):
                df = cargar_datos('ingresos')
                nuevo = pd.DataFrame([{'Fecha': fecha, 'Dia': fecha.strftime("%A"), 'Monto': monto, 'Notas': notas}])
                df = pd.concat([df, nuevo], ignore_index=True)
                guardar_datos(df, 'ingresos')
                st.success("Venta guardada.")
    else:
        # Cargar Maestros
        emps = cargar_datos('empleados')['Nombre'].tolist()
        provs = cargar_datos('proveedores')['Empresa'].tolist()
        
        cat = st.selectbox("Categoría", ["Compra Proveedor", "Nómina", "Otros"])
        beneficiario = st.text_input("Beneficiario")
        
        # Lógica inteligente de autocompletado
        if cat == "Compra Proveedor" and provs:
            beneficiario = st.selectbox("Seleccionar Proveedor", provs)
        elif cat == "Nómina" and emps:
            beneficiario = st.selectbox("Seleccionar Empleado", emps)

        with st.form("form_gas"):
            fecha = st.date_input("Fecha", datetime.today())
            monto = st.number_input("Monto ($)", min_value=0.0)
            detalle = st.text_input("Detalle")
            if st.form_submit_button("Guardar Gasto"):
                df = cargar_datos('gastos')
                nuevo = pd.DataFrame([{
                    'Fecha': fecha, 'Categoria': cat, 'Beneficiario': beneficiario, 
                    'Detalle': detalle, 'Monto': monto
                }])
                df = pd.concat([df, nuevo], ignore_index=True)
                guardar_datos(df, 'gastos')
                st.success("Gasto guardado.")

# ==============================================================================
# 4. CONFIGURACIÓN (MAESTROS)
# ==============================================================================
elif menu == "⚙️ Configuración":
    st.header("⚙️ Gestión de Maestros")
    t1, t2 = st.tabs(["Empleados", "Proveedores"])
    
    with t1:
        with st.form("add_emp"):
            col1, col2 = st.columns(2)
            nom = col1.text_input("Nombre")
            sueldo = col2.number_input("Sueldo Base", min_value=0.0)
            if st.form_submit_button("Agregar Empleado"):
                df = cargar_datos('empleados')
                nuevo = pd.DataFrame([{'Nombre': nom, 'Cargo': 'General', 'Sueldo_Base': sueldo}])
                df = pd.concat([df, nuevo], ignore_index=True)
                guardar_datos(df, 'empleados')
                st.success("Empleado agregado.")
        st.dataframe(cargar_datos('empleados'), use_container_width=True)

    with t2:
        with st.form("add_prov"):
            emp = st.text_input("Nombre Empresa")
            cat = st.text_input("Categoría (Carne, Lacteos...)")
            if st.form_submit_button("Agregar Proveedor"):
                df = cargar_datos('proveedores')
                nuevo = pd.DataFrame([{'Empresa': emp, 'Categoria': cat, 'Contacto': ''}])
                df = pd.concat([df, nuevo], ignore_index=True)
                guardar_datos(df, 'proveedores')
                st.success("Proveedor agregado.")
        st.dataframe(cargar_datos('proveedores'), use_container_width=True)