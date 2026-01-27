import telebot
from supabase import create_client
import re
from datetime import datetime
from dateparser.search import search_dates

# --- 1. CONFIGURACIÓN (PEGAR TUS CLAVES AQUÍ) ---
TELEGRAM_TOKEN = "8387488883:AAGHuw40CtSSx6XVFimW8uZcF6V_kdmEtkQ"

SUPABASE_URL = "https://lzwwztbjregufgqvftsi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx6d3d6dGJqcmVndWZncXZmdHNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk1NDE3NDIsImV4cCI6MjA4NTExNzc0Mn0.Y95yaYPm6wm-d_6vez_HWyCo9Gy4YEwDL4EZFTD2zBk"

# Conectar
bot = telebot.TeleBot(TELEGRAM_TOKEN)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🤖 Bot de Telegram INICIADO. Esperando mensajes...")

# --- 2. EL CEREBRO (Misma lógica que en la Web) ---
def interpretar_mensaje(texto):
    # Detectar Monto
    numeros = re.findall(r'\d+[.,]?\d*', texto)
    monto = float(numeros[0].replace(',', '.')) if numeros else 0.0
    
    # Detectar Tipo y Categoría
    texto_lower = texto.lower()
    tipo = "Gasto"
    categoria = "Varios"
    
    if any(p in texto_lower for p in ['vendí', 'venta', 'ingreso', 'cobré', 'cierre']):
        tipo = "Ingreso"
        categoria = "Venta General"
    elif any(p in texto_lower for p in ['gasté', 'gasto', 'compré', 'pago', 'pagar']):
        tipo = "Gasto"
        if "empleado" in texto_lower or "sueldo" in texto_lower: categoria = "Nómina"
        elif "carne" in texto_lower or "pan" in texto_lower: categoria = "Proveedores"
        elif "luz" in texto_lower or "agua" in texto_lower: categoria = "Servicios"

    # Detectar Fecha Inteligente
    fecha_str = datetime.today().strftime('%Y-%m-%d') # Por defecto hoy
    try:
        # Configuración para que entienda español
        settings = {'DATE_ORDER': 'DMY', 'PREFER_DATES_FROM': 'past'}
        match = search_dates(texto, languages=['es'], settings=settings)
        if match:
            # Tomamos la última fecha encontrada
            fecha_str = match[-1][1].strftime('%Y-%m-%d')
    except:
        pass

    return {
        "fecha": fecha_str,
        "tipo": tipo,
        "categoria": categoria,
        "beneficiario": "Telegram",
        "detalle": texto,
        "monto": monto
    }

# --- 3. ESCUCHAR MENSAJES ---
@bot.message_handler(func=lambda message: True)
def recibir_mensaje(message):
    texto = message.text
    chat_id = message.chat.id
    
    # Procesar el texto
    datos = interpretar_mensaje(texto)
    
    if datos['monto'] > 0:
        # Guardar en Nube (Supabase)
        try:
            supabase.table("movimientos").insert(datos).execute()
            
            # Responder al usuario
            respuesta = (
                f"✅ **Registro Exitoso**\n"
                f"📅 Fecha: {datos['fecha']}\n"
                f"💰 Monto: ${datos['monto']}\n"
                f"📂 Tipo: {datos['tipo']}\n"
                f"📝 Detalle: {datos['detalle']}"
            )
            bot.reply_to(message, respuesta)
            print(f"Nuevo registro desde Telegram: {datos['detalle']}")
            
        except Exception as e:
            bot.reply_to(message, f"❌ Error al guardar en la nube: {e}")
    else:
        bot.reply_to(message, "⚠️ No detecté ningún monto de dinero. Intenta decir: 'Gaste 5 dolares en pan'")

# Mantener el bot corriendo
bot.infinity_polling()