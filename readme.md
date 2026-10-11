# Lead-Recherche-Tool für KI Beratung Hessen

A Python tool that searches a list of freight forwarders in the DACH region for open Tender Manager positions and returns a verified link to the job posting as proof for every hit. The goal is to find companies that are actively hiring for tender or bid management, a strong sign that they work with tenders and could benefit from support in that area.

The project started as [Firmenbewerter](https://github.com/haritianaramparany3331-ship-it/Firmenbewerter), where GPT researched companies from scraped Indeed lists with live web search and rated each one with a score from 0 to 100. The scores turned out to be subjective and hard to check, so the idea evolved: instead of asking GPT for an opinion, the tool now looks for concrete evidence that anyone can verify by clicking a link.

- Reads company lists as CSV with `Firmenname` and `Domain` as required columns, and `Land`, `Mitarbeiter`, `Umsatz_Mio` as optional ones
- Filters the list by size: at least 100 employees or at least €25M annual revenue
- Finds a company's official domain automatically if the list doesn't include it, skipping directories, registers and job portals like LinkedIn or StepStone
- Searches each company twice via Serper: `site:domain` for precise results on the company website, and a free search by company name to also catch postings on external portals like Personio or Softgarden
- Uses two keyword tiers: exact role titles such as "Tender Manager" or "Ausschreibungsmanager" (confidence 100%) and related roles such as "Key Account Manager Logistik" (confidence 75%)
- Loads every candidate page directly instead of trusting search snippets, and checks it for the keywords plus typical job ad phrases like "wir suchen" or "apply now"
- Uses GPT only for borderline cases, where a keyword is on the page but there is no clear job ad signal; GPT then returns the job title or "NEIN", which keeps token costs low
- Saves one CSV per input list (`<name>_tenderManagerTreffer.csv`) with found yes/no, proof link, job title, confidence and a note
- Pauses between requests to respect the Serper rate limit

The company lists come from manual research, for example a North Data export filtered by industry and company size.

Antsa Haritiana Ramparany, computer science student at Hochschule Darmstadt (h_da), Germany

