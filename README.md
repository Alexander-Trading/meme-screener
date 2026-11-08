# Meme-Screener mit Musterdepot

Prüft einmal täglich neue und trendende Meme-Coins auf **Solana** und **Base**, filtert Betrugsverdacht heraus, vergibt einen Score (0–100), führt ein **fiktives Musterdepot** und schickt dir die Ergebnisse per Telegram. Läuft kostenlos auf GitHub, ohne PC und ohne API-Keys.

> Keine Anlageberatung. Das Depot ist rein fiktiv und dient nur dazu, die Regeln ehrlich zu überprüfen.

## Einrichtung (ca. 15 Minuten, geht auch am Handy)

### 1. GitHub-Repository anlegen
1. Kostenloses Konto auf github.com anlegen.
2. Neues Repository erstellen, z. B. `meme-screener`, Sichtbarkeit **Public** (für kostenlose GitHub Pages; der Inhalt ist unkritisch). Private geht auch, dann aber ohne Pages.
3. Alle Dateien aus diesem Ordner hochladen („Add file → Upload files“). Wichtig: Der Ordner `.github/workflows/` mit `daily.yml` muss mit hoch.

### 2. Telegram-Bot (optional, empfohlen)
1. In Telegram **@BotFather** öffnen, `/newbot` senden, Namen vergeben → du bekommst einen **Token**.
2. Deinem neuen Bot eine beliebige Nachricht schicken.
3. Im Browser `https://api.telegram.org/bot<TOKEN>/getUpdates` öffnen und bei `"chat":{"id": …}` die **Chat-ID** ablesen.
4. Im Repository: **Settings → Secrets and variables → Actions → New repository secret**
   - `TELEGRAM_BOT_TOKEN` = der Token
   - `TELEGRAM_CHAT_ID` = die Chat-ID

### 3. Dashboard (GitHub Pages)
**Settings → Pages → Source: „Deploy from a branch“, Branch `main`, Ordner `/docs`** → Speichern.
Nach dem ersten Lauf ist das Dashboard unter `https://<dein-name>.github.io/meme-screener/` erreichbar.

### 4. Starten
**Actions → „Taeglicher Meme-Screener“ → Run workflow.** Danach läuft er automatisch: morgens gegen 7:45/8:45 Uhr der Hauptlauf (Depot + Telegram), dazu drei Sammelläufe am Tag, die nur Daten speichern. Ein manueller Start nach 6/7 Uhr deutscher Zeit gilt als Hauptlauf, solange es an dem Tag noch keinen gab.

## So arbeitet der Screener

1. **Sammeln:** neue Profile, Boosts und Community-Takeovers von DEX Screener sowie trendende und umsatzstarke Pools von GeckoTerminal.
2. **Basisfilter:** 3–120 Tage alt, Liquidität ≥ 30.000 $, Marktkapitalisierung 0,1–50 Mio. $, ≥ 150 Transaktionen am Tag.
3. **Sicherheit:** Solana über RugCheck, Base über GoPlus. Ausschluss bei aktivem Mint/Freeze, Honeypot, hohen Steuern, Rug-Markierung, gefährlichen Risiken oder wenn die Top-10-Wallets über 35 % halten.
4. **Score:** Alter (Überlebende 14–60 Tage bevorzugt), Liquidität und deren Verhältnis zur MCap, Volumen/Liquidität (Wash-Trading-Warnung), Kaufdruck, Aktivität, Trend ohne Pump-Hinterherlaufen, Socials, Holderzahl und **Holderwachstum über 7 Tage** (aus eigenen täglichen Snapshots, wirkt also ab ca. Tag 2–8 voll).
5. **Musterdepot:** Startkapital 10.000 € fiktiv. Pro Tag bis zu 3 Käufe à 100 € für Kandidaten mit Score ≥ 65 und bestandenem Sicherheitscheck. Gewinnmitnahme: ⅓ bei 3x, die Hälfte des Rests bei 10x. Stop-Loss −70 %, Verkauf nach spätestens 90 Tagen. Verschwindet die Liquidität, zählt die Position als Totalverlust.
   Zusätzliche Ausstiege (`exits` in `config.json`): Trailing Stop (ab 2x, Rest raus bei −50 % vom Hoch), Liquidität −50 % seit gestern, negativer Sicherheitscheck (sofort raus), Holder −10 % in 7 Tagen (halbieren).
   Verkaufte Tokens werden unbegrenzt weiterverfolgt; das Dashboard zeigt Hoch und Kurs nach dem Verkauf und je Regel, ob sie Geld gerettet hat.

Alle Grenzen und Regeln stehen in `config.json` und lassen sich dort anpassen (z. B. `"chains": ["solana", "base", "bsc", "ethereum"]`).

## Dateien
- `screener.py` – Logik
- `dashboard.py` – erzeugt `docs/index.html`
- `config.json` – Filter, Score-Schwellen, Depot-Regeln
- `data/state.json` – Depot und letzter Lauf (wird automatisch gespeichert)
- `data/snapshots.json` – Verlauf je Token für das Holderwachstum
- `data/runs/JJJJ-MM-TT.json` – die sicherheitsgeprüften Kandidaten je Tag
- `data/raw/JJJJ-MM-TT_HH.json.gz` – Rohdaten **aller** gesehenen Tokens je Lauf (auch der aussortierten)
- `data/tokens/JJJJ-MM-TT.json.gz` – Tokens, die an diesem Tag zum ersten Mal gesehen wurden (Startmerkmale)
- `data/prices/JJJJ-MM-TT_HH.json.gz` – Kurse aller verfolgten Tokens je Lauf; jeder Token wird 180 Tage verfolgt, tote Tokens (7 Tage Liquidität < 1.000 $) nicht mehr
- `analyse.csv` – Merkmale am ersten Tag + Entwicklung nach 7/30/90 Tagen (Excel, Semikolon); nach jedem Hauptlauf unter **Actions → letzter Lauf → Artifacts** zum Download
- `analyze.py` – Zusammenfassung: Trefferquote (≥ 3x) und Ausfallquote nach Score, Alter und Filter

## Daten sammeln und auswerten
Weil ein Rückwärtstest mit kostenlosen Daten nicht sauber geht, baut der Screener sich seine eigene Datenbank auf: Jeder Token, der irgendwo auftaucht, wird mit seinen Startmerkmalen gespeichert und danach täglich weiterverfolgt – auch die, die durchfallen oder sterben. Nach 1–3 Monaten zeigt die Auswertung im Dashboard bzw. `analyse.csv`, welche Merkmale die späteren Gewinner am ersten Tag hatten und ob der Score funktioniert. Alle Datendateien werden nur einmal geschrieben, damit das Repository langsam wächst (grob 150–300 MB pro Jahr).

## Grenzen
- Die kostenlosen APIs können Felder ändern oder zeitweise drosseln; dann fallen einzelne Prüfungen aus und das Dashboard markiert „Sicherheit ungeprüft“.
- Ein echter Rückwärtstest ist mit kostenlosen Daten nicht sauber möglich (siehe Hinweis im Chat). Das Musterdepot ist deshalb ein Vorwärtstest ab dem ersten Lauf.
