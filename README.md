# Proyecto Dollar 💵

Aplicación web para la ingesta, limpieza y visualización de activos financieros. Este proyecto permite transformar archivos CSV brutos en datos estructurados dentro de una base de datos SQLite para su análisis estadístico.

## 🚀 Funcionalidades
* **Limpieza Interactiva**: Selector de filas mediante Sliders y renombramiento dinámico de columnas con Streamlit.
* **Persistencia**: Almacenamiento de datos depurados en SQLite.
* **Visualización**: Gráfico evolutivo automático (Eje X: Tiempo / Eje Y: Cartera de valores).

## 🛠️ Stack Tecnológico
* **Lenguaje**: Python
* **Gestor de entorno**: `uv` (rápido y eficiente)
* **Frontend**: Streamlit
* **Base de datos**: SQLite

## 💻 Instalación y Uso
1. Activar el entorno virtual:
   `.venv\Scripts\activate`
2. Ejecutar la aplicación:
   `streamlit run app.py`

## 📊 Flujo de Trabajo
1. Cargar el archivo `.csv` (ej. `be2203.csv`).
2. Ajustar el Slider para acotar filas y renombrar columnas.
3. Finalizar limpieza para impactar en la base de datos y generar el gráfico.
