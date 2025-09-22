import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
from pushbullet import Pushbullet
from dotenv import load_dotenv
import re

load_dotenv()

MINILIDE_URL = "http://192.168.10.107"
CSV_PATH = "data/temperatures.csv"
ALERTE_SEUIL = 5  # °C
PUSHBULLET_TOKEN = os.getenv("PUSHBULLET_TOKEN")

# Plage de températures pour chaque capteur (min, max)
REFERENCE_TEMPS = {
    "Capteur 1": (10.0, 30.0),
    "Capteur 2": (-30, -15),
    "Capteur 3": (-30, -15),
    "Capteur 4": (-25, -15),
    "Capteur 5": (-25, -15),
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
    "Capteur 16": (-110, -90),
}

def month_csv_path(dt: datetime) -> str:
    return os.path.join("data", f"temperatures_{dt.strftime('%m-%Y')}.csv")

try:
    pb = Pushbullet(PUSHBULLET_TOKEN)
except Exception:
    pb = None

def send_alert(message: str):
    if pb:
        try:
            pb.push_note("Alerte Température Minilide", message)
            print(" Alerte envoyée via Pushbullet.")
        except Exception as e:
            print(f" Échec envoi Pushbullet : {e}")
    else:
        print(" Pushbullet non configuré.")

def extract_temperatures():
    try:
        response = requests.get(MINILIDE_URL, timeout=5)
        response.raise_for_status()
    except Exception as e:
        print(f" Échec : Impossible de contacter le Minilide ({e})")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    raw_text = soup.get_text()

    pattern = r"[-+]?\d{1,3}(?:[.,]\d{1,2})?\s*°C"
    matches = re.findall(pattern, raw_text)

    values = []
    for match in matches:
        try:
            temp = float(match.replace("°C", "").replace(",", ".").strip())
            values.append(temp)
        except ValueError:
            continue

    if not values:
        print(" Aucune température détectée dans la page HTML.")
        return

    values = values[:16]

    now = datetime.now()
    os.makedirs("data", exist_ok=True)

    new_data = []
    alert_messages = []

    for i in range(16):
        capteur = f"Capteur {i+1}"
        temp = values[i] if i < len(values) else None
        new_data.append([now, capteur, temp])

        if temp is not None:
            plage = REFERENCE_TEMPS.get(capteur)
            if plage is not None:
                min_temp, max_temp = plage
                if temp < min_temp or temp > max_temp:
                    alert_messages.append(
                        f"{capteur}: {temp}°C (hors plage {min_temp} – {max_temp}°C)"
                    )

    df_new = pd.DataFrame(new_data, columns=["timestamp", "capteur", "temperature"])

    _month_path = month_csv_path(now)
    exists_month = os.path.exists(_month_path) and os.path.getsize(_month_path) > 0

    if exists_month:
        try:
            df_old = pd.read_csv(_month_path)
            df_combined = pd.concat([df_old, df_new], ignore_index=True)
        except Exception:
            df_combined = df_new
    else:
        df_combined = df_new

    df_new.to_csv(
        _month_path,
        mode="a" if exists_month else "w",
        header=not exists_month,
        index=False,
    )

    try:
        pd.read_csv(_month_path).to_csv(CSV_PATH, index=False)
    except Exception:
        df_combined.to_csv(CSV_PATH, index=False)

    print(f" Températures enregistrées (total mois : {len(df_combined)} lignes)")

    if alert_messages:
        message = "\n".join(alert_messages)
        send_alert(message)

if __name__ == "__main__":
    extract_temperatures()
