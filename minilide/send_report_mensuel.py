#!/usr/bin/env python3
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
from fpdf import FPDF
import matplotlib.pyplot as plt

load_dotenv()

# --- Chemins / SMTP / Destinataires ---
CSV_MIRROR = "data/temperatures.csv"   # miroir du mois courant (secours)
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

# --- Libellés capteurs (adapter si besoin) ---
NOM_CAPTEURS = {f"Capteur {i}": f"Capteur {i}" for i in range(1, 17)}

def month_csv_path(dt: datetime) -> str:
    """Chemin du CSV mensuel pour une date donnée."""
    return os.path.join("data", f"temperatures_{dt.strftime('%m-%Y')}.csv")

def load_month_dataframe() -> pd.DataFrame:
    """
    Charge le CSV du mois courant. Si absent (début de mois), bascule sur le miroir.
    Valide les colonnes, parse dates et températures.
    """
    now = datetime.now()
    mpath = month_csv_path(now)

    if os.path.exists(mpath) and os.path.getsize(mpath) > 0:
        print(f"[INFO] Lecture du CSV mensuel : {mpath}")
        df = pd.read_csv(mpath)
    else:
        if not (os.path.exists(CSV_MIRROR) and os.path.getsize(CSV_MIRROR) > 0):
            raise SystemExit("[ERREUR] Aucun CSV disponible (ni mensuel, ni miroir).")
        print(f"[WARN] CSV mensuel introuvable, fallback sur {CSV_MIRROR}")
        df = pd.read_csv(CSV_MIRROR)

    expected = {"timestamp", "capteur", "temperature"}
    missing = expected - set(df.columns)
    if missing:
        raise SystemExit(f"[ERREUR] Colonnes manquantes dans le CSV : {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df = df.dropna(subset=["timestamp"])  # on garde les lignes avec timestamp valide
    return df

def build_month_stats(df: pd.DataFrame):
    """
    Calcule les stats par capteur sur tout le mois :
    n / min / max / moyenne / dernière valeur.
    Retourne: stats_capteurs (DataFrame), df_all (DataFrame trié).
    """
    df_all = df.copy().sort_values("timestamp")

    # Dernière valeur par capteur
    last_vals = (
        df_all.dropna(subset=["temperature"])
              .groupby("capteur", as_index=True)
              .tail(1)
              .set_index("capteur")["temperature"]
    )

    grouped = df_all.groupby("capteur")["temperature"]
    stats_capteurs = pd.DataFrame({
        "n": grouped.count(),
        "min": grouped.min(),
        "max": grouped.max(),
        "mean": grouped.mean().round(2),
        "last": last_vals
    }).sort_index()

    # Remap noms capteurs
    pretty_index = [NOM_CAPTEURS.get(c, c) for c in stats_capteurs.index]
    stats_capteurs.index = pretty_index

    return stats_capteurs, df_all

def render_pdf_month(stats_caps: pd.DataFrame, df_all: pd.DataFrame, out_pdf: str):
    """
    Génére un PDF mensuel avec :
      - Titre / période
      - Tableau de synthèse (n / min / max / moy) avec en-tête coloré
      - Graph global des températures du mois (légende à droite)
    """
    now = datetime.now()
    periode = now.strftime("%m/%Y")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=12)

    # --- Titre ---
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Rapport mensuel - Températures", ln=1)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Période : {periode}", ln=1)

    # --- Tableau synthèse ---
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Synthèse par capteur (mois)", ln=1)

    # En-tête colorée (bleu) + texte blanc
    pdf.set_fill_color(60, 100, 180)   # bleu
    pdf.set_text_color(255, 255, 255)  # blanc
    pdf.set_font("Arial", 'B', 10)

    headers = ["Capteur", "n", "min", "max", "moy"]
    col_w = [60, 20, 25, 25, 25]

    for w, h in zip(col_w, headers):
        pdf.cell(w, 8, h, 1, 0, 'C', True)
    pdf.ln()

    # Lignes normales (texte noir)
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(0, 0, 0)

    for capteur, row in stats_caps.iterrows():
        pdf.cell(col_w[0], 8, str(capteur), 1)
        pdf.cell(col_w[1], 8, str(int(row["n"])) if pd.notna(row["n"]) else "—", 1, 0, 'C')
        pdf.cell(col_w[2], 8, f"{row['min']:.1f}" if pd.notna(row["min"]) else "—", 1, 0, 'C')
        pdf.cell(col_w[3], 8, f"{row['max']:.1f}" if pd.notna(row["max"]) else "—", 1, 0, 'C')
        pdf.cell(col_w[4], 8, f"{row['mean']:.1f}" if pd.notna(row["mean"]) else "—", 1, 0, 'C')
        pdf.ln()

    # --- Graph global (températures du mois) ---
    graph_path = "data/graph_temp_month.png"
    plt.figure(figsize=(10, 5))
    for capteur in df_all["capteur"].dropna().unique():
        df_cap = df_all[df_all["capteur"] == capteur].sort_values("timestamp")
        label = NOM_CAPTEURS.get(capteur, capteur)
        plt.plot(df_cap["timestamp"], df_cap["temperature"], label=label)
    plt.xlabel("Date/Heure")
    plt.ylabel("Température (°C)")
    plt.title(f"Évolution des températures – {periode}")

    # Légende déplacée à droite (hors du tracé)
    plt.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), borderaxespad=0.)
    # Laisser de la place à droite
    plt.subplots_adjust(right=0.78)

    plt.tight_layout()
    plt.savefig(graph_path, bbox_inches="tight")
    plt.close()

    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Graphique mensuel", ln=1)
    try:
        pdf.image(graph_path, x=10, y=None, w=180)
    except Exception:
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 7, "Graphique indisponible.", ln=1)

    pdf.output(out_pdf)

def send_email_with_attachment(pdf_path: str, subject: str, body: str):
    """Envoie l'email avec la PJ PDF."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg.set_content(body)

    with open(pdf_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf",
                           filename=os.path.basename(pdf_path))

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)

def main():
    df = load_month_dataframe()
    if df.empty:
        raise SystemExit("[INFO] Aucun relevé pour ce mois.")

    stats_caps, df_all = build_month_stats(df)

    os.makedirs("data", exist_ok=True)
    now = datetime.now()
    periode = now.strftime("%m-%Y")
    pdf_path = f"data/rapport_temp_{periode}.pdf"

    render_pdf_month(stats_caps, df_all, pdf_path)

    subject = f"Rapport Températures – {periode}"
    body = f"Veuillez trouver ci-joint le rapport mensuel des températures ({periode})."
    send_email_with_attachment(pdf_path, subject, body)
    print(f"[OK] Rapport mensuel envoyé à {EMAIL_TO} : {pdf_path}")

if __name__ == "__main__":
    main()