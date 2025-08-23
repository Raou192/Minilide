# Projet Minilide – Suivi Automatisé de Températures

## Description

Minilide est un système de relevé, visualisation et envoi automatisé des températures mesurées par un appareil local accessible via une interface HTML.  
Le projet permet de :

- Extraire automatiquement les températures de l'appareil Minilide
- Générer un fichier CSV journalier
- Afficher les relevés via une interface web (NiceGUI)
- Envoyer un rapport quotidien par email avec graphique et tableau
- Déclencher une alerte Pushbullet en cas de variation brutale (+-5°C)

## Arborescence du projet

```
minilide/
│
├── data/
│   ├── temperatures.csv         ← Données collectées
│   └── graph_temp.png           ← Image générée pour l’email/PDF
│
├── extract_minilide.py         ← Script principal de collecte
├── interface.py                ← Interface graphique web (NiceGUI)
├── send_report.py              ← Génération + envoi du rapport par mail
├── .env                        ← Fichier de configuration (non partagé)
├── requirements.txt            ← Dépendances Python
└── README.md                   ← Ce fichier
```

## Configuration .env

Crée un fichier `.env` à la racine du projet avec ce contenu :

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=votre_mail
SMTP_PASS=mot_de_passe_application
EMAIL_TO=votre_mail
PUSHBULLET_TOKEN=Token_Push_Bullet
```

Utilise un mot de passe d'application Gmail 
https://myaccount.google.com/apppasswords

## Installation

1. Installer Python 3.9+
2. Crée un environnement virtuel :

```
python -m venv venv
venv\Scripts\activate  # Windows
```

3. Installer les dépendances :

```
pip install -r requirements.txt
```

## Lancement

1. Récupérer les données :

```
python extract_minilide.py
```

2. Afficher l’interface graphique :

```
python interface.py
# → http://localhost:8081
```

3. Envoyer le rapport par email (graphique + PDF) :

```
python send_report.py
```

## Fonctionnalités

- Lecture HTML à partir de `http://192.168.10.107`
- Écriture CSV automatique dans `/data`
- Interface NiceGUI avec graphique dynamique filtrable par date
- Rapport PDF avec résumé des températures
- Alerte Pushbullet si variation brutale (seuil : ±5°C)
- Intégration facile via planificateur de tâches