#!/usr/bin/env python3
"""Maakt een rapport van events.csv: hoe vaak komen bedden vrij, en hoe snel zijn ze weg?

Gebruik:  python3 rapport.py          (schrijft ook data/rapport.md)
"""
import csv
import os
import statistics
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("HUTRADAR_DATA", os.path.join(HERE, "data"))


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def main():
    events_path = os.path.join(DATA, "events.csv")
    runs_path = os.path.join(DATA, "runs.csv")
    if not os.path.exists(events_path):
        print("Nog geen events.csv. Laat hutradar.py eerst een tijd draaien.")
        return
    events = list(csv.DictReader(open(events_path, encoding="utf-8")))
    runs = list(csv.DictReader(open(runs_path, encoding="utf-8"))) if os.path.exists(runs_path) else []

    # Koppel elke VRIJGEKOMEN aan de eerstvolgende WEER_VOL voor dezelfde hut + datum
    open_since = {}
    durations = defaultdict(list)          # hut -> [minuten]
    freed = defaultdict(int)
    freed_summer = defaultdict(int)
    still_open = defaultdict(int)
    booking_open = defaultdict(int)
    for e in sorted(events, key=lambda r: r["tijdstip_utc"]):
        key = (e["hut"], e["datum"])
        kind = e["gebeurtenis"]
        if kind == "VRIJGEKOMEN":
            freed[e["hut"]] += 1
            if e["datum"][5:7] in ("06", "07", "08", "09") or e["datum"][3:5] in ("06", "07", "08", "09"):
                freed_summer[e["hut"]] += 1
            open_since[key] = ts(e["tijdstip_utc"])
        elif kind == "WEER_VOL" and key in open_since:
            durations[e["hut"]].append((ts(e["tijdstip_utc"]) - open_since.pop(key)).total_seconds() / 60)
        elif kind == "BOEKING_OPEN":
            booking_open[e["hut"]] += 1
    for (hut, _), _t in open_since.items():
        still_open[hut] += 1

    first = runs[0]["tijdstip_utc"] if runs else "?"
    last = runs[-1]["tijdstip_utc"] if runs else "?"
    all_d = [d for v in durations.values() for d in v]
    lines = [
        "# Hutradar-rapport",
        "",
        f"Meetperiode: {first} t/m {last} ({len(runs)} runs)",
        f"Vrijgekomen plekken op volle data: **{sum(freed.values())}** (waarvan zomer jun-sep: {sum(freed_summer.values())})",
        f"Seizoen/boeking-open-momenten: {sum(booking_open.values())}",
    ]
    if all_d:
        within = lambda m: 100 * sum(1 for d in all_d if d <= m) / len(all_d)
        lines += [
            f"Mediane tijd tot weer vol: **{statistics.median(all_d):.0f} minuten** (n={len(all_d)})",
            f"Weer vol binnen 10 min: {within(10):.0f}%  |  binnen 60 min: {within(60):.0f}%  |  binnen 24 uur: {within(1440):.0f}%",
        ]
    lines += ["", "| Hut | Vrijgekomen | Zomer | Mediaan tot vol (min) | Nog open | Boeking open |",
              "| --- | --- | --- | --- | --- | --- |"]
    for hut in sorted(set(freed) | set(booking_open), key=lambda h: -freed[h]):
        med = f"{statistics.median(durations[hut]):.0f}" if durations[hut] else "-"
        lines.append(f"| {hut} | {freed[hut]} | {freed_summer[hut]} | {med} | {still_open[hut]} | {booking_open[hut]} |")
    lines += ["", "## Hoe lees je dit?",
              "- Veel vrijgekomen plekken op zomerdata = er is aanbod om te melden.",
              "- Mediaan onder ~10 min = alleen razendsnelle meldingen hebben waarde (en jij ziet dan 1x per 10 min te weinig).",
              "- Mediaan van uren of dagen = een melding werkt, maar de urgentie (en betaalbereidheid) is lager.",
              "- Weinig vrijgekomen plekken = de dienst heeft te weinig te melden: stoppen."]
    report = "\n".join(lines)
    print(report)
    with open(os.path.join(DATA, "rapport.md"), "w", encoding="utf-8") as f:
        f.write(report + "\n")


if __name__ == "__main__":
    main()
