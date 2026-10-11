# Lead-Recherche-Tool für KI Beratung Hessen

Lead-Recherche-Tool: A Python tool that searches a list of freight forwarders in the DACH region for open Tender Manager positions and returns a verified link to the job posting as proof for every hit.

This project started as [Firmenbewerter](https://github.com/haritianaramparany3331-ship-it/Firmenbewerter), a tool that let GPT rate companies from scraped Indeed lists with a score from 0 to 100. The idea evolved from subjective scoring to finding concrete, verifiable evidence: an active job posting on the web. That shift became this project. The company lists themselves come from manual research, e.g. a North Data export

---

## Requirements

- Serper API Key
- OpenAI API Key
- List in firmenlist

---

## Changelog

- Added GPT analysis of companies from Indeed-scraped CSV lists, using live web search
- Added a score from 0 to 100 and a qualified yes/no per company, plus website, phone, email and a short comment, saved as CSV
- Added a keyword list so GPT knows which search term produced each list; results are saved as `<keyword>Result.csv`
- Changed the structure: helper functions moved into `hilfsfunktionen.py`
- Added a prompt folder with example prompts for a sample company
- Changed the tool to be generic: configurable prompts, a main prompt template, and input/output folders created automatically
- Changed the whole approach: from subjective GPT scoring to searching for verifiable Tender Manager job postings
- Added a new input format: `Firmenname`, `Domain` (required) and `Land`, `Mitarbeiter`, `Umsatz_Mio` (optional), with an example file
- Added a size filter: at least 100 employees OR at least €25M annual revenue
- Added automatic domain lookup when a company has no website in the list, skipping directories, registers and job portals
- Added two combined searches per company via Serper: `site:domain` for precision and a free search by company name to also catch external job portals
- Added two keyword tiers: exact role titles (confidence 100%) and related roles (confidence 75%)
- Added direct verification: every candidate page is loaded and checked for a keyword plus typical job ad phrases ("wir suchen", "apply now", ...)
- Changed GPT's role: it only classifies borderline cases (keyword found, but no clear job ad signal) and returns the job title or "NEIN", no scoring anymore
- Added one result CSV per input list (`<name>_tenderManagerTreffer.csv`) with found yes/no, proof link, job title, confidence and a note
- Added pauses between requests to respect the Serper rate limit

---

## Author and resources
Antsa Haritiana Ramparany, computer science student at Hochschule Darmstadt (h_da), Germany
