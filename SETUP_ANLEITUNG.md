# 🤖 Job-Agent Setup — Schritt für Schritt

Dieser Guide führt dich durch das komplette Setup.
Kein Programmierwissen nötig — alles copy-paste.

Dauer: ca. 30–45 Minuten

---

## Was du am Ende hast

Jeden Morgen um 8 Uhr bekommst du eine E-Mail mit:
- ✅ Stellen zum sofort Bewerben
- ⚠️ Stellen die vielleicht passen
- Jede mit direktem Link und kurzer Begründung

Keine doppelten Stellen — der Agent merkt sich was er schon geschickt hat.

---

## Schritt 1 — GitHub Account erstellen

GitHub ist wo dein Code gespeichert wird. Kostenlos.

1. Geh zu https://github.com
2. Klick "Sign up"
3. E-Mail, Passwort, Username eingeben
4. Kostenlosen Plan wählen
5. E-Mail bestätigen

---

## Schritt 2 — Render Account erstellen

Render ist der Server wo der Agent täglich läuft. Kostenlos.

1. Geh zu https://render.com
2. Klick "Get Started for Free"
3. Melde dich mit deinem GitHub Account an (einfacher)

---

## Schritt 3 — Anthropic API Key holen

Der Agent braucht einen Key um Claude nutzen zu können.

1. Geh zu https://console.anthropic.com
2. Account erstellen (oder einloggen)
3. Links auf "API Keys" klicken
4. "Create Key" klicken
5. Den Key kopieren und irgendwo sicher speichern
   (sieht so aus: sk-ant-api03-xxxxx...)

⚠️ Kosten: ca. 0,50–2€ pro Monat bei täglicher Nutzung.
   Du bekommst am Anfang Gratis-Credits.

---

## Schritt 4 — Gmail App-Passwort erstellen

Der Agent braucht ein spezielles Passwort um E-Mails zu senden.
(Nicht dein normales Gmail-Passwort)

1. Geh zu https://myaccount.google.com
2. Klick auf "Sicherheit" (links)
3. Scroll zu "2-Schritt-Verifizierung" — muss aktiviert sein
   (falls nicht: aktiviere es zuerst)
4. Scroll weiter zu "App-Passwörter"
5. Klick darauf
6. Wähle App: "E-Mail", Gerät: "Sonstiges"
7. Gib ein: "Job Agent"
8. Klick "Erstellen"
9. Das 16-stellige Passwort kopieren und speichern
   (sieht so aus: xxxx xxxx xxxx xxxx)

---

## Schritt 5 — Code auf GitHub hochladen

1. Geh zu https://github.com
2. Klick auf "+" oben rechts → "New repository"
3. Name: "job-agent"
4. Wähle "Private"
5. Klick "Create repository"

Jetzt die zwei Dateien hochladen:

6. Klick "uploading an existing file"
7. Lade job_agent.py hoch
8. Lade requirements.txt hoch
9. Klick "Commit changes"

---

## Schritt 6 — Agent auf Render deployen

1. Geh zu https://render.com (eingeloggt)
2. Klick "New +" → "Cron Job"
3. Verbinde dein GitHub Repository (job-agent)
4. Einstellungen:

   Name:          job-agent
   Runtime:       Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python job_agent.py
   Schedule:      0 7 * * *
   (= jeden Tag um 8 Uhr deutscher Zeit)

5. Scroll zu "Environment Variables" und füge hinzu:

   ANTHROPIC_API_KEY  →  dein Anthropic Key (sk-ant-...)
   EMAIL_ABSENDER     →  deine Gmail-Adresse
   EMAIL_PASSWORT     →  das 16-stellige App-Passwort
   EMAIL_EMPFAENGER   →  deine E-Mail-Adresse (kann dieselbe sein)

6. Klick "Create Cron Job"

---

## Schritt 7 — Testen

1. Auf Render: klick auf deinen Job-Agent
2. Klick "Trigger Run" (oben rechts)
3. Warte 2–3 Minuten
4. Schau in dein E-Mail-Postfach

Falls keine E-Mail kommt:
- Schau in den "Logs" auf Render — da siehst du Fehlermeldungen
- Häufigste Fehler: falsches App-Passwort, falscher API Key

---

## Schritt 8 — Fertig!

Ab jetzt läuft der Agent jeden Morgen automatisch.
Du musst nichts mehr tun — außer die E-Mail lesen und entscheiden.

---

## Plattformen die durchsucht werden

| Plattform | Was gesucht wird |
|---|---|
| Interamt | Koordination, Projektassistenz, Veranstaltung in Berlin |
| Epojobs | Koordination, Projektassistenz (international) |
| Kulturjobs.de | Koordination in Berlin |
| Karriereportal Berlin | Koordination Berlin |

LinkedIn: leider nicht automatisierbar — 10 Min täglich manuell.

---

## Kosten Übersicht

| Service | Kosten |
|---|---|
| GitHub | Kostenlos |
| Render (Cron Job) | Kostenlos |
| Anthropic API | ~0,50–2€/Monat |
| Gmail | Kostenlos |

---

## Häufige Fragen

**Der Agent schickt mir Stellen die ich schon kenne.**
Normal beim ersten Mal — danach merkt er sich alles.

**Ich will mehr/andere Plattformen hinzufügen.**
In job_agent.py unter RSS_FEEDS einen neuen Eintrag hinzufügen.

**Ich will die Uhrzeit ändern.**
Auf Render den Schedule ändern: 0 6 * * * = 7 Uhr, 0 8 * * * = 9 Uhr.

**Ich will auch Frankfurt-Stellen sehen.**
In job_agent.py bei den RSS_FEEDS die Suchanfragen anpassen.
