import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import os
from pushbullet import Pushbullet
from dotenv import load_dotenv
import re
import time as t

load_dotenv()

MINILIDE_URL = "http://192.168.10.107"
CSV_PATH = "data/temperatures.csv"

# Var
pushbullet_alert_count = 0
MAX_PUSHBULLET_ALERTS = 3
PUSHBULLET_TOKEN = os.getenv("PUSHBULLET_TOKEN")

LOG_PATH = "log/monitoring.txt"
os.makedirs("log", exist_ok=True)
HEURES_EXTRACTION = [(7, 0), (12, 0), (18, 30)]

HEURES_REPORT = [
    (4, 17, 30),  # exemple : vendredi à 17:30
]

INTERVAL_MINUTES = 10
MAX_LOG_LINES = 2000

REFERENCE_TEMPS = {
    "Capteur 1": (10.0, 30.0),
    "Capteur 2": (-30, -15),
    "Capteur 3": (-30, -15),
    "Capteur 4": (-110, -90),
    "Capteur 5": (-110, -90),
    "Capteur 6": (-110, -90),
    "Capteur 7": (-110, -90),
    "Capteur 8": (-110, -90),
    "Capteur 9": (-110, -90),
    "Capteur 10": (-110, -90),
    "Capteur 11": (-110, -90),
    "Capteur 12": (-110, -90),
    "Capteur 13": (-110, -90),
    "Capteur 14": (-110, -90),
    "Capteur 15": (-110, -90),
    "Capteur 16": (-110, -90)
}

try:
    pb = Pushbullet(PUSHBULLET_TOKEN)
except Exception:
    pb = None

def write_log(message):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{now_str}] {message}"
    print(full_message)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")

# --- Logo ASCII ---
def print_logo():
    logo = r"""
███╗   ███╗██╗███╗   ██╗██╗██╗     ██╗██████╗ ███████╗
████╗ ████║██║████╗  ██║██║██║     ██║██╔══██╗██╔════╝
██╔████╔██║██║██╔██╗ ██║██║██║     ██║██║  ██║█████╗  
██║╚██╔╝██║██║██║╚██╗██║██║██║     ██║██║  ██║██╔══╝  
██║ ╚═╝ ██║██║██║ ╚████║██║███████╗██║██████╔╝███████╗
╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝╚══════╝╚═╝╚═════╝ ╚══════╝
Monitoring Minilide H24 - Pure 100% Python Juice

Démarrage du monitoring H24...
"""
    write_log(logo)

def send_alert(message):
    if pb:
        try:
            pb.push_note("Alerte Température Minilide", message)
            write_log("Alerte envoyée via Pushbullet.")
        except Exception as e:
            write_log(f"Échec envoi Pushbullet : {e}")
    else:
        write_log("Pushbullet non configuré.")

def extract_temperatures():
    global pushbullet_alert_count

    try:
        response = requests.get(MINILIDE_URL, timeout=5)
        response.raise_for_status()
    except Exception as e:
        write_log(f"Échec : Impossible de contacter le Minilide ({e})")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    raw_text = soup.get_text()
    pattern = r"[-+]?\d{1,3}[.,]?\d*\s*°C"
    matches = re.findall(pattern, raw_text)

    values = []
    for match in matches:
        try:
            temp = float(match.replace("°C", "").replace(",", ".").strip())
            values.append(temp)
        except ValueError:
            continue

    if not values:
        write_log("Aucune température détectée dans la page HTML.")
        return

    now = datetime.now()
    os.makedirs("data", exist_ok=True)

    new_data = []
    alert_messages = []

    for i, temp in enumerate(values):
        capteur = f"Capteur {i+1}"
        new_data.append([now, capteur, temp])

        plage = REFERENCE_TEMPS.get(capteur)
        if plage is not None:
            min_temp, max_temp = plage
            if temp < min_temp or temp > max_temp:
                alert_messages.append(f"{capteur}: {temp}°C (hors plage {min_temp}-{max_temp}°C)")

    #CSV
    df_new = pd.DataFrame(new_data, columns=["timestamp", "capteur", "temperature"])
    if os.path.exists(CSV_PATH):
        df_old = pd.read_csv(CSV_PATH)
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_csv(CSV_PATH, index=False)
    write_log(f"Températures enregistrées (total fichier : {len(df_combined)} lignes)")

    if alert_messages:
        if pushbullet_alert_count < MAX_PUSHBULLET_ALERTS:
            message = "\n".join(alert_messages)
            send_alert(message)
            pushbullet_alert_count += 1
    else:
        if pushbullet_alert_count > 0:
            write_log("Toutes les températures sont revenues à la normale, compteur Pushbullet remis à zéro.")
        pushbullet_alert_count = 0

if __name__ == "__main__":
    last_extraction = None
    last_report = None
    print_logo()

    while True:
        now = datetime.now()
        current_tuple = (now.weekday(), now.hour, now.minute)
        interval_delta = timedelta(minutes=INTERVAL_MINUTES)

        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > MAX_LOG_LINES:
                lignes_a_garder = lines[MAX_LOG_LINES // 2:]
                with open(LOG_PATH, "w", encoding="utf-8") as f:
                    f.writelines(lignes_a_garder)
                write_log(f"Log dépassait {MAX_LOG_LINES} lignes, les {MAX_LOG_LINES // 2} premières ont été supprimées.")

        for hh, mm in HEURES_EXTRACTION:
            target_time = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if target_time <= now < target_time + interval_delta and last_extraction != (hh, mm):
                write_log(f"--- Extraction température prévue à {hh}:{mm:02d} ---")
                extract_temperatures()
                write_log("Extraction terminée.")
                last_extraction = (hh, mm)

        for jd, hh, mm in HEURES_REPORT:
            target_time = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            report_tuple = (jd, hh, mm)
            if (current_tuple[0] == jd and target_time <= now < target_time + interval_delta
                and last_report != report_tuple):
                write_log(f"--- Envoi du rapport prévu pour jour {jd}, {hh}:{mm:02d} ---")
                os.system("python send_report.py")
                write_log("Rapport envoyé.")
                last_report = report_tuple

        write_log(f"Attente {INTERVAL_MINUTES} minutes avant la prochaine vérification...\n")
        t.sleep(INTERVAL_MINUTES * 60)