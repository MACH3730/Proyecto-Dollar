import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, inspect
import re

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Proyecto Dollar | Suite Estadística", layout="wide")

def obtener_motor():
    return create_engine('sqlite:///datos_proyecto.db')

def guardar_en_db(df, nombre_tabla):
    try:
        engine = obtener_motor()
        df_db = df.copy().astype(str)
        df_db.columns = [str(c).strip().replace(' ', '_').lower() for c in df_db.columns]
        with engine.connect() as conn:
            df_db.to_sql(nombre_tabla, con=conn, if_exists='replace', index=False)
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

# --- INTERFAZ ---
st.title("💵 Proyecto Dollar")
st.markdown("---")

st.sidebar.header("📂 Carga de Archivos")
archivo_subido = st.sidebar.file_uploader("Sube tu CSV", type=["csv"])
con_cabecera = st.sidebar.checkbox("¿Tiene cabecera?", value=True)

if archivo_subido:
    df_raw = cargar_csv(archivo_subido, con_cabecera)
    
    tab_explorar, tab_limpiar, tab_db, tab_stats = st.tabs([
        "📊 Exploración", "🧹 Limpieza", "🗄️ Base de Datos", "🧮 Estadística"
    ])

    with tab_explorar:
        st.subheader("Vista Previa del Archivo Original")
        st.dataframe(df_raw.head(50), use_container_width=True)

    with tab_limpiar:
        st.subheader("Herramientas de Depuración")
        # --- APLICAMOS CAMBIOS EN ORDEN ---
        df_clean = df_raw.copy()

        with st.expander("✂️ Paso 1: Recortar filas"):
            rango = st.slider("Filas a conservar:", 0, len(df_raw), (0, len(df_raw)))
            df_clean = df_clean.iloc[rango[0]:rango[1]]

        with st.expander("✏️ Paso 2: Renombrar Columnas"):
            nuevos_nombres = {}
            cols_ui = st.columns(3)
            for i, col_antigua in enumerate(df_clean.columns):
                with cols_ui[i % 3]:
                    nuevo = st.text_input(f"Col {i}: {col_antigua}", value=col_antigua, key=f"ren_{i}")
                    nuevos_nombres[col_antigua] = nuevo.strip()
            df_clean = df_clean.rename(columns=nuevos_nombres)

        with st.expander("🎯 Paso 3: Selección y Nulos"):
            columnas_finales = st.multiselect("Mantener columnas:", df_clean.columns.tolist(), default=df_clean.columns.tolist())
            df_clean = df_clean[columnas_finales]
            accion_nulos = st.segmented_control("Nulos:", ["Mantener", "Eliminar", "Poner 0"], default="Mantener")
            if accion_nulos == "Eliminar": df_clean = df_clean.dropna()
            if accion_nulos == "Poner 0": df_clean = df_clean.fillna(0)

        st.divider()
        st.write("### 👁️ Vista Previa de Datos Limpios")
        st.dataframe(df_clean, use_container_width=True) # <--- Ahora sí muestra los cambios

        if st.button("💾 Guardar en SQLite", use_container_width=True, type="primary"):
            nombre_tabla = re.sub(r'\W+', '', archivo_subido.name.split('.')[0])
            if guardar_en_db(df_clean, nombre_tabla):
                st.success(f"¡Tabla '{nombre_tabla}' guardada!")

    with tab_db:
        st.subheader("Contenido de la Base de Datos")
        engine = obtener_motor()
        tablas = inspect(engine).get_table_names()
        if tablas:
            tabla_sel = st.selectbox("Selecciona tabla:", tablas)
            df_db = pd.read_sql(f"SELECT * FROM {tabla_sel}", con=engine)
            st.dataframe(df_db.apply(pd.to_numeric, errors='ignore'), use_container_width=True)
        else:
            st.info("Base de datos vacía.")

    with tab_stats:
        st.subheader("🧮 Análisis Estadístico")
        
        # Trabajamos sobre los datos que has limpiado en la pestaña anterior
        df_stats = df_clean.copy()
        
        # --- MEJORA DE CONVERSIÓN ---
        # Recorremos las columnas (saltándonos la primera que es el tiempo)
        for col in df_stats.columns[1:]:
            # Paso A: Forzamos a texto y limpiamos espacios
            df_stats[col] = df_stats[col].astype(str).str.strip()
            # Paso B: Si detectamos que el número viene como "1.234,56", lo normalizamos
            # (Quitamos puntos de miles y cambiamos coma por punto decimal)
            df_stats[col] = df_stats[col].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            # Paso C: Convertimos a valor numérico real
            df_stats[col] = pd.to_numeric(df_stats[col], errors='ignore')
        
        # Identificamos cuáles son numéricas (deberían ser tus carteras)
        cols_num = df_stats.select_dtypes(include=['number']).columns.tolist()
        col_tiempo = df_stats.columns[0] # Nombre de la primera columna (ej: "Fecha")

        if cols_num:
            st.info(f"📅 Eje temporal detectado: **{col_tiempo}**")
            
            # Aquí es donde ahora verás los nombres de tus carteras
            var_y = st.selectbox("Selecciona la cartera para visualizar:", options=cols_num)

            # --- GRÁFICO ---
            try:
                import plotly.express as px
                fig = px.line(df_stats, x=col_tiempo, y=var_y, 
                              title=f"Evolución: {var_y}",
                              markers=True,
                              line_shape="linear")
                # Personalizamos el diseño para que se vea más profesional
                fig.update_layout(hovermode="x unified", xaxis_title=col_tiempo, yaxis_title="Valor")
                st.plotly_chart(fig, use_container_width=True)
            except:
                # Alternativa nativa si falla Plotly
                st.line_chart(df_stats.set_index(col_tiempo)[var_y])

            st.divider()
            st.write(f"#### 📊 Resumen Estadístico: {var_y}")
            # Mostramos las estadísticas solo de la columna seleccionada para no saturar
            st.table(df_stats[var_y].describe())
        else:
            st.warning("⚠️ No se han detectado columnas numéricas. Revisa que en la pestaña 'Limpieza' hayas dejado solo los números de las carteras.")

else:
    st.info("👋 Sube un archivo CSV para empezar.")