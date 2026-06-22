"""
Job Agent für Niloofar
Sucht Stellen via Web Scraping + AI Bewertung
Schickt Ergebnisse via Telegram
"""

import requests
import json
import os
import hashlib
from datetime import datetime
from anthropic import Anthropic

# ─────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────

ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY")
TELEGRAM_TOKEN     = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
GESEHENE_DATEI     = "gesehene_jobs.json"

# ─────────────────────────────────────────────
# SUCHBEGRIFFE — Agent sucht diese via Web
# ─────────────────────────────────────────────

SUCHEN = [
    "Projektkoordinator Berlin Vollzeit Stelle",
    "Projektassistenz Berlin Job",
    "Office Manager Berlin Stelle",
    "Koordination Kultur Berlin Job",
    "Veranstaltungskoordination Berlin Vollzeit",
    "Eventkoordinator Berlin Stelle",
    "GIZ Koordinator Berlin Stelle",
    "Goethe Institut Stelle Koordination",
    "Festivalkoordination Berlin Job",
    "Kulturmanagement Berlin Stelle Vollzeit",
]

# ─────────────────────────────────────────────
# PROFIL
# ─────────────────────────────────────────────

PROFIL = """
Du bist ein Job-Matching-Agent für folgende Kandidatin:

NAME: Niloofar Sojoodi
ZIEL: Projektkoordinatorin / Junior Project Manager in Berlin
SPRACHEN: Deutsch (C1), Englisch (C1), Persisch (Muttersprache)
AKTUELL: Marketing & Operations Koordinatorin bei Kanlog (Frankfurt), MA American Studies (Mainz)

ERFAHRUNG:
- Schichtplanung für 30+ Mitarbeiter, Partnerkoordination, monatliches Reporting
- Office & Projektkoordinatorin bei Tadbir Petro Energy (Teheran), inkl. internationale Messeeinsätze
- Ehrenamtliche Kulturveranstaltungskoordination (Ausstellungen, Filmabende, Panels)
- Tools: Google Workspace, Factorial, SharePoint, Canva, MS Office

BEVORZUGTE ARBEITGEBER:
- Kulturinstitutionen (Berlinale, Goethe-Institut, Berliner Festspiele)
- Internationale Organisationen (GIZ, UN Women, Bertelsmann Stiftung)
- Öffentlicher Dienst (TVöD)
- Eventproduktion, Festivalkoordination
- Musik/Entertainment (Techno/elektronische Musik)

HARD FILTERS — sofort ablehnen:
- Reine PR/Redaktion/Copywriting
- B2B Sales mit Quota
- Sicherheitsrelevant (BND etc.)
- Nur Frankfurt, kein Remote/Berlin
- Senior-Level mit 5+ Jahren zwingend
- Reine NGO unter ~35k
- Werkstudent:in

POSITIVE SIGNALE:
- Berlin oder Remote
- Koordination, Operations, Projektassistenz, Office Management
- Mehrsprachigkeit erwünscht
- Kultur, internationale Organisationen, Events
- TVöD / öffentlicher Dienst
- Eintrittslevel bis 3 Jahre Erfahrung
"""

# ─────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────

def lade_gesehene_jobs():
    if os.path.exists(GESEHENE_DATEI):
        with open(GESEHENE_DATEI, "r") as f:
            return set(json.load(f))
    return set()

def speichere_gesehene_jobs(gesehen):
    with open(GESEHENE_DATEI, "w") as f:
        json.dump(list(gesehen), f)

def job_id(job):
    return hashlib.md5((job.get("titel", "") + job.get("link", "")).encode()).hexdigest()

def sende_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    r = requests.post(url, json=data)
    if r.status_code == 200:
        print("✅ Telegram gesendet")
    else:
        print(f"❌ Telegram Fehler: {r.text}")

def suche_jobs_mit_ai(suchbegriffe):
    """Nutzt Claude mit Web Search um echte Stellenanzeigen zu finden"""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    alle_jobs = []
    
    for suchbegriff in suchbegriffe:
        print(f"🔍 Suche: {suchbegriff}")
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{
                    "role": "user",
                    "content": f"""Suche nach aktuellen Stellenanzeigen für: "{suchbegriff}"
                    
Finde 3-5 echte, aktuelle Stellenanzeigen (nicht älter als 30 Tage).
Antworte NUR mit einem JSON-Array, kein Text davor oder danach:
[
  {{
    "titel": "Jobtitel",
    "unternehmen": "Firmenname",
    "link": "URL zur Stelle",
    "beschreibung": "Kurze Beschreibung der Stelle (2-3 Sätze)"
  }}
]

Nur echte Stellenanzeigen. Keine Blogposts oder Nachrichtenartikel."""
                }]
            )
            
            # Text aus Antwort extrahieren
            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text
            
            # JSON extrahieren
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                jobs = json.loads(text[start:end])
                for job in jobs:
                    job["suchbegriff"] = suchbegriff
                    alle_jobs.append(job)
                print(f"  → {len(jobs)} Stellen gefunden")
        except Exception as e:
            print(f"  ❌ Fehler: {e}")
    
    return alle_jobs

def bewerte_job(job):
    """Bewertet einen einzelnen Job gegen das Profil"""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""
{PROFIL}

Bewerte diese Stelle:
TITEL: {job.get('titel', '')}
UNTERNEHMEN: {job.get('unternehmen', '')}
BESCHREIBUNG: {job.get('beschreibung', '')}

Antworte NUR mit JSON:
{{
  "empfehlung": "✅ Bewerben" oder "⚠️ Vielleicht" oder "❌ Skip",
  "begruendung": "1 Satz warum",
  "prioritaet": 1 bis 3
}}"""
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except:
        return {"empfehlung": "⚠️ Vielleicht", "begruendung": "Konnte nicht bewertet werden.", "prioritaet": 2}

# ─────────────────────────────────────────────
# HAUPTPROGRAMM
# ─────────────────────────────────────────────

def main():
    heute = datetime.now().strftime("%d.%m.%Y")
    print(f"\n🤖 Job-Agent startet — {heute}\n")

    gesehen = lade_gesehene_jobs()

    # Jobs suchen
    alle_jobs = suche_jobs_mit_ai(SUCHEN)
    print(f"\n📋 Gesamt gefunden: {len(alle_jobs)}")

    # Duplikate filtern
    neue_jobs = []
    for job in alle_jobs:
        jid = job_id(job)
        if jid not in gesehen:
            neue_jobs.append(job)
            gesehen.add(jid)
    
    print(f"🆕 Davon neu: {len(neue_jobs)}")

    if not neue_jobs:
        sende_telegram(f"🔍 Job-Agent {heute}\n\nKeine neuen Stellen heute.")
        return

    # Jobs bewerten
    print("\n🧠 Bewerte Jobs...\n")
    bewerbungen = []
    vielleicht = []
    
    for job in neue_jobs:
        bewertung = bewerte_job(job)
        job.update(bewertung)
        
        if job["empfehlung"] == "✅ Bewerben":
            bewerbungen.append(job)
        elif job["empfehlung"] == "⚠️ Vielleicht":
            vielleicht.append(job)

    # Telegram Nachrichten senden
    # Zusammenfassung
    sende_telegram(
        f"🔍 <b>Job-Agent — {heute}</b>\n\n"
        f"📊 {len(neue_jobs)} neue Stellen analysiert\n"
        f"✅ {len(bewerbungen)} zum Bewerben\n"
        f"⚠️ {len(vielleicht)} vielleicht\n\n"
        f"Details folgen gleich 👇"
    )

    # Bewerbungen
    if bewerbungen:
        for job in bewerbungen[:5]:  # max 5
            text = (
                f"✅ <b>{job.get('titel', '')}</b>\n"
                f"🏢 {job.get('unternehmen', '')}\n"
                f"💬 {job.get('begruendung', '')}\n"
                f"🔗 <a href='{job.get('link', '')}'>Zur Stelle</a>"
            )
            sende_telegram(text)

    # Vielleicht
    if vielleicht:
        for job in vielleicht[:3]:  # max 3
            text = (
                f"⚠️ <b>{job.get('titel', '')}</b>\n"
                f"🏢 {job.get('unternehmen', '')}\n"
                f"💬 {job.get('begruendung', '')}\n"
                f"🔗 <a href='{job.get('link', '')}'>Zur Stelle</a>"
            )
            sende_telegram(text)

    speichere_gesehene_jobs(gesehen)
    print("\n✅ Fertig!\n")

if __name__ == "__main__":
    main()
