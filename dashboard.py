"""Interactive weather dashboard (Streamlit + Plotly).

Run locally:  streamlit run dashboard.py
Reads weather.db (created by weather_pipeline.py).
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

DB_FILE = Path(__file__).parent / "weather.db"
RAW_URL = "https://raw.githubusercontent.com/adi916tya/weather-etl-pipeline/main/weather.db"
HEAT = "RdYlBu_r"  # blue = cool, red = hot

st.set_page_config(page_title="India Weather Dashboard", page_icon="🌡️", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem;}
    [data-testid="stMetric"] {
        background: rgba(128,128,128,0.08);
        border: 1px solid rgba(128,128,128,0.2);
        padding: 14px 18px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=600)  # reload the data at most every 10 minutes
def load_data():
    path = DB_FILE
    if not path.exists():  # fallback: download the latest db from GitHub
        path = Path("weather_downloaded.db")
        path.write_bytes(requests.get(RAW_URL, timeout=15).content)
    with sqlite3.connect(path) as conn:
        df = pd.read_sql("SELECT city, temperature_c, timestamp FROM weather", conn)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp")


df = load_data()
if df.empty:
    st.warning("No data yet. Run the pipeline first.")
    st.stop()

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
all_cities = sorted(df["city"].unique())
cities = st.sidebar.multiselect("Cities", all_cities, default=all_cities)
min_d, max_d = df["timestamp"].dt.date.min(), df["timestamp"].dt.date.max()
date_range = st.sidebar.date_input(
    "Date range", (min_d, max_d), min_value=min_d, max_value=max_d
)
start, end = (date_range[0], date_range[-1]) if date_range else (min_d, max_d)

data = df[df["city"].isin(cities) & df["timestamp"].dt.date.between(start, end)]
if data.empty:
    st.info("No data for these filters. Pick at least one city and a valid date range.")
    st.stop()

# ---------- Header + KPIs ----------
st.title("🌡️ India Weather Dashboard")
st.caption("Live temperatures from Open-Meteo, collected every 6 hours by a GitHub Actions pipeline.")

latest = data.groupby("city").tail(1)  # data is already sorted by time
hot = latest.loc[latest["temperature_c"].idxmax()]
cold = latest.loc[latest["temperature_c"].idxmin()]
run_avgs = data.groupby("timestamp")["temperature_c"].mean()
current_avg = run_avgs.iloc[-1]
delta = f"{current_avg - run_avgs.iloc[-2]:+.1f} °C" if len(run_avgs) > 1 else None

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Average now", f"{current_avg:.1f} °C", delta=delta)
k2.metric(f"Hottest · {hot['city']}", f"{hot['temperature_c']:.1f} °C")
k3.metric(f"Coolest · {cold['city']}", f"{cold['temperature_c']:.1f} °C")
k4.metric("Total readings", f"{len(data):,}")
k5.metric("Last updated", data["timestamp"].max().strftime("%d %b, %H:%M"))

st.write("")
tab1, tab2, tab3 = st.tabs(["📈 Overview", "🔍 Compare cities", "🗂️ Data"])

# ---------- Tab 1: Overview ----------
with tab1:
    left, right = st.columns([2, 1])
    with left:
        fig = px.line(
            data, x="timestamp", y="temperature_c", color="city", markers=True,
            title="Temperature over time", labels={"temperature_c": "°C", "timestamp": ""},
        )
        fig.update_layout(hovermode="x unified", legend_title_text="")
        st.plotly_chart(fig)
    with right:
        fig = px.bar(
            latest.sort_values("temperature_c"), x="temperature_c", y="city", orientation="h",
            color="temperature_c", color_continuous_scale=HEAT, text_auto=".1f",
            title="Right now, hottest to coolest", labels={"temperature_c": "°C", "city": ""},
        )
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig)

# ---------- Tab 2: Compare ----------
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        avg = data.groupby("city", as_index=False)["temperature_c"].mean()
        fig = px.bar(
            avg.sort_values("temperature_c", ascending=False), x="city", y="temperature_c",
            color="temperature_c", color_continuous_scale=HEAT, text_auto=".1f",
            title="Average temperature per city", labels={"temperature_c": "°C", "city": ""},
        )
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig)
    with c2:
        fig = px.box(
            data, x="city", y="temperature_c", color="city",
            title="Temperature spread per city", labels={"temperature_c": "°C", "city": ""},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig)

    heat = data.assign(hour=data["timestamp"].dt.hour).pivot_table(
        index="city", columns="hour", values="temperature_c", aggfunc="mean"
    )
    fig = px.imshow(
        heat, aspect="auto", color_continuous_scale=HEAT,
        title="Average temperature by hour of day (fills in as data grows)",
        labels={"x": "Hour of day", "y": "", "color": "°C"},
    )
    st.plotly_chart(fig)

# ---------- Tab 3: Data ----------
with tab3:
    st.dataframe(data.sort_values("timestamp", ascending=False), hide_index=True)
    st.download_button("Download CSV", data.to_csv(index=False), "weather.csv", "text/csv")

st.caption("Source: Open-Meteo API · Built with Python, SQLite, Streamlit and Plotly")
