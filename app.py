import streamlit as st
import pandas as pd
import re
from sqlalchemy import create_engine, inspect, text

# Gráficos con Plotly
try:
    import plotly.express as px
except ImportError:
    px = None

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Proyecto Dollar | Suite Estadística", layout="wide")

def obtener_motor():
    return create_engine('sqlite:///datos_proyecto.db')

def limpiar_numeros(valor):
    """
    Tratamiento quirúrgico de strings financieros.
    Convierte '1.234,56' a 1234.56 y respeta '7.15' como 7.15.
    """
    if pd.isna(valor) or valor == "": return 0.0
    s = str(valor).strip()
    
    # Caso: 1.234,56 (Punto miles, coma decimal)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    # Caso: 1234,56 (Solo coma)
    elif "," in s:
        s = s.replace(",", ".")
    # Si solo hay un punto y no hay comas, lo dejamos como decimal (ej: 7.15)
    
    # Extraer solo caracteres válidos para float
    s = "".join(c for c in s if c in "0123456789.-")
    try:
        return float(s)
    except:
        return 0.0

def guardar_en_db(df, nombre_tabla):
    try:
        engine = obtener_motor()
        df_db = df.copy()
        # Estandarizar nombres de columnas para SQL
        df_db.columns = [str(c).strip().replace(' ', '_').lower() for c in df_db.columns]
        with engine.connect() as conn:
            df_db.to_sql(nombre_tabla, con=conn, if_exists='replace', index=False)
            conn.commit()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

@st.cache_data
def cargar_csv(file, tiene_header):
    header_val = 0 if tiene_header else None
    try:
        return pd.read_csv(file, header=header_val)
    except:
        file.seek(0)
        return pd.read_csv(file, encoding='latin-1', sep=None, engine='python', header=header_val)

# --- INICIO DE LÓGICA DE INTERFAZ ---
st.title("💵 Proyecto Dollar")
st.markdown("---")

# BARRA LATERAL: Siempre presente
st.sidebar.header("📂 Control de Datos")
archivo_subido = st.sidebar.file_uploader("Sube tu CSV para limpiar", type=["csv"])
con_cabecera = st.sidebar.checkbox("¿Tiene cabecera?", value=True)

# Detección de tablas existentes en la DB
engine = obtener_motor()
tablas = []
try:
    tablas = inspect(engine).get_table_names()
except:
    pass

st.sidebar.divider()
tabla_seleccionada = None
if tablas:
    tabla_seleccionada = st.sidebar.selectbox("📊 Selecciona tabla para análisis:", tablas)
else:
    st.sidebar.info("No hay tablas en la base de datos.")

# --- PESTAÑAS: Siempre fuera de cualquier condicional ---
tab_explorar, tab_limpiar, tab_db, tab_stats = st.tabs([
    "📊 Exploración", "🧹 Limpieza", "🗄️ Base de Datos", "🧮 Estadística"
])

# CONTENIDO DE PESTAÑAS 1 Y 2: Solo si hay un archivo nuevo
if archivo_subido:
    df_raw = cargar_csv(archivo_subido, con_cabecera)
    
    with tab_explorar:
        st.subheader("Vista Previa del Archivo Original")
        st.dataframe(df_raw.head(200), use_container_width=True)

    with tab_limpiar:
        st.subheader("Herramientas de Depuración")
        df_clean = df_raw.copy()

        with st.expander("✂️ Paso 1: Recortar filas"):
            rango = st.slider("Rango de filas:", 0, len(df_raw), (0, len(df_raw)))
            df_clean = df_clean.iloc[rango[0]:rango[1]]

        with st.expander("✏️ Paso 2: Renombrar Columnas"):
            nuevos_nombres = {}
            cols_ui = st.columns(3)
            for i, col_antigua in enumerate(df_clean.columns):
                with cols_ui[i % 3]:
                    nuevo = st.text_input(f"Col {i}: {col_antigua}", value=col_antigua, key=f"ren_{i}")
                    nuevos_nombres[col_antigua] = nuevo.strip()
            df_clean = df_clean.rename(columns=nuevos_nombres)

        with st.expander("🎯 Paso 3: Limpieza Numérica"):
            cols_a_limpiar = st.multiselect("Selecciona columnas de valores:", df_clean.columns.tolist())
            for c in cols_a_limpiar:
                df_clean[c] = df_clean[c].apply(limpiar_numeros)
            st.success("Limpieza aplicada.")

        st.divider()
        st.dataframe(df_clean, use_container_width=True)

        if st.button("💾 Guardar en SQLite", use_container_width=True, type="primary"):
            # Generar nombre limpio basado en el archivo
            nombre_tabla_limpio = re.sub(r'\W+', '', archivo_subido.name.split('.')[0])
            if guardar_en_db(df_clean, nombre_tabla_limpio):
                st.success(f"Tabla '{nombre_tabla_limpio}' guardada.")
                st.rerun()
else:
    with tab_explorar: st.info("Sube un CSV desde la barra lateral para ver su contenido.")
    with tab_limpiar: st.info("Sube un CSV desde la barra lateral para procesar datos.")

# PESTAÑA 3: BASE DE DATOS (Lee de la tabla seleccionada en el sidebar)
with tab_db:
    st.subheader("Contenido de la Base de Datos")
    if tabla_seleccionada:
        df_db = pd.read_sql(f"SELECT * FROM {tabla_seleccionada}", con=engine)
        st.write(f"Mostrando tabla: **{tabla_seleccionada}**")
        st.dataframe(df_db, use_container_width=True)
        
        if st.button(f"🗑️ Borrar tabla {tabla_seleccionada}"):
            with engine.connect() as conn:
                conn.execute(text(f"DROP TABLE {tabla_seleccionada}"))
                conn.commit()
            st.rerun()
    else:
        st.info("La base de datos está vacía.")

# PESTAÑA 4: ESTADÍSTICA (Sincronizada con el sidebar)
with tab_stats:
    st.subheader("Análisis Estadístico")
    if tabla_seleccionada:
        df_stats = pd.read_sql(f"SELECT * FROM {tabla_seleccionada}", con=engine)
        
        # Seleccionamos solo columnas que realmente sean numéricas después de limpiar
        # Nota: pd.to_numeric ayuda a confirmar que son números para el gráfico
        for col in df_stats.columns:
            if col != df_stats.columns[0]: # Ignorar la primera columna (normalmente nombres/fechas)
                df_stats[col] = pd.to_numeric(df_stats[col], errors='coerce')
        
        cols_num = df_stats.select_dtypes(include=['number']).columns.tolist()
        
        if cols_num:
            eje_x = df_stats.columns[0]
            col_grafico = st.selectbox("Columna a graficar:", cols_num)
            
            if px:
                fig = px.line(df_stats, x=eje_x, y=col_grafico, markers=True, title=f"Evolución {col_grafico}")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(df_stats.set_index(eje_x)[col_grafico])
            
            st.write("### Resumen")
            st.table(df_stats[col_grafico].describe())
        else:
            st.error("No se detectaron columnas numéricas válidas en esta tabla.")
    else:
        st.warning("Selecciona una tabla en la barra lateral para visualizarla.")