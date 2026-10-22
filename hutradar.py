#!/usr/bin/env python3
"""Hutradar-logger: meet hoe vaak bedden vrijkomen in volgeboekte Alpenhutten.

Eén run = alle hutten uit huts.csv één keer bevragen via de openbare
beschikbaarheidsdata van hut-reservation.org (geen login), vergelijken met de
vorige run en elke wijziging loggen in events.csv. Draai dit elke 10 minuten
(cron, Taakplanner of GitHub Actions). Alleen Python 3.9+ standaardbibliotheek.

Gebeurtenissen die gelogd worden:
  VRIJGEKOMEN   een datum die vol was (0 vrije bedden) heeft weer vrije bedden
  WEER_VOL      een datum die vrij was gekomen is weer vol (zo meet je hoe snel)
  BOEKING_OPEN  een datum die gesloten was, is nu boekbaar (seizoen gaat open)
  BEDDEN_ERBIJ  er komen bedden bij op een datum die al vrij was (info)

Het script meldt nog niets aan klanten: het meet alleen.
"""
import csv
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

BASE = "https://www.hut-reservation.org/api/v1/reservation/getHutAvailability?hutId={}&step=WIZARD"
USER_AGENT = os.environ.get(
    "HUTRADAR_UA",
    "Hutradar-onderzoek/0.1 (meet beschikbaarheid 1x per 10 min; contact: zie README)",
)
PAUSE_SECONDS = float(os.environ.get("HUTRADAR_PAUSE", "2"))  # beleefd: pauze tussen hutten
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("HUTRADAR_DATA", os.path.join(HERE, "data"))
STATE_FILE = os.path.join(DATA, "state.json")
EVENTS_FILE = os.path.join(DATA, "events.csv")
RUNS_FILE = os.path.join(DATA, "runs.csv")
RAW_DIR = os.path.join(DATA, "raw")
EVENT_FIELDS = ["tijdstip_utc", "hut_id", "hut", "datum", "gebeurtenis", "vrij_voor", "vrij_na", "status_na"]


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_huts(path=os.path.join(HERE, "huts.csv")):
    with open(path, newline="", encoding="utf-8") as f:
        return [(int(r["hut_id"]), r["naam"]) for r in csv.DictReader(f) if r.get("hut_id", "").strip()]


def fetch(hut_id):
    req = urllib.request.Request(BASE.format(hut_id), headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _entries(payload):
    """Haal de lijst met dag-items uit het antwoord, ook als die in een object zit."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("availability", "days", "content", "data", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def parse(payload):
    """Zet het antwoord om naar {datum: (vrije_bedden, status)}."""
    out = {}
    for e in _entries(payload):
        if not isinstance(e, dict):
            continue
        date = e.get("date") or e.get("dateFormatted") or e.get("reservationDate")
        if not date:
            continue
        date = str(date)[:10]
        free = e.get("freeBeds")
        if free is None and isinstance(e.get("freeBedsPerCategory"), dict):
            free = sum(v for v in e["freeBedsPerCategory"].values() if isinstance(v, (int, float)))
        status = str(e.get("percentage") or e.get("hutStatus") or "").upper()
        if status == "CLOSED" or str(e.get("hutStatus", "")).upper() == "CLOSED":
            status = "CLOSED"
        out[date] = (int(free) if free is not None else None, status)
    return out


def diff(hut_id, name, old, new, ts):
    """Vergelijk twee snapshots van één hut en geef gebeurtenissen terug."""
    events = []
    for date, (free_new, st_new) in new.items():
        if date not in old:
            continue
        free_old, st_old = old[date]
        if st_old == "CLOSED" and st_new != "CLOSED" and (free_new or 0) > 0:
            kind = "BOEKING_OPEN"
        elif free_old == 0 and (free_new or 0) > 0:
            kind = "VRIJGEKOMEN"
        elif (free_old or 0) > 0 and free_new == 0:
            kind = "WEER_VOL"
        elif free_old is not None and free_new is not None and free_new > free_old and free_old <= 5:
            kind = "BEDDEN_ERBIJ"
        else:
            continue
        events.append({"tijdstip_utc": ts, "hut_id": hut_id, "hut": name, "datum": date,
                       "gebeurtenis": kind, "vrij_voor": free_old, "vrij_na": free_new, "status_na": st_new})
    return events


def append_csv(path, fields, rows):
    new_file = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new_file:
            w.writeheader()
        w.writerows(rows)


def run():
    os.makedirs(RAW_DIR, exist_ok=True)
    state = json.load(open(STATE_FILE, encoding="utf-8")) if os.path.exists(STATE_FILE) else {}
    ts = now_utc()
    all_events, ok, failed = [], 0, []
    for hut_id, name in load_huts():
        try:
            payload = fetch(hut_id)
        except Exception as exc:  # netwerk of blokkade: noteren en doorgaan
            failed.append(f"{hut_id}:{type(exc).__name__}")
            time.sleep(PAUSE_SECONDS)
            continue
        sample = os.path.join(RAW_DIR, f"eerste_antwoord_{hut_id}.json")
        if not os.path.exists(sample):  # bewaar één ruw voorbeeld per hut ter controle
            with open(sample, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
        snap = parse(payload)
        old = {d: tuple(v) for d, v in state.get(str(hut_id), {}).items()}
        all_events += diff(hut_id, name, old, snap, ts)
        state[str(hut_id)] = {d: list(v) for d, v in snap.items()}
        ok += 1
        time.sleep(PAUSE_SECONDS)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)
    append_csv(EVENTS_FILE, EVENT_FIELDS, all_events)
    append_csv(RUNS_FILE, ["tijdstip_utc", "hutten_ok", "mislukt", "gebeurtenissen"],
               [{"tijdstip_utc": ts, "hutten_ok": ok, "mislukt": " ".join(failed), "gebeurtenissen": len(all_events)}])
    print(f"{ts}  hutten ok: {ok}  mislukt: {len(failed)}  nieuwe gebeurtenissen: {len(all_events)}")
    if failed and ok == 0:
        print("Alle verzoeken mislukt. Controleer je internet, of de site je blokkeert (stop dan).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
