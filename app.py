import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, inspect, text
# Importante: para el gráfico profesional usamos plotly si está instalado
try:
    import plotly.express as px
except ImportError:
    px = None

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Proyecto Dollar | Suite Estadística", layout="wide")

def obtener_motor():
    return create_engine('sqlite:///datos_proyecto.db')

def guardar_en_db(df, nombre_tabla):
    try:
        engine = obtener_motor()
        # Limpiamos nombres de columnas para SQL (sin espacios ni caracteres raros)
        df_db = df.copy()
        df_db.columns = [str(c).strip().replace(' ', '_').lower() for c in df_db.columns]
        
        with engine.connect() as conn:
            # 'append' permite añadir datos mes a mes. Si quieres que borre todo usa 'replace'
            df_db.to_sql(nombre_tabla, con=conn, if_exists='append', index=False)
            conn.commit()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

@st.cache_data
def cargar_csv(file, tiene_header):
    header_val = 0 if tiene_header else None
    try:
        # Intentamos lectura estándar
        return pd.read_csv(file, header=header_val)
    except:
        file.seek(0)
        return pd.read_csv(file, encoding='latin-1', sep=None, engine='python', header=header_val)

def limpiar_numeros(valor):
    """
    Función mágica para arreglar los 715,9014B vs 7.177877T
    Quita puntos de miles, comas decimales y fuerza a flotante puro.
    """
    if pd.isna(valor): return 0.0
    s = str(valor).strip()
    # Si detectamos que el decimal es .01 o .00 y está estorbando:
    # 1. Quitamos puntos (habituales en miles europeos)
    s = s.replace('.', '')
    # 2. Cambiamos coma por punto decimal
    s = s.replace(',', '.')
    # 3. Extraemos solo lo numérico (por si hay letras o símbolos)
    s = "".join(c for c in s if c in "0123456789.-")
    try:
        return float(s)
    except:
        return 0.0

# --- INTERFAZ ---
st.title("💵 Proyecto Dollar")
st.markdown("---")

st.sidebar.header("📂 Carga de Archivos")
archivo_subido = st.sidebar.file_uploader("Sube tu CSV (Marzo, Abril, Mayo...)", type=["csv"])
con_cabecera = st.sidebar.checkbox("¿Tiene cabecera?", value=True)

if archivo_subido:
    df_raw = cargar_csv(archivo_subido, con_cabecera)
    
    tab_explorar, tab_limpiar, tab_db, tab_stats = st.tabs([
        "📊 Exploración", "🧹 Limpieza", "🗄️ Base de Datos", "🧮 Estadística"
    ])

    with tab_explorar:
        st.subheader("Vista Previa del Archivo Original")
        st.dataframe(df_raw.head(20), use_container_width=True)

    with tab_limpiar:
        st.subheader("Herramientas de Depuración")
        df_clean = df_raw.copy()

        with st.expander("✂️ Paso 1: Recortar filas (Selecciona tu fila de datos)"):
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

        with st.expander("🎯 Paso 3: Limpieza Numérica (Arreglo de Billones/Trillones)"):
            cols_a_limpiar = st.multiselect("Selecciona columnas de valores (carteras):", df_clean.columns.tolist())
            for c in cols_a_limpiar:
                df_clean[c] = df_clean[c].apply(limpiar_numeros)
            st.success("Conversión aplicada: Ahora los datos son números decimales puros.")

        st.divider()
        st.write("### 👁️ Vista Previa antes de Guardar")
        st.dataframe(df_clean, use_container_width=True)

        if st.button("💾 Guardar y Consolidar en SQLite", use_container_width=True, type="primary"):
            # Forzamos un nombre de tabla fijo para que todos los meses vayan al mismo sitio
            nombre_tabla = "cartera_consolidada" 
            if guardar_en_db(df_clean, nombre_tabla):
                st.success(f"¡Datos añadidos a la tabla '{nombre_tabla}'!")

    with tab_db:
        st.subheader("Contenido Histórico (SQLite)")
        engine = obtener_motor()
        try:
            tablas = inspect(engine).get_table_names()
            if tablas:
                tabla_sel = st.selectbox("Selecciona tabla para ver el histórico:", tablas)
                df_db = pd.read_sql(f"SELECT * FROM {tabla_sel}", con=engine)
                st.dataframe(df_db, use_container_width=True)
                
                if st.button("🗑️ Borrar toda la Base de Datos"):
                    with engine.connect() as conn:
                        conn.execute(text(f"DROP TABLE {tabla_sel}"))
                        conn.commit()
                    st.rerun()
            else:
                st.info("Base de datos vacía.")
        except:
            st.info("Iniciando base de datos...")

    with tab_stats:
        st.subheader("🧮 Análisis y Gráfico Evolutivo")
        
        # Leemos de la DB para que el gráfico use TODO lo guardado (Marzo + Abril + Mayo)
        try:
            df_hist = pd.read_sql("SELECT * FROM cartera_consolidada", con=obtener_motor())
            
            if not df_hist.empty:
                cols_num = df_hist.select_dtypes(include=['number']).columns.tolist()
                col_eje_x = df_hist.columns[0] # Usualmente la fecha o mes

                var_y = st.selectbox("Selecciona cartera para comparar meses:", options=cols_num)

                if px:
                    fig = px.line(df_hist, x=col_eje_x, y=var_y, title=f"Evolución Real: {var_y}", markers=True)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.line_chart(df_hist.set_index(col_eje_x)[var_y])
                
                st.table(df_hist[var_y].describe())
            else:
                st.warning("No hay datos históricos para graficar.")
        except:
            st.warning("Primero guarda datos en la pestaña 'Limpieza'.")