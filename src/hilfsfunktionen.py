"""
Hilfsfunktionen fuer die Tender-Manager-Suche.

Pro Firma werden zwei Serper-Suchvarianten kombiniert (site: + freie Suche),
die Kandidaten-URLs direkt geladen und verifiziert. GPT wird nur fuer
Grenzfaelle zur Klassifikation eingesetzt, nicht zur Bewertung.
"""

import re
import time
from pathlib import Path
import os

import pandas as pd
import requests
from openai import OpenAI

# ---------------------------------------------------------------------------
# Zwei Konfidenz-Stufen statt einer flachen Keyword-Liste:
# - EXAKT: Begriff trifft die gesuchte Rolle 1:1 -> Konfidenz 100
# - VERWANDT: Begriff ist thematisch nah dran, aber nicht zwingend deckungs-
#   gleich (z.B. Oberbegriff oder verwandte Rolle) -> Konfidenz 75
# ---------------------------------------------------------------------------
KEYWORDS_EXAKT = [
    "Tender Management",
    "Tender Manager",
    "Bid Management",
    "Bid Manager",
    "Ausschreibungsmanagement",
    "Ausschreibungsmanager",
    "Angebotsmanagement",
    "Angebotsmanager",
]

KEYWORDS_VERWANDT = [
    "Business Development Logistik",
    "Head of Sales Logistik",
    "Vertriebsleiter Logistik",
    "Key Account Manager Logistik",
    "Strategic Sales",
    "Kontraktlogistik",
    "3PL / Third Party Logistics",
    "Supply Chain Solutions",
    "End-to-End Logistik",
    "Fulfillment",
    "Individuelle Logistiklösungen",
]

KEYWORD_KONFIDENZ = {kw.lower(): 100 for kw in KEYWORDS_EXAKT}
KEYWORD_KONFIDENZ.update({kw.lower(): 75 for kw in KEYWORDS_VERWANDT})
ALLE_KEYWORDS = KEYWORDS_EXAKT + KEYWORDS_VERWANDT

# Signalwoerter, die eine ECHTE, AKTIVE Stellenausschreibung von einer
# blossen Erwaehnung des Keywords unterscheiden (Jobboersen-Uebersichten,
# Agentur-Werbetexte etc. enthalten das Keyword oft auch, sind aber keine
# Anzeige der Firma selbst).
STELLENANZEIGE_SIGNALE = [
    "wir suchen", "jetzt bewerben", "stellenausschreibung", "stellenanzeige",
    "ihre aufgaben", "ihr profil", "bewerben sie sich", "offene stelle",
    "join our team", "apply now", "job description", "we are looking for",
]

def lade_key(name: str) -> str:
    """Liest einen API-Key aus os.environ; bricht mit klarer Meldung ab, falls er fehlt."""
    try:
        return os.environ[name]  # wie map.at() in C++: wirft KeyError, wenn der Name fehlt
    except KeyError:
        # name in der Meldung -> man sieht sofort, WELCHER Key fehlt
        raise SystemExit(f"Fehlender API-Key: {name} in .env eintragen")

def ausgabe_pfad(input_csv: Path, output_folder: str) -> Path:
    return Path(output_folder) / f"{input_csv.stem}_tenderManagerTreffer.csv"


def normalisiere_domain(url_oder_domain: str) -> str:
    """
    'https://www.spedition-muster.de/impressum' -> 'spedition-muster.de'
    Die site:-Suche braucht eine reine Domain, keine volle URL.
    """
    if not url_oder_domain or url_oder_domain.lower() in ("nan", "none"):
        return ""
    if not url_oder_domain.startswith("http"):
        url_oder_domain = "https://" + url_oder_domain
    netloc = re.sub(r"^https?://", "", url_oder_domain).split("/")[0]
    return netloc.replace("www.", "").strip()


def firmenliste_filtern(
    df: pd.DataFrame,
    min_mitarbeiter: int = 100,
    min_umsatz_mio: float = 25.0,
) -> pd.DataFrame:
    """
    Groessenkriterium: >= 100 Mitarbeiter ODER >= 25 Mio Euro Jahresumsatz.
    Falls die Spalten "Mitarbeiter"/"Umsatz_Mio" in der CSV fehlen (z.B. weil
    die Liste schon vorgefiltert aus North Data exportiert wurde -- Achtung,
    North Data verknuepft mehrere Kennzahlen-Filter selbst mit UND, nicht
    ODER, deshalb dort zwei separate Exports + hier zusammenfuehren),
    wird die Liste unveraendert durchgereicht.
    """
    hat_mitarbeiter_spalte = "Mitarbeiter" in df.columns
    hat_umsatz_spalte = "Umsatz_Mio" in df.columns

    if not hat_mitarbeiter_spalte and not hat_umsatz_spalte:
        return df

    mitarbeiter = pd.to_numeric(df.get("Mitarbeiter"), errors="coerce").fillna(0)
    umsatz = pd.to_numeric(df.get("Umsatz_Mio"), errors="coerce").fillna(0)
    maske = (mitarbeiter >= min_mitarbeiter) | (umsatz >= min_umsatz_mio)
    return df[maske].reset_index(drop=True)


# Domains, die in Suchergebnissen zu einer Firma haeufig auftauchen, aber
# NICHT die offizielle Firmenwebsite sind (Verzeichnisse, Jobportale,
# Netzwerke, Register) -- fuer die automatische Domain-Erkennung rausfiltern.
BLOCKLISTE_DOMAINS = [
    "linkedin.com", "xing.com", "kununu.com", "northdata.de", "northdata.com",
    "wlw.de", "europages.de", "unternehmensregister.de", "bundesanzeiger.de",
    "handelsregister.de", "indeed.com", "stepstone.de", "kimeta.de",
    "jobware.de", "wikipedia.org", "facebook.com", "instagram.com",
    "de.statista.com", "gelbeseiten.de", "dastelefonbuch.de",
]


def finde_domain(firma: str, api_key: str) -> str:
    """
    North-Data-Exporte enthalten zuverlaessig Firmenname/Adresse/Register-
    nummer, aber die Website ist nicht bei jeder Firma gepflegt. Deshalb hier
    die offizielle Domain per Suche selbst herausfinden, falls sie in der
    CSV fehlt: einfache Namenssuche, erstes Ergebnis nehmen, das NICHT auf
    der BLOCKLISTE steht.

    Heuristik, kein Beweis -- bei mehrdeutigen Firmennamen (mehrere Firmen
    mit aehnlichem Namen, z.B. Filialen/Tochtergesellschaften) kann das
    danebenliegen. Fuer den Prototyp ausreichend; fuer die produktive
    Version wuerde man Stichproben manuell gegenchecken.
    """
    treffer = _serper_suche(f'"{firma}" offizielle Webseite', api_key, anzahl=5)

    for t in treffer:
        domain = normalisiere_domain(t.get("link", ""))
        if domain and not any(blocked in domain for blocked in BLOCKLISTE_DOMAINS):
            return domain

    return ""


def _serper_suche(query: str, api_key: str, anzahl: int) -> list[dict]:
    """Ein einzelner Serper-Call, roh zurueckgegeben (Liste von organic-Treffern)."""
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": anzahl},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("organic", [])
    except requests.RequestException as e:
        print(f"    WARNUNG: Suche fehlgeschlagen fuer '{query}' ({e})")
        return []


def suche_jobanzeige_kandidaten(
    firma: str,
    domain: str,
    api_key: str,
    keywords: list = ALLE_KEYWORDS,
    max_pro_suche: int = 5,
) -> list[dict]:
    """
    Zwei Suchvarianten kombiniert, weil beide unterschiedliche Luecken haben:

    1. `site:domain (...)`  -> praezise, findet aber nur, was Google unter
       der Firmen-Domain selbst indexiert hat. Verpasst z.B. Anzeigen auf
       fremden ATS-Portalen (Personio, Softgarden, SAP SuccessFactors) oder
       Jobboersen (StepStone, Kimeta), wenn die nicht unter der Domain
       gelistet sind.
    2. `"Firmenname" (...)` ohne site-Filter -> durchsucht das ganze Netz,
       findet auch Drittportale, bringt dafuer mehr Rauschen (Uebersichts-
       artikel, Konkurrenz-Erwaehnungen, Namensmehrdeutigkeit) -> deshalb
       danach strikt verifizieren statt dem Snippet zu vertrauen.

    Liefert eine deduplizierte Liste von Kandidaten-URLs, NOCH NICHT
    verifiziert -- das passiert erst in verifiziere_treffer().
    """
    or_kette = " OR ".join(f'"{kw}"' for kw in keywords)
    queries = [f"site:{domain} ({or_kette})"] if domain else []
    queries.append(f'"{firma}" ({or_kette})')

    kandidaten = []
    gesehene_urls = set()

    for query in queries:
        for treffer in _serper_suche(query, api_key, max_pro_suche):
            url = treffer.get("link")
            if url and url not in gesehene_urls:
                gesehene_urls.add(url)
                kandidaten.append({"url": url, "snippet": treffer.get("snippet", "")})

    return kandidaten


def verifiziere_treffer(url: str, keywords: list = ALLE_KEYWORDS) -> dict:
    """
    Laedt die Kandidaten-Seite direkt (Suchmaschinen-Snippets allein sind
    kein verlaesslicher Beweis) und prueft zwei Dinge statt nur eins:

    1. kommt eines der Keywords ueberhaupt im Text vor? Daraus ergibt sich
       die Konfidenz (100 fuer KEYWORDS_EXAKT, 75 fuer KEYWORDS_VERWANDT).
    2. sieht die Seite ueberhaupt wie eine AKTIVE Stellenausschreibung aus
       (Signalwoerter aus STELLENANZEIGE_SIGNALE)? Sonst zaehlt eine reine
       Erwaehnung (z.B. ein Jobboersen-Uebersichtsartikel) faelschlich als
       Treffer -- besonders relevant seit der freien Suche ohne site:-Filter.

    Bei JS-lastigen Bewerbungsportalen liefert requests oft nur ein leeres
    Grundgeruest -> dann muesste man hier auf Playwright umsteigen
    (page.goto(url); page.content()). Fuer den Prototyp bewusst weggelassen.
    """
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        text = re.sub(r"<[^>]+>", " ", resp.text).lower()
    except requests.RequestException as e:
        return {"verifiziert": False, "keyword": "", "konfidenz": 0, "ausschnitt": "", "grund": f"Fehler beim Laden: {e}"}

    gematchte_keywords = [kw for kw in keywords if kw.lower() in text]
    ausschnitt = re.sub(r"<[^>]+>", " ", resp.text)[:800]

    if not gematchte_keywords:
        return {"verifiziert": False, "keyword": "", "konfidenz": 0, "ausschnitt": ausschnitt, "grund": "Keyword nicht im Seitentext"}

    # bei mehreren Treffern die hoechste Konfidenz gewinnen lassen (EXAKT > VERWANDT)
    keyword = max(gematchte_keywords, key=lambda kw: KEYWORD_KONFIDENZ.get(kw.lower(), 0))
    konfidenz = KEYWORD_KONFIDENZ.get(keyword.lower(), 0)
    hat_signal = any(signal in text for signal in STELLENANZEIGE_SIGNALE)

    return {
        "verifiziert": hat_signal,  # ohne Anzeigen-Signal noch nicht als sicherer Treffer werten
        "keyword": keyword,
        "konfidenz": konfidenz,
        "ausschnitt": ausschnitt,
        "grund": "" if hat_signal else "Keyword da, aber kein eindeutiges Stellenanzeigen-Signal",
    }


def llm_klassifiziere_stelle(
    seiten_ausschnitt: str,
    firma: str,
    client: OpenAI,
    model: str,
) -> str:
    """
    Nur fuer Grenzfaelle: Keyword gefunden, aber kein klares Anzeigen-Signal
    auf der Seite (z.B. individuelles ATS-Layout ohne Standardphrasen, oder
    requests hat nur ein JS-Grundgeruest geladen). GPT liest den Ausschnitt
    und nennt entweder den konkreten Stellentitel oder "NEIN". Nur Klassifikation, kein Scoring -> wenig Tokens/Kosten pro Firma.
    """
    prompt = (
        f"Firma: {firma}\n"
        f"Ausschnitt einer Webseite:\n{seiten_ausschnitt}\n\n"
        "Handelt es sich hier um eine AKTIVE Stellenausschreibung fuer eine "
        "Tender-Manager-nahe Position (Speditions-/Logistikbranche)? "
        "Antworte NUR mit dem exakten Stellentitel aus dem Text, oder mit "
        "'NEIN' falls es keine aktive Ausschreibung dafuer ist."
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Unklar (LLM-Fehler: {e})"


def process_firmenliste(
    df: pd.DataFrame,
    output_folder: str,
    search_api_key: str,
    client: OpenAI,
    model: str,
    quelle_csv: Path,
) -> None:
    output_file = ausgabe_pfad(quelle_csv, output_folder)
    total = len(df)
    ergebnisse = []

    for index, row in df.iterrows():
        firma = str(row.get("Firmenname", "") or "").strip()
        domain = normalisiere_domain(str(row.get("Domain", "") or "").strip())
        land = str(row.get("Land", "") or "").strip()

        if not domain:
            domain = finde_domain(firma, search_api_key)
            print(f"  [{index + 1}/{total}] {firma}  (Domain aufgeloest: {domain or 'nicht gefunden'})")
        else:
            print(f"  [{index + 1}/{total}] {firma}  ({domain})")

        kandidaten = suche_jobanzeige_kandidaten(firma, domain, search_api_key)
        bester_treffer = None

        for kandidat in kandidaten:
            ergebnis = verifiziere_treffer(kandidat["url"])

            if not ergebnis["keyword"]:
                continue  # kein Keyword auf der Seite -> naechster Kandidat

            if not ergebnis["verifiziert"]:
                # Keyword da, aber kein eindeutiges Anzeigen-Signal -> GPT
                # schaut sich den Ausschnitt an statt das automatisch als
                # Fehltreffer zu werten
                klassifikation = llm_klassifiziere_stelle(
                    ergebnis["ausschnitt"] or kandidat["snippet"], firma, client, model
                )
                if klassifikation.strip().upper() != "NEIN":
                    ergebnis["verifiziert"] = True
                    ergebnis["keyword"] = klassifikation

            if ergebnis["verifiziert"]:
                bester_treffer = {"url": kandidat["url"], "snippet": kandidat["snippet"], **ergebnis}
                break  # ersten verifizierten Treffer nehmen, nicht alle Kandidaten durchpruefen

            time.sleep(0.5)  # kurze Pause zwischen den Seitenaufrufen pro Firma

        if bester_treffer:
            ergebnisse.append({
                "Firmenname": firma, "Domain": domain, "Land": land,
                "Gefunden": "Ja",
                "Beweis-Link": bester_treffer["url"],
                "Stellentitel/Keyword": bester_treffer["keyword"],
                "Konfidenz (%)": bester_treffer["konfidenz"],
                "Anmerkung": bester_treffer["snippet"],
            })
        else:
            ergebnisse.append({
                "Firmenname": firma, "Domain": domain, "Land": land,
                "Gefunden": "Nein",
                "Beweis-Link": "", "Stellentitel/Keyword": "", "Konfidenz (%)": "",
                "Anmerkung": "keine verifizierte Jobanzeige gefunden" if kandidaten else "keine Suchtreffer",
            })

        time.sleep(1.0)  # Rate-Limit-Puffer fuer die Serper API zwischen Firmen

    results_df = pd.DataFrame(ergebnisse)
    results_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    treffer_anzahl = (results_df["Gefunden"] == "Ja").sum()
    print(f"\n  -> Gespeichert: {output_file}")
    print(f"  -> Treffer: {treffer_anzahl} von {total}\n")
