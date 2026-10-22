# Hutradar-logger

Meet 4 weken lang hoe vaak er bedden vrijkomen in 34 populaire, vaak volgeboekte Alpenhutten
(Stubaier en Berliner Höhenweg, Karwendel, Zugspitze, Watzmann, Rätikon, Wallis e.a.)
en hoe snel ze weer weg zijn. Het stuurt nog geen meldingen: eerst meten of er genoeg te melden is.

Bron: de openbare beschikbaarheidsdata van hut-reservation.org (zonder login; per hut één
verzoek dat ~15 maanden aan data teruggeeft). 34 hutten x 1 verzoek per 10 minuten, met 2 seconden
pauze ertussen. Dat is bescheiden verkeer.

## Starten (kies één)

**A. Gratis via GitHub (aanrader, draait ook als je laptop uit is)**
1. Maak een GitHub-account en een nieuwe repository. Kies *public*: dan zijn de minuten gratis
   (bij private zit je met elke 10 minuten boven de gratis 2.000 minuten per maand).
2. Upload alle bestanden uit deze map, inclusief de map `.github`.
3. Ga naar *Actions* en zet de workflow aan; klik *Run workflow* voor een eerste test.
4. Daarna draait hij elke ~10 minuten. De resultaten staan in `data/` (events.csv en rapport.md).

**B. Op je eigen computer (alleen als die aan staat)**
- Test: `python3 hutradar.py` (twee keer achter elkaar draaien; de eerste run legt de nulmeting vast).
- Mac/Linux, elke 10 minuten via cron: `*/10 * * * * cd /pad/naar/hutradar && python3 hutradar.py`
- Windows: Taakplanner, actie `python hutradar.py`, herhalen elke 10 minuten.

**C. Klein servertje (~€4 per maand, bijvoorbeeld Hetzner)**: zelfde cron-regel als bij B.

## Eerste controle (belangrijk)
Na de eerste run staat per hut een ruw voorbeeld in `data/raw/`. Open er één en check of je
datums en vrije bedden ziet. Staat er een foutmelding in, of mislukken alle verzoeken? Stop dan
en stuur het bestand naar Claude om het script aan te passen.

## Uitlezen
`python3 rapport.py` (of open `data/rapport.md` op GitHub). Belangrijkste cijfers:
- **Vrijgekomen plekken op volle zomerdata**: is er genoeg aanbod om te melden?
- **Mediane tijd tot weer vol**: hoe snel moet een melding zijn?

## Spelregels
- Blijf bij 1x per 10 minuten. Niet sneller, niet meer hutten zonder reden.
- Krijg je foutmeldingen of blokkades (HTTP 403/429)? Stop dan direct.
- Zet een contactadres in de variabele `HUTRADAR_UA` zodat de beheerder je kan bereiken.
- Dit is een meting voor eigen onderzoek. Voordat je er een betaalde dienst van maakt:
  de voorwaarden van hut-reservation.org nalezen en bij voorkeur de alpenverenigingen informeren.

## Hutten aanpassen
Bewerk `huts.csv`. Alle hut-ID's komen uit de catalogus van hut-reservation.org (~570 hutten).
