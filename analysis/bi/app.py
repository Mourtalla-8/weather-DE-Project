import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import ensure_enriched_csv

st.set_page_config(
    page_title="Tableau de Bord Météorologique",
    page_icon="☀️",
    layout="wide",
)


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(ensure_enriched_csv())
    df["date_time"] = pd.to_datetime(df["date_time"])
    return df


try:
    df = load_data()
except Exception:
    st.error(
        "Dataset enrichi ETL introuvable. Lancez d'abord : python scripts/run_pipeline.py"
    )
    st.stop()

st.title("☀️ Tableau de bord : Suivi des changements climatiques")
st.markdown("Ce tableau de bord interactif permet de suivre les indicateurs clés météorologiques.")

st.sidebar.header("Filtres interactifs")

precip_options = df["precip_type"].dropna().unique().tolist()
selected_precip = st.sidebar.multiselect(
    "Type de précipitations :",
    options=precip_options,
    default=precip_options,
)

min_date = df["date_time"].min().date()
max_date = df["date_time"].max().date()
selected_dates = st.sidebar.date_input(
    "Plage de dates :",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

filtered_df = df[
    (df["precip_type"].isin(selected_precip))
    & (df["date_time"].dt.date >= selected_dates[0])
    & (df["date_time"].dt.date <= selected_dates[1])
]

st.subheader("📊 Indicateurs Clés (KPI)")
col1, col2, col3 = st.columns(3)

avg_temp = filtered_df["temperature_c"].mean()
avg_humidity = filtered_df["humidity"].mean() * 100
total_records = len(filtered_df)

with col1:
    st.metric(label="Température Moyenne", value=f"{avg_temp:.2f} °C")
with col2:
    st.metric(label="Humidité Moyenne", value=f"{avg_humidity:.1f} %")
with col3:
    st.metric(label="Total Observations", value=f"{total_records:,}")

st.markdown("---")

st.subheader("📈 Suivi temporel")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### Évolution des températures")
    daily_filtered = (
        filtered_df.resample("D", on="date_time").mean(numeric_only=True).reset_index()
    )

    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.lineplot(
        data=daily_filtered,
        x="date_time",
        y="temperature_c",
        color="#2ecc71",
        ax=ax,
        label="Température moyenne",
    )
    ax.set_title("Évolution journalière de la température")
    ax.set_xlabel("Date")
    ax.set_ylabel("Température (°C)")
    sns.despine()
    st.pyplot(fig)

with col_right:
    st.markdown("#### Distribution du taux d'humidité")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.histplot(data=filtered_df, x="humidity", color="#3498db", kde=True, ax=ax)
    ax.set_title("Distribution de l'Humidité")
    ax.set_xlabel("Humidité (Ratio)")
    ax.set_ylabel("Fréquence")
    sns.despine()
    st.pyplot(fig)

if st.checkbox("Afficher un extrait des données brutes filtrées"):
    st.dataframe(filtered_df.head(100))
