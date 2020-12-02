"""
-*- coding: utf-8 -*-
Written by: stef.vandermeulen
Date: 12/17/2019
"""

import colorlover as cl
import numpy as np
import os
import pandas as pd
import plotly as py
import plotly.graph_objects as go
from plotly.graph_objs import Figure

from plotly.subplots import make_subplots

PRICES = {
    "prijs verbruik laag": 0.2033,
    "prijs verbruik hoog": 0.2163,
    "prijs verbruik gas": 0.7673,
    "leveringskosten": 0.2281,
    "netbeheerkosten_elektra": 0.6293,
    "netbeheerkosten_gas": 0.4971,
    "vermindering energiebelasting": 1.44
}


def create_dir(path: str) -> bool:
    if not os.path.isdir(path):
        os.makedirs(path)

    return True


def plot_usage(df: pd.DataFrame, columns: list) -> Figure:
    fig = make_subplots(rows=4, cols=1)

    colors = cl.scales[f"{len(columns)}"]["qual"]["Set1"]
    colors = {c: color for c, color in zip(columns, colors)}

    df = df.sort_values(by="Datum").reset_index(drop=True)

    for column in columns:
        trace = go.Scatter(x=df["Datum"], y=df[column], name=column.strip("Stand ").capitalize(), legendgroup=column,
                           marker=dict(color=colors[column]))
        fig.append_trace(trace, 1, 1)

        column_daily_delta = column.replace("Stand", "Delta")
        trace = go.Scatter(x=df["Datum"], y=df[column_daily_delta], showlegend=False, legendgroup=column,
                           marker=dict(color=colors[column]))
        fig.append_trace(trace, 2, 1)

        column_annual_delta = column_daily_delta + " jaarlijks"
        trace = go.Scatter(x=df["Datum"], y=df[column_annual_delta], showlegend=False, legendgroup=column,
                           marker=dict(color=colors[column]))
        fig.append_trace(trace, 3, 1)

        if "gas" in column or "elektra" in column:
            column_costs = column_annual_delta + " kosten"
            trace = go.Scatter(x=df["Datum"], y=df[column_costs], showlegend=False, legendgroup=column,
                               marker=dict(color=colors[column]))
            fig.append_trace(trace, 4, 1)

    column_totaal = "Kosten jaarlijks totaal"
    trace = go.Scatter(x=df["Datum"], y=df[column_totaal], showlegend=True, legendgroup=column_totaal,
                       name=column_totaal, marker=dict(color="black"))
    fig.append_trace(trace, 4, 1)

    fig["layout"]["yaxis1"]["title"] = "Meterstand - offset"
    fig["layout"]["yaxis2"]["title"] = "Verbruik per dag"
    fig["layout"]["yaxis3"]["title"] = "Verbruik afgelopen jaar"
    fig["layout"]["yaxis4"]["title"] = "Kosten afgelopen jaar"

    fig.update_layout(template="plotly_white")

    return fig


def get_columns_electricity(columns: list) -> list:
    return [c for c in columns if any([val in c for val in ["laag", "hoog"]])]


def compute_daily_usage(df: pd.DataFrame, columns: list) -> (pd.DataFrame, list):
    columns_delta = []
    for column in columns:
        df[column] = df[column].interpolate()
        df[column] = df[column] - df[column][0]
        col_delta = column.replace("Stand", "Delta")
        columns_delta.append(col_delta)
        df[col_delta] = df[column].diff()

    return df, columns_delta


def compute_annual_usage(df: pd.DataFrame, columns: list) -> (pd.DataFrame, list):
    date_min = df["Datum"].min() + pd.Timedelta(days=365)
    columns_annual = [c + ' jaarlijks' for c in columns]

    for c in columns_annual:
        df[c] = np.nan
    for d in pd.date_range(date_min, df["Datum"].max()):
        d_min = d - pd.Timedelta(days=365)
        df.loc[df["Datum"] == d, columns_annual] = df.loc[
            (df["Datum"] >= d_min) &
            (df["Datum"] <= d), columns].sum().values

    return df, columns_annual


def compute_costs(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    column_e_total = ""
    column_g_total = ""
    for column in columns:
        column_costs = column + " kosten"
        if "elektra" in column:
            column_e_total = column_costs
            continue
        elif "laag" in column:
            df[column_costs] = df[column] * PRICES["prijs verbruik laag"]
        elif "hoog" in column:
            df[column_costs] = df[column] * PRICES["prijs verbruik hoog"]
        else:
            column_g_total = column_costs
            df[column_costs] = df[column] * PRICES["prijs verbruik gas"]
            df[column_costs] = df[column_costs].add(365 * PRICES["leveringskosten"])
            df[column_costs] = df[column_costs].add(365 * PRICES["netbeheerkosten_gas"])

    columns_e = get_columns_electricity(columns=[c for c in df if "kosten" in c])
    assert column_e_total
    df[column_e_total] = df[columns_e].sum(axis=1)
    df[column_e_total] = df[column_e_total].add(365 * PRICES["leveringskosten"])
    df[column_e_total] = df[column_e_total].add(365 * PRICES["netbeheerkosten_elektra"])
    df["Kosten jaarlijks totaal"] = df[[column_e_total, column_g_total]].sum(axis=1)
    df["Kosten jaarlijks totaal"] = df["Kosten jaarlijks totaal"].subtract(PRICES["vermindering energiebelasting"] * 365)

    return df


def main():
    path_home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path_data = os.path.join(path_home, "data")
    path_usage_data = os.path.join(path_data, "meter_standen.csv")
    path_output = os.path.join(path_home, "output")
    create_dir(path_output)

    df = pd.read_csv(path_usage_data, sep=";")
    df["Datum"] = pd.to_datetime(df["Datum"], format="%d-%m-%Y")
    columns_usage = [c for c in df if "verbruik" in c]
    cols_usage_electricity = get_columns_electricity(columns=columns_usage)
    df["Stand verbruik elektra"] = df[cols_usage_electricity].sum(axis=1)
    columns_usage = [c for c in df if "verbruik" in c]

    df_days = pd.DataFrame()
    df_days["Datum"] = pd.date_range(df["Datum"].min(), df["Datum"].max())
    df_days = df_days.merge(df[["Datum"] + columns_usage], on="Datum", how="left")
    df_days = df_days.sort_values(by="Datum").reset_index(drop=True)
    df_days, columns_delta = compute_daily_usage(df=df_days, columns=columns_usage)
    df_days, columns_annual = compute_annual_usage(df=df_days, columns=columns_delta)
    df_days = compute_costs(df=df_days, columns=columns_annual)

    path_html = os.path.join(path_output, "test.html")
    fig = plot_usage(df=df_days, columns=columns_usage)
    py.offline.plot(fig, filename=path_html, auto_open=True)

    # print(f"Totaal kosten per jaar: {cost_per_year:.2f}")
    # print(f"Totaal kosten per maand: {cost_per_month:.2f}")

    return True


if __name__ == "__main__":
    main()
    print("Done")
