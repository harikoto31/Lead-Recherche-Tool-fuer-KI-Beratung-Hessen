"""
Sucht in einer Firmenliste (Speditionen DACH, >= 100 Mitarbeiter ODER
>= 25 Mio Euro Jahresumsatz) nach offenen "Tender Manager"-Stellen auf den
jeweiligen Firmen-Webseiten und liefert bei einem Treffer den Link als Beweis.

EINGABE-FORMAT (CSV in INPUT_FOLDER):
    Firmenname, Domain                              [Pflicht]
    Land, Mitarbeiter, Umsatz_Mio                    [optional]
    -> siehe firmenlisten/beispiel_speditionen.csv

WOHER DIE FIRMENLISTE KOMMT (nicht Teil dieses Skripts, da manuelle
Recherche/Export noetig):
    - North Data Power-Search (Kennzahlen-Filter Mitarbeiterzahl/Umsatz +
      Branche Spedition/Gueterverkehr), CSV/XLSX-Export ueber den Premium-
      Service (nicht die teure API noetig).
    - Mitgliederlisten der Branchenverbaende: DSLV (Deutschland),
      Zentralverband Spedition & Logistik (Oesterreich), SPEDLOGSWISS
      (Schweiz) -- v.a. wichtig, weil North Data AT/CH duenner abdeckt.

BENOETIGTE API-KEYS:
    - Serper (serper.dev) fuer die site:-Suche -> SEARCH_API_KEY
    - OpenAI, nur fuer die Klassifikation von Grenzfaellen -> OPENAI_API_KEY
"""

from pathlib import Path
import os
from dotenv import load_dotenv

import pandas as pd
from openai import OpenAI

from hilfsfunktionen import ausgabe_pfad, firmenliste_filtern, process_firmenliste, lade_key

PROJEKT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FOLDER  = PROJEKT_ROOT / "firmenlisten"
OUTPUT_FOLDER = PROJEKT_ROOT / "results"

MIN_MITARBEITER = 100
MIN_UMSATZ_MIO   = 25.0

load_dotenv(PROJEKT_ROOT / ".env")

SEARCH_API_KEY = lade_key("SERPER_API_KEY")
OPENAI_API_KEY = lade_key("OPENAI_API_KEY")

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

client = OpenAI(api_key=OPENAI_API_KEY)


def main() -> None:
    Path(INPUT_FOLDER).mkdir(exist_ok=True)
    Path(OUTPUT_FOLDER).mkdir(exist_ok=True)

    input_files = sorted(Path(INPUT_FOLDER).glob("*.csv"))

    if not input_files:
        print(f"Keine CSV-Dateien in '{INPUT_FOLDER}/' gefunden.")
        print("Erwartete Spalten: Firmenname, Domain (optional: Land, Mitarbeiter, Umsatz_Mio)")
        print("Beispiel liegt in firmenlisten/beispiel_speditionen.csv")
        return

    for csv_path in input_files:
        print("=" * 60)
        print(f"Datei: {csv_path.name}  ->  {ausgabe_pfad(csv_path, OUTPUT_FOLDER).name}")

        df = pd.read_csv(csv_path)
        vorher = len(df)
        df = firmenliste_filtern(df, MIN_MITARBEITER, MIN_UMSATZ_MIO)
        print(f"  -> {len(df)} von {vorher} Firmen erfuellen das Groessenkriterium\n")

        if df.empty:
            continue

        process_firmenliste(df, OUTPUT_FOLDER, SEARCH_API_KEY, client, MODEL, csv_path)

    print("=" * 60)
    print(f"Fertig. Ergebnisse in '{OUTPUT_FOLDER}/'")


if __name__ == "__main__":
    main()
