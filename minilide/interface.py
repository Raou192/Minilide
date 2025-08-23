from nicegui import ui
import pandas as pd
import os
import threading
import time
from datetime import datetime
import re

csv_path = 'data/temperatures.csv'
selected_date = None

def load_data():
    if not os.path.exists(csv_path):
        print("Fichier CSV introuvable.")
        return pd.DataFrame(columns=["timestamp", "capteur", "temperature"])
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
    return df

def update_chart(date_str=None):
    global selected_date

    df = load_data()
    if df.empty:
        print("CSV vide.")
        return

    if date_str:
        selected_date = pd.to_datetime(date_str).date()
    elif not selected_date:
        selected_date = datetime.now().date()

    df_filtered = df[df["timestamp"].dt.date == selected_date]
    print(f"Date sélectionnée : {selected_date}")
    print(f"Lignes trouvées : {len(df_filtered)}")

    chart.options['xAxis']['data'] = []
    chart.options['series'] = []
    table_column.clear()

    if df_filtered.empty:
        print("Aucun relevé pour cette date.")
        return

    df_filtered = df_filtered.assign(heure=df_filtered["timestamp"].dt.strftime("%H:%M"))
    heures = sorted(df_filtered["heure"].unique())
    chart.options['xAxis']['data'] = heures

    # pivot table
    pivot = df_filtered.pivot_table(index="heure", columns="capteur", values="temperature").reset_index()

    # Trier les colonnes : heure en premier, puis capteurs numériquement
    def capteur_key(col):
        if col == "heure":
            return -1  # heure en premier
        m = re.search(r'\d+', col)
        return int(m.group()) if m else float('inf')

    sorted_cols = sorted(pivot.columns, key=capteur_key)
    pivot = pivot[sorted_cols]

    # Table HTML
    with table_column:
        ui.table(
            columns=[{'name': col, 'label': col, 'field': col} for col in pivot.columns],
            rows=pivot.to_dict(orient="records")
        ).classes("w-full").style('overflow-x: auto; max-height: 300px;')

    # Graphique
    for capteur in pivot.columns[1:]:  # toutes les colonnes sauf "heure"
        serie_data = pivot[capteur].tolist()
        chart.options['series'].append({
            'name': capteur,
            'type': 'line',
            'data': serie_data,
        })

# UI
with ui.row():
    default_date = str(datetime.now().date())
    date_picker = ui.date(default_date, on_change=lambda e: update_chart(e.value)).props('max')

table_column = ui.column()

chart = ui.echart({
    'title': {'text': 'Températures par capteur'},
    'tooltip': {'trigger': 'axis'},
    'legend': {'data': []},
    'xAxis': {'type': 'category', 'data': []},
    'yAxis': {'type': 'value'},
    'series': [],
}).classes("w-full")

# Initialisation
selected_date = datetime.now().date()
update_chart(str(selected_date))

# Rafraîchissement automatique toutes les 30 secondes
def refresh_loop():
    while True:
        time.sleep(30)
        update_chart(str(selected_date))

threading.Thread(target=refresh_loop, daemon=True).start()

# Lancement serveur sur port 80
ui.run(host="0.0.0.0", port=80)