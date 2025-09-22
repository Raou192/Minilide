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

def extract_name_temp_from_html(html: str):
    soup = BeautifulSoup(html, 'html.parser')
    pairs = []
    temp_nodes = soup.find_all(string=re.compile(r"[-+]?\d{1,3}[.,]?\d*\s*°\s*C", re.I))
    for tnode in temp_nodes:
        try:
            temp = float(re.sub(r"[^\d\-,.]", "", tnode).replace(",", "."))
        except Exception:
            continue

        name = None

        card = tnode.find_parent(["div","td","span","li","section","article"])
        if card:
            title = (card.find(["h1","h2","h3","h4","h5","h6"]) or
                     card.find(["strong","b"]))
            if title and title.get_text(strip=True):
                name = title.get_text(" ", strip=True)

            if not name:
                texts = [x.strip() for x in card.stripped_strings]
                if len(texts) >= 2 and any("°" in s for s in texts):
                    try:
                        idx = max(i for i,s in enumerate(texts) if "°" in s)
                    except ValueError:
                        idx = -1
                    label_parts = [s for s in texts[:idx] if "°" not in s]
                    if label_parts:
                        name = " ".join(label_parts).strip()

        pairs.append((name, temp))

    for tr in soup.select("table tr"):
        tds = [td.get_text(" ", strip=True) for td in tr.select("td")]
        if len(tds) >= 2 and re.search(r"°\s*C", tds[1]):
            try:
                temp = float(re.sub(r"[^\d\-,.]", "", tds[1]).replace(",", "."))
                name = tds[0] or None
                pairs.append((name, temp))
            except Exception:
                pass

    seen = set()
    uniq = []
    for name, temp in pairs:
        key = (name or "", temp)
        if key not in seen:
            seen.add(key)
            uniq.append((name, temp))
    return uniq

def month_csv_path(dt):
    """Ex: data/temperatures_08-2025.csv"""
    return os.path.join("data", f"temperatures_{dt.strftime('%m-%Y')}.csv")

def read_csv_safe(path: str) -> pd.DataFrame:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame(columns=["timestamp", "capteur", "temperature"])
    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception:
        df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "timestamp" not in df.columns:
        for c in ["date", "datetime", "time", "horodatage", "temps"]:
            if c in df.columns:
                df = df.rename(columns={c: "timestamp"})
                break
        else:
            first = df.columns[0]
            if first != "timestamp":
                df = df.rename(columns={first: "timestamp"})
    if "capteur" not in df.columns:
        for c in ["sensor", "probe", "cap"]:
            if c in df.columns:
                df = df.rename(columns={c: "capteur"})
                break
    if "temperature" not in df.columns:
        for c in ["temp", "t", "valeur"]:
            if c in df.columns:
                df = df.rename(columns={c: "temperature"})
                break
    keep = [c for c in ["timestamp", "capteur", "temperature"] if c in df.columns]
    df = df[keep]
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df

def append_csv_safe(path: str, df_new: pd.DataFrame):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    exists = os.path.exists(path)
    empty = (not exists) or os.path.getsize(path) == 0
    df_new = df_new[["timestamp", "capteur", "temperature"]]
    df_new.to_csv(path, mode="a" if exists and not empty else "w",
                  header=empty, index=False)

MINILIDE_URL = "http://192.168.10.107"
CSV_PATH = "data/temperatures.csv"

# Var
pushbullet_alert_count = 0
MAX_PUSHBULLET_ALERTS = 3
PUSHBULLET_TOKEN = os.getenv("PUSHBULLET_TOKEN")

LOG_PATH = "log/monitoring.txt"
os.makedirs("log", exist_ok=True)
os.makedirs("data", exist_ok=True)
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

    pairs = extract_name_temp_from_html(response.text)

    values = [(n, v) for (n, v) in pairs if isinstance(v, (int, float))]
    if not values:
        write_log("Aucune température détectée dans la page HTML.")
        return


    now = datetime.now()

    new_data = []
    alert_messages = []

    for i, (name, temp) in enumerate(values):
        capteur = (name or f"Capteur {i+1}").strip()

        new_data.append([now, capteur, temp])

        plage = REFERENCE_TEMPS.get(capteur) or REFERENCE_TEMPS.get(f"Capteur {i+1}")
        if plage is not None:
            min_temp, max_temp = plage
            if temp < min_temp or temp > max_temp:
                alert_messages.append(f"{capteur}: {temp}°C (hors plage {min_temp}-{max_temp}°C)")

    #CSV
    df_new = pd.DataFrame(new_data, columns=["timestamp", "capteur", "temperature"])

    month_path = month_csv_path(now)
    append_csv_safe(month_path, df_new)

    try:
        df_month = read_csv_safe(month_path)
        df_month.to_csv(CSV_PATH, index=False)
    except Exception as e:
        write_log(f"Copie vers {CSV_PATH} échouée : {e}")

    try:
        total_lines = len(read_csv_safe(month_path))
    except Exception:
        total_lines = "?"

    write_log(f"Températures enregistrées (fichier mensuel : {month_path}, total : {total_lines} lignes)")

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