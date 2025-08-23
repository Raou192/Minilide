import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage
from fpdf import FPDF
import matplotlib.pyplot as plt
import math

load_dotenv()

CSV_PATH = "data/temperatures.csv"
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

NOM_CAPTEURS = {f"Capteur {i}": f"Capteur {i}" for i in range(1, 17)}

if not os.path.exists(CSV_PATH):
    print(" Le fichier 'temperatures.csv' est introuvable.")
    exit(1)

df = pd.read_csv(CSV_PATH)
df['timestamp'] = pd.to_datetime(df['timestamp'])
today = datetime.now().date()
df_today = df[df['timestamp'].dt.date == today]

if df_today.empty:
    print(" Aucun relevé pour aujourd’hui.")
    exit(1)

df_today = df_today.assign(heure=df_today["timestamp"].dt.strftime("%H:%M"))

pivot = df_today.pivot_table(index="heure", columns="capteur", values="temperature")
pivot = pivot.round(1).fillna("")
pivot.reset_index(inplace=True)

if len(pivot) < 2:
    print(" Pas assez de relevés pour générer un rapport.")
    exit(0)

ordered_cols = ["heure"] + sorted([col for col in pivot.columns if col != "heure"], key=lambda x: int(x.split()[-1]))
pivot = pivot[ordered_cols]

pivot.rename(columns=NOM_CAPTEURS, inplace=True)

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", 'B', 16)
pdf.cell(0, 10, "Rapport journalier - Températures", ln=1)

pdf.set_font("Arial", '', 11)
pdf.cell(0, 10, f"Résumé du {today.strftime('%d/%m/%Y')} :", ln=1)

cols = pivot.columns.tolist()
heure_col = cols[0]
capteurs = cols[1:]
n_blocs = math.ceil(len(capteurs) / 6)

for i in range(n_blocs):
    bloc_capteurs = capteurs[i*6:(i+1)*6]
    bloc_cols = [heure_col] + bloc_capteurs
    bloc_data = pivot[bloc_cols]


    pdf.set_fill_color(230, 230, 230)  # Gris clair
    pdf.set_text_color(0, 0, 0)        # Texte noir
    pdf.set_font("Arial", style='B', size=10)

    col_width = max(25, 180 // len(bloc_cols))
    for col in bloc_cols:
        pdf.cell(col_width, 8, col, 1, 0, 'C', True)
    pdf.ln()


    pdf.set_font("Arial", size=10)
    for _, row in bloc_data.iterrows():
        for val in row:
            pdf.cell(col_width, 8, str(val), 1)
        pdf.ln()

    pdf.ln(4)  

#graph
plt.figure(figsize=(10, 5))
for capteur in df_today["capteur"].unique():
    df_cap = df_today[df_today["capteur"] == capteur]
    plt.plot(df_cap["heure"], df_cap["temperature"], label=NOM_CAPTEURS.get(capteur, capteur))
plt.xlabel("Heure")
plt.ylabel("Température (°C)")
plt.title("Températures par capteur")
plt.legend()
plt.tight_layout()
graph_path = "data/graph_temp.png"
plt.savefig(graph_path)
plt.close()

#mail
msg = EmailMessage()
msg['Subject'] = f"Rapport Températures {today.strftime('%d/%m/%Y')}"
msg['From'] = SMTP_USER
msg['To'] = EMAIL_TO
msg.set_content("Veuillez trouver ci-joint le rapport des températures du jour.")

pdf.image(graph_path, x=10, y=None, w=180)
pdf_path = "data/rapport_temp.pdf"
pdf.output(pdf_path)

with open(pdf_path, "rb") as f:
    msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename="rapport_temp.pdf")

with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
    smtp.login(SMTP_USER, SMTP_PASS)
    smtp.send_message(msg)

print(f" Rapport envoyé à {EMAIL_TO}")