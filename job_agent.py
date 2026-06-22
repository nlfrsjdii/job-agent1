"""
Job Agent für Niloofar
Liest RSS-Feeds von Interamt, Epojobs, Kulturjobs, Karriereportal Berlin
Bewertet jeden Job gegen dein Profil
Schickt täglich eine E-Mail mit den Ergebnissen
"""

import feedparser
import smtplib
import json
import os
import hashlib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from anthropic import Anthropic

# ─────────────────────────────────────────────
# KONFIGURATION — hier anpassen
# ─────────────────────────────────────────────

EMAIL_ABSENDER    = os.environ.get("EMAIL_ABSENDER")     # deine Gmail-Adresse
EMAIL_PASSWORT    = os.environ.get("EMAIL_PASSWORT")     # Gmail App-Passwort
EMAIL_EMPFAENGER  = os.environ.get("EMAIL_EMPFAENGER")   # wohin die E-Mail geht
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")  # Anthropic API Key
GESEHENE_DATEI    = "gesehene_jobs.json"                 # speichert bereits gesehene Stellen

# ─────────────────────────────────────────────
# RSS FEEDS
# ─────────────────────────────────────────────

RSS_FEEDS = [
    {
        "name": "Interamt — Koordination Berlin",
        "url": "https://www.interamt.de/koop/app/trefferliste?stellenangebotsart=0&behoerde=&land=&ort=Berlin&berufsfeld=&suche=Koordination&umkreis=0&format=rss"
    },
    {
        "name": "Interamt — Projektassistenz Berlin",
        "url": "https://www.interamt.de/koop/app/trefferliste?stellenangebotsart=0&behoerde=&land=&ort=Berlin&berufsfeld=&suche=Projektassistenz&umkreis=0&format=rss"
    },
    {
        "name": "Interamt — Veranstaltung Berlin",
        "url": "https://www.interamt.de/koop/app/trefferliste?stellenangebotsart=0&behoerde=&land=&ort=Berlin&berufsfeld=&suche=Veranstaltung&umkreis=0&format=rss"
    },
    {
        "name": "Epojobs — Koordination",
        "url": "https://www.epojobs.eu/index.php?option=com_jobboard&view=jobs&format=feed&type=rss&searchword=koordination"
    },
    {
        "name": "Epojobs — Projektassistenz",
        "url": "https://www.epojobs.eu/index.php?option=com_jobboard&view=jobs&format=feed&type=rss&searchword=projektassistenz"
    },
    {
        "name": "Kulturjobs — Berlin",
        "url": "https://www.kulturjobs.de/jobs/rss/?q=koordination&location=Berlin"
    },
    {
        "name": "Karriereportal Berlin — Koordination",
        "url": "https://karriereportal-stellen.berlin.de/suche?facets=%7B%7D&query=koordination&format=rss"
    },
]

# ─────────────────────────────────────────────
# PROFIL — wird dem AI-Agenten übergeben
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
- Ehrenamtliche Kulturveranstaltungskoordination (Ausstellungen, Filmbende, Panels)
- Tools: Google Workspace, Factorial, SharePoint, Canva, MS Office

BEVORZUGTE ARBEITGEBER:
- Kulturinstitutionen (Berlinale, Goethe-Institut, Berliner Festspiele)
- Internationale Organisationen (GIZ, UN Women, Bertelsmann Stiftung)
- Öffentlicher Dienst (TVöD)
- Eventproduktion, Festivalkoordination
- Musik/Entertainment (echte persönliche Affinität zu Techno/elektronischer Musik)

HARD FILTERS — sofort ablehnen wenn:
- Reine PR/Redaktion/Copywriting-Rolle (erfordert muttersprachliches Schreiben auf Deutsch)
- B2B Sales mit Quota
- Sicherheitsrelevant (BND, Verfassungsschutz) — erfordert deutsche Staatsbürgerschaft
- Nur Frankfurt, kein Remote/Berlin
- Senior-Level mit 5+ Jahren Erfahrung zwingend erforderlich
- Reine NGO mit sehr niedrigem Gehalt (unter ~35k)
- Werkstudent:in (sie arbeitet bereits Vollzeit)

POSITIVE SIGNALE — höheres Ranking:
- Berlin oder Remote
- Koordination, Operations, Projektassistenz, Office Management
- Mehrsprachigkeit erwünscht
- Kultur, internationale Organisationen, Medien, Events
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

def lese_feeds():
    alle_jobs = []
    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:15]:  # max 15 pro Feed
                alle_jobs.append({
                    "quelle": feed_info["name"],
                    "titel": entry.get("title", "Kein Titel"),
                    "link": entry.get("link", ""),
                    "beschreibung": entry.get("summary", "")[:500],
                    "datum": entry.get("published", "")
                })
            print(f"✅ {feed_info['name']}: {len(feed.entries)} Einträge")
        except Exception as e:
            print(f"❌ Fehler bei {feed_info['name']}: {e}")
    return alle_jobs

def bewerte_jobs_mit_ai(jobs):
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    bewertete = []

    for job in jobs:
        prompt = f"""
{PROFIL}

Bewerte diese Stellenanzeige für die Kandidatin:

TITEL: {job['titel']}
QUELLE: {job['quelle']}
BESCHREIBUNG: {job['beschreibung']}
LINK: {job['link']}

Antworte NUR mit einem JSON-Objekt, kein Text davor oder danach:
{{
  "empfehlung": "✅ Bewerben" oder "⚠️ Vielleicht" oder "❌ Skip",
  "begruendung": "1-2 Sätze warum",
  "prioritaet": 1 bis 3 (1=hoch, 3=niedrig)
}}
"""
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text.strip()
            # JSON aus Antwort extrahieren
            start = text.find("{")
            end = text.rfind("}") + 1
            bewertung = json.loads(text[start:end])
            job.update(bewertung)
            bewertete.append(job)
        except Exception as e:
            print(f"⚠️ Bewertungsfehler für '{job['titel']}': {e}")
            job.update({"empfehlung": "⚠️ Vielleicht", "begruendung": "Konnte nicht bewertet werden.", "prioritaet": 2})
            bewertete.append(job)

    # Sortieren: zuerst ✅, dann ⚠️, dann ❌, innerhalb nach Priorität
    reihenfolge = {"✅ Bewerben": 0, "⚠️ Vielleicht": 1, "❌ Skip": 2}
    bewertete.sort(key=lambda j: (reihenfolge.get(j.get("empfehlung", "⚠️"), 1), j.get("prioritaet", 2)))
    return bewertete

def erstelle_email_html(jobs):
    heute = datetime.now().strftime("%d.%m.%Y")
    bewerben = [j for j in jobs if j.get("empfehlung") == "✅ Bewerben"]
    vielleicht = [j for j in jobs if j.get("empfehlung") == "⚠️ Vielleicht"]

    def job_karte(job, farbe, emoji):
        return f"""
        <div style="border-left: 4px solid {farbe}; padding: 12px 16px; margin: 12px 0; background: #f9f9f9; border-radius: 4px;">
            <strong>{emoji} {job['titel']}</strong><br>
            <small style="color: #666;">📍 {job['quelle']}</small><br>
            <p style="margin: 8px 0; font-size: 14px;">{job.get('begruendung', '')}</p>
            <a href="{job['link']}" style="color: #1a73e8; font-size: 13px;">→ Zur Stelle</a>
        </div>
        """

    bewerben_html = "".join([job_karte(j, "#34a853", "✅") for j in bewerben]) if bewerben else "<p style='color:#999'>Keine heute.</p>"
    vielleicht_html = "".join([job_karte(j, "#fbbc04", "⚠️") for j in vielleicht]) if vielleicht else "<p style='color:#999'>Keine heute.</p>"

    return f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 680px; margin: auto; padding: 24px; color: #333;">
        <h2 style="border-bottom: 2px solid #1a73e8; padding-bottom: 8px;">
            🔍 Job-Agent — {heute}
        </h2>
        <p>{len(jobs)} neue Stellen gefunden · {len(bewerben)} zum Bewerben · {len(vielleicht)} vielleicht</p>

        <h3 style="color: #34a853;">✅ Direkt bewerben ({len(bewerben)})</h3>
        {bewerben_html}

        <h3 style="color: #f9a825;">⚠️ Vielleicht ({len(vielleicht)})</h3>
        {vielleicht_html}

        <hr style="margin-top: 32px; border: none; border-top: 1px solid #eee;">
        <p style="color: #999; font-size: 12px;">Job-Agent · Automatisch generiert · {heute}</p>
    </body></html>
    """

def sende_email(html_inhalt, anzahl_jobs):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔍 Job-Agent: {anzahl_jobs} neue Stellen — {datetime.now().strftime('%d.%m.%Y')}"
    msg["From"] = EMAIL_ABSENDER
    msg["To"] = EMAIL_EMPFAENGER
    msg.attach(MIMEText(html_inhalt, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ABSENDER, EMAIL_PASSWORT)
        server.sendmail(EMAIL_ABSENDER, EMAIL_EMPFAENGER, msg.as_string())
    print("✅ E-Mail gesendet!")

# ─────────────────────────────────────────────
# HAUPTPROGRAMM
# ─────────────────────────────────────────────

def main():
    print(f"\n🤖 Job-Agent startet — {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")

    # 1. Bereits gesehene Jobs laden
    gesehen = lade_gesehene_jobs()

    # 2. Feeds lesen
    alle_jobs = lese_feeds()
    print(f"\n📋 Gesamt gefunden: {len(alle_jobs)} Jobs")

    # 3. Nur neue Jobs filtern
    neue_jobs = [j for j in alle_jobs if job_id(j) not in gesehen]
    print(f"🆕 Davon neu: {len(neue_jobs)} Jobs\n")

    if not neue_jobs:
        print("Keine neuen Jobs heute. Fertig.")
        return

    # 4. Mit AI bewerten
    print("🧠 Bewerte Jobs mit AI...\n")
    bewertete_jobs = bewerte_jobs_mit_ai(neue_jobs)

    # 5. Nur relevante Jobs in E-Mail (kein ❌)
    relevante_jobs = [j for j in bewertete_jobs if j.get("empfehlung") != "❌ Skip"]
    print(f"\n📬 Relevante Jobs für E-Mail: {len(relevante_jobs)}")

    # 6. E-Mail senden
    if relevante_jobs:
        html = erstelle_email_html(relevante_jobs)
        sende_email(html, len(relevante_jobs))
    else:
        print("Keine relevanten Jobs heute — keine E-Mail.")

    # 7. Gesehene Jobs speichern
    for job in neue_jobs:
        gesehen.add(job_id(job))
    speichere_gesehene_jobs(gesehen)

    print("\n✅ Fertig!\n")

if __name__ == "__main__":
    main()
