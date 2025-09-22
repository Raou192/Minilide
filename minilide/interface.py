from nicegui import ui
import pandas as pd
import os
from datetime import datetime
import re
from typing import Optional

csv_path = 'data/temperatures.csv'
selected_date = None

CAPTEUR_NOMS = {
    'Capteur 1': 'LABO Ambiant',
    'Capteur 2': 'PUREE FRUIT Congélateur',
    'Capteur 3': 'PROD FINIS Congélateur',
    'Capteur 4': 'DEPART Congélateur',
    'Capteur 5': 'TEMP5 vide',
    'Capteur 6': 'TEMP6 vide',
    'Capteur 7': 'TEMP7 vide',
    'Capteur 8': 'TEMP8 vide',
    'Capteur 9': 'TEMP9 vide',
    'Capteur 10': 'TEMP10 vide',
    'Capteur 11': 'TEMP11 vide',
    'Capteur 12': 'TEMP12 vide',
    'Capteur 13': 'TEMP13 vide',
    'Capteur 14': 'TEMP14 vide',
    'Capteur 15': 'TEMP15 vide',
    'Capteur 16': 'TEMP16 vide',
}

def set_chart_options(chart, options: dict) -> None:
    chart.options.clear()
    chart.options.update(options)
    chart.update()

def load_data() -> pd.DataFrame:
    if not os.path.exists(csv_path):
        print("Fichier CSV introuvable.")
        return pd.DataFrame(columns=["timestamp", "capteur", "temperature"])
    try:
        df = pd.read_csv(csv_path, sep=None, engine='python')
    except Exception:
        df = pd.read_csv(csv_path)

    df.columns = [str(c).strip().lower() for c in df.columns]
    required = {"timestamp", "capteur", "temperature"}
    if not required.issubset(df.columns):
        print(f"Colonnes manquantes: {required - set(df.columns)}")
        return pd.DataFrame(columns=["timestamp", "capteur", "temperature"])

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
    df = df.dropna(subset=["timestamp"])
    return df

def update_chart(date_str: Optional[str] = None) -> None:
    global selected_date

    df = load_data()
    if df.empty:
        print("CSV vide.")
        set_chart_options(chart, {
            'title': {'text': 'Températures par capteur', 'left': 'center', 'top': 5},
            'tooltip': {'trigger': 'axis'},
            'legend': {'data': [], 'top': 10, 'type': 'scroll', 'orient': 'horizontal'},
            'grid': {'top': 90, 'bottom': 60, 'left': 60, 'right': 30, 'containLabel': True},
            'xAxis': {'type': 'category', 'data': []},
            'yAxis': {'type': 'value'},
            'series': [],
        })
        table_column.clear()
        return

    if date_str:
        selected_date = pd.to_datetime(date_str).date()
    elif not selected_date:
        selected_date = datetime.now().date()

    df_filtered = df[df["timestamp"].dt.date == selected_date]
    print(f"Date sélectionnée : {selected_date} — lignes: {len(df_filtered)}")

    if df_filtered.empty:
        print("Aucun relevé pour cette date.")
        set_chart_options(chart, {
            'title': {'text': 'Températures par capteur', 'left': 'center', 'top': 5},
            'tooltip': {'trigger': 'axis'},
            'legend': {'data': [], 'top': 10, 'type': 'scroll', 'orient': 'horizontal'},
            'grid': {'top': 90, 'bottom': 60, 'left': 60, 'right': 30, 'containLabel': True},
            'xAxis': {'type': 'category', 'data': []},
            'yAxis': {'type': 'value'},
            'series': [],
        })
        table_column.clear()
        return

    df_filtered = df_filtered.assign(heure=df_filtered["timestamp"].dt.strftime("%H:%M"))
    heures = sorted(df_filtered["heure"].unique())

    pivot = df_filtered.pivot_table(index="heure", columns="capteur",
                                    values="temperature", aggfunc="mean")
    pivot = pivot.reindex(index=heures).reset_index()

    def capteur_key(col):
        if col == "heure":
            return -1
        m = re.search(r'\d+', str(col))
        return int(m.group()) if m else float('inf')

    pivot = pivot[sorted(pivot.columns, key=capteur_key)]
    pivot.rename(columns=CAPTEUR_NOMS, inplace=True)

    legend = [c for c in pivot.columns if c != "heure"]
    x_data = pivot["heure"].tolist()
    series = []
    for c in legend:
        numeric = pd.to_numeric(pivot[c], errors='coerce').round(1)
        serie_data = [None if pd.isna(v) else float(v) for v in numeric.tolist()]
        series.append({'name': c, 'type': 'line', 'data': serie_data})

    set_chart_options(chart, {
        'title': {'text': 'Températures par capteur', 'left': 'center', 'top': 0},
        'tooltip': {'trigger': 'axis'},
        'legend': {'data': legend, 'top': 40, 'type': 'scroll', 'orient': 'horizontal'},
        'grid': {'top': 90, 'bottom': 60, 'left': 60, 'right': 30, 'containLabel': True},
        'xAxis': {'type': 'category', 'data': x_data},
        'yAxis': {'type': 'value'},
        'series': series,
    })

    display_df = pivot.copy()
    for col in display_df.columns:
        if col != 'heure':
            display_df[col] = pd.to_numeric(display_df[col], errors='coerce').round(1)
    display_df = display_df.fillna('')
    table_column.clear()
    with table_column:
        ui.table(
            columns=[{'name': col, 'label': col, 'field': col} for col in display_df.columns],
            rows=display_df.to_dict(orient="records")
        ).classes("w-full").style('overflow-x: auto; max-height: 300px;')

with ui.row():
    default_date = str(datetime.now().date())
    date_picker = ui.date(
        default_date,
        on_change=lambda e: update_chart(e.value)
    ).props(f'max={default_date}')

table_column = ui.column()

chart = ui.echart({
    'title': {'text': 'Températures par capteur', 'left': 'center', 'top': 5},
    'tooltip': {'trigger': 'axis'},
    'legend': {'data': [], 'top': 10, 'type': 'scroll', 'orient': 'horizontal'},
    'grid': {'top': 90, 'bottom': 60, 'left': 60, 'right': 30, 'containLabel': True},
    'xAxis': {'type': 'category', 'data': []},
    'yAxis': {'type': 'value'},
    'series': [],
}).classes("w-full").style('height: 520px; margin-top: 8px;')

selected_date = datetime.now().date()
update_chart(str(selected_date))

ui.timer(30.0, lambda: update_chart(str(selected_date)))

ui.run(host="0.0.0.0", port=80)