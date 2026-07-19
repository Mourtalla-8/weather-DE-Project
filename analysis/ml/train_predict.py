#!/usr/bin/env python3
"""Entraînement Random Forest et génération de la figure historique complète."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import ensure_enriched_csv, OUTPUT_ML, ensure_output_dirs

sns.set_style("whitegrid")
plt.rcParams["font.family"] = "sans-serif"
PALETTE = {"real": "#1b3a4b", "pred": "#e8b054"}


def main() -> None:
    ensure_output_dirs()

    enriched_csv = ensure_enriched_csv()
    df = pd.read_csv(enriched_csv, parse_dates=["date_time", "date"])
    df = df.sort_values("date_time").reset_index(drop=True)

    target = "temperature_c"
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["is_rain"] = (df["precip_type"] == "rain").astype(int)
    df["is_snow"] = (df["precip_type"] == "snow").astype(int)

    lag_hours = [1, 2, 3, 6, 12, 24]
    roll_windows = [3, 6, 12, 24]
    for lag in lag_hours:
        df[f"temp_lag_{lag}"] = df[target].shift(lag)
    for window in roll_windows:
        df[f"temp_roll_mean_{window}"] = (
            df[target].shift(1).rolling(window, min_periods=window).mean()
        )

    base_feats = [
        "humidity",
        "wind_speed_km_per_h",
        "wind_bearing_degrees",
        "visibility_km",
        "pressure_millibars",
        "hour_sin",
        "hour_cos",
        "month_sin",
        "month_cos",
        "is_rain",
        "is_snow",
    ]
    features = base_feats + [f"temp_lag_{h}" for h in lag_hours] + [
        f"temp_roll_mean_{w}" for w in roll_windows
    ]

    df_full = df.copy()
    df_model = df.dropna(subset=features + [target]).reset_index(drop=True)

    n = len(df_model)
    i1, i2 = int(n * 0.70), int(n * 0.85)
    train = df_model.iloc[:i1].copy()
    val = df_model.iloc[i1:i2].copy()
    test = df_model.iloc[i2:].copy()
    x_train, y_train = train[features], train[target]
    x_test, y_test = test[features], test[target]

    scaler = StandardScaler()
    x_train_s = scaler.fit_transform(x_train)
    x_test_s = scaler.transform(x_test)

    rf = RandomForestRegressor(
        n_estimators=150, max_depth=16, random_state=42, n_jobs=-1
    )
    rf.fit(x_train_s, y_train)
    pred_test = rf.predict(x_test_s)
    print(f"MAE={mean_absolute_error(y_test, pred_test):.3f} R2={r2_score(y_test, pred_test):.4f}")

    pred_full = pd.Series(np.nan, index=df_full.index)
    test_index_in_full = df_full[df_full["date_time"].isin(test["date_time"])].index
    pred_full.loc[test_index_in_full] = pred_test
    df_full["prediction"] = pred_full.values

    daily = (
        df_full.resample("D", on="date_time")
        .agg({target: "mean", "prediction": "mean"})
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(
        daily["date_time"],
        daily[target],
        color=PALETTE["real"],
        lw=0.8,
        label="Température réelle (moyenne journalière)",
    )
    ax.plot(
        daily["date_time"],
        daily["prediction"],
        color=PALETTE["pred"],
        lw=1.3,
        label="Température prédite (période de test uniquement)",
    )

    train_end = train["date_time"].max()
    val_end = val["date_time"].max()
    ax.axvspan(
        daily["date_time"].min(),
        train_end,
        color="#e6edf2",
        alpha=0.5,
        label="Entraînement",
    )
    ax.axvspan(train_end, val_end, color="#f5e6c8", alpha=0.4, label="Validation")

    ax.set_title(
        "Température réelle (2005–2016) vs prédite (période de test)",
        fontsize=14,
        weight="bold",
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Température (°C)")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    fig.tight_layout()

    output_path = OUTPUT_ML / "fig1_historique_complet.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"OK -> {output_path}")


if __name__ == "__main__":
    main()
