import streamlit as st
import plotly.express as px
import json
import pandas as pd

st.set_page_config(page_title="Mapa Colombia Plotly", layout="wide")

st.title("🇨🇴 Mapa Interactivo de Colombia")

# --- CARGAR DATOS ---
@st.cache_data
def cargar_datos():
    try:
        with open("colombia.geo.json", "r", encoding="utf-8") as f:
            geojson = json.load(f)

        # Crear una lista de todos los departamentos desde el GeoJSON
        deptos = [f["properties"]["name"] for f in geojson["features"]]
        return geojson, sorted(deptos)
    except Exception as e:
        st.error(f"Error al cargar el archivo: {e}")
        return None, []

geojson, lista_deptos = cargar_datos()

# --- ESTADO DE LA APP ---
if "seleccionados" not in st.session_state:
    st.session_state.seleccionados = {}
if "color_pincel" not in st.session_state:
    st.session_state.color_pincel = "#FF5733"

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎨 Configuración")

    st.subheader("1. Color de Pintura")
    st.session_state.color_pincel = st.color_picker("Elige un color", st.session_state.color_pincel)

    st.divider()

    st.subheader("2. Seleccionar Departamento")
    depto_sel = st.selectbox("Buscar departamento:", [""] + lista_deptos)

    col1, col2 = st.columns(2)
    if col1.button("✅ Pintar"):
        if depto_sel:
            st.session_state.seleccionados[depto_sel] = st.session_state.color_pincel
            st.rerun()

    if col2.button("🗑️ Borrar"):
        if depto_sel in st.session_state.seleccionados:
            del st.session_state.seleccionados[depto_sel]
            st.rerun()

    if st.button("🧹 Limpiar Todo"):
        st.session_state.seleccionados = {}
        st.rerun()

    st.divider()
    if st.session_state.seleccionados:
        st.write("**Departamentos Pintados:**")
        for d, c in st.session_state.seleccionados.items():
            st.markdown(f'<span style="color:{c}">■</span> {d}', unsafe_allow_html=True)

# --- PREPARAR DATOS PARA EL MAPA ---
# Creamos un DataFrame con todos los departamentos
df = pd.DataFrame({"departamento": lista_deptos})
# Asignamos el color seleccionado o un gris claro por defecto
df["color"] = df["departamento"].map(st.session_state.seleccionados).fillna("#F0F0F0")

# Calcular centroides de cada departamento para las etiquetas
def calcular_centroide(geometry):
    coords = []
    def extraer_coords(geom):
        if geom["type"] == "Polygon":
            for c in geom["coordinates"][0]:
                coords.append(c)
        elif geom["type"] == "MultiPolygon":
            for poly in geom["coordinates"]:
                for c in poly[0]:
                    coords.append(c)
    extraer_coords(geometry)
    if coords:
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return sum(lons)/len(lons), sum(lats)/len(lats)
    return None, None

centroides = {}
if geojson:
    for feature in geojson["features"]:
        nombre = feature["properties"]["name"]
        lon, lat = calcular_centroide(feature["geometry"])
        centroides[nombre] = (lon, lat)

# --- CREAR MAPA CON PLOTLY ---
fig = px.choropleth(
    df,
    geojson=geojson,
    locations="departamento",
    featureidkey="properties.name",
    color="color",
    color_discrete_map={c: c for c in df["color"].unique()},
    hover_name="departamento",
    labels={"color": "Color"}
)

# --- LEYENDA INTERNA (se exporta en el PNG) usando anotaciones ---
import plotly.graph_objects as go

annotations = []
shapes = []

if st.session_state.seleccionados:
    items = list(st.session_state.seleccionados.items())
    # Leyenda pegada al borde derecho del mapa (dentro del área paper)
    x0 = 0.76
    x1 = 0.99
    y_start = 0.97
    line_h = 0.08
    box_h = 0.07 + len(items) * line_h
    y0 = y_start - box_h
    r = 0.015  # radio de esquinas redondeadas (simulado con path SVG)

    # Fondo redondeado con path SVG
    shapes.append(dict(
        type="path",
        xref="paper", yref="paper",
        path=(
            f"M {x0+r},{y0} "
            f"L {x1-r},{y0} "
            f"Q {x1},{y0} {x1},{y0+r} "
            f"L {x1},{y_start-r} "
            f"Q {x1},{y_start} {x1-r},{y_start} "
            f"L {x0+r},{y_start} "
            f"Q {x0},{y_start} {x0},{y_start-r} "
            f"L {x0},{y0+r} "
            f"Q {x0},{y0} {x0+r},{y0} Z"
        ),
        fillcolor="#1a1a2e",
        line=dict(color="#f0c040", width=2.5),
        layer="above"
    ))

    # Título de la leyenda
    annotations.append(dict(
        xref="paper", yref="paper",
        x=x0 + 0.015, y=y_start - 0.012,
        text="<b>📋 LEYENDA</b>",
        showarrow=False,
        font=dict(size=13, color="#f0c040", family="Arial"),
        xanchor="left", yanchor="top"
    ))

    # Cada ítem: cuadro de color + nombre
    for i, (depto, color) in enumerate(items):
        y_pos = y_start - 0.065 - i * line_h

        # Cuadrito de color redondeado
        shapes.append(dict(
            type="rect",
            xref="paper", yref="paper",
            x0=x0 + 0.015, y0=y_pos - 0.025,
            x1=x0 + 0.048, y1=y_pos + 0.010,
            fillcolor=color,
            line=dict(color="white", width=1),
            layer="above"
        ))

        # Nombre del departamento
        annotations.append(dict(
            xref="paper", yref="paper",
            x=x0 + 0.058, y=y_pos - 0.007,
            text=depto,
            showarrow=False,
            font=dict(size=11, color="white", family="Arial"),
            xanchor="left", yanchor="middle"
        ))

# Ajustes estéticos del mapa
fig.update_geos(
    fitbounds="locations",
    visible=False,
    projection_type="mercator"
)

fig.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    height=700,
    showlegend=False,
    dragmode=False,
    annotations=annotations,
    shapes=shapes,
    paper_bgcolor="white",
)

# --- MOSTRAR MAPA + LEYENDA LATERAL ---
st.caption("📷 Pasa el mouse sobre el mapa y haz clic en la cámara para descargar PNG.")

config = {
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'mapa_colombia_personalizado',
        'height': 1400,
        'width': 1200,
        'scale': 2
    },
    'displaylogo': False,
    'modeBarButtonsToRemove': ['select2d', 'lasso2d']
}

st.plotly_chart(fig, use_container_width=True, config=config)