# Lead-Recherche-Tool für KI Beratung Hessen

A Python tool that searches a list of freight forwarders in the DACH region for open Tender Manager positions and returns a verified link to the job posting as proof for every hit. Companies that are actively hiring for tender or bid management work with tenders and are likely to benefit from support in that area.

The project started as [Firmenbewerter](https://github.com/harikoto31/Firmenbewerter), where GPT researched companies with live web search and rated each one from 0 to 100. The scores turned out to be subjective and hard to check, so the idea evolved: instead of asking GPT for an opinion, the tool now looks for concrete evidence that anyone can verify by clicking a link.

## How it works

- Reads company lists as CSV (`Firmenname`, `Domain` required; `Land`, `Mitarbeiter`, `Umsatz_Mio` optional) and filters by size: at least 100 employees or €25M annual revenue
- Finds a company's official domain automatically if it's missing
- Searches each company twice via the Serper API: `site:domain` on the company website, plus a free search to catch external job portals like Personio or Softgarden
- Loads every candidate page and verifies it: role keyword present (exact title = 100 %, related role = 75 % confidence) plus typical job ad phrases like "wir suchen" or "apply now"
- Uses GPT only for borderline cases, returning the job title or "NEIN", which keeps token costs low

## Usage

Requires Python 3.10+ and API keys for [Serper](https://serper.dev) and [OpenAI](https://platform.openai.com).

```bash
pip install -r requirements.txt
cp .env.example .env   # then add your API keys
python src/finde_tender_manager.py
```

Put your CSV files in `firmenlisten/` (see `beispiel_speditionen.csv`). The tool saves one result file per list to `results/`:

| Firmenname | Gefunden | Beweis-Link | Stellentitel/Keyword | Konfidenz (%) |
|---|---|---|---|---|
| Beispiel Spedition GmbH | Ja | https://… | Tender Manager (m/w/d) | 100 |
| Platzhalter Transporte GmbH | Nein | | | |

---

Antsa Haritiana Ramparany, computer science student at Hochschule Darmstadt (h_da), Germany