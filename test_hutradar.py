"""Zelftest met nepdata (geen internet nodig): python3 test_hutradar.py"""
import os
import shutil
import sys
import tempfile

tmp = tempfile.mkdtemp()
os.environ["HUTRADAR_DATA"] = tmp
os.environ["HUTRADAR_PAUSE"] = "0"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hutradar  # noqa: E402
import rapport  # noqa: E402

day = lambda d, free, pct: {"date": d, "freeBeds": free, "percentage": pct, "hutStatus": "SERVICED"}
rounds = [
    [day("2027-07-10", 0, "FULL"), day("2027-07-11", 3, "NEARLY_FULL"), {"date": "2027-08-01", "freeBeds": 0, "percentage": "CLOSED", "hutStatus": "CLOSED"}],
    [day("2027-07-10", 2, "NEARLY_FULL"), day("2027-07-11", 3, "NEARLY_FULL"), {"date": "2027-08-01", "freeBeds": 0, "percentage": "CLOSED", "hutStatus": "CLOSED"}],
    [day("2027-07-10", 0, "FULL"), day("2027-07-11", 0, "FULL"), day("2027-08-01", 40, "AVAILABLE")],
]
times = ["2026-10-22T10:00:00Z", "2026-10-22T10:10:00Z", "2026-10-22T10:30:00Z"]
hutradar.load_huts = lambda path=None: [(119, "Olpererhütte")]
for payload, t in zip(rounds, times):
    hutradar.fetch = lambda hut_id, p=payload: p
    hutradar.now_utc = lambda t=t: t
    assert hutradar.run() == 0

import csv  # noqa: E402
kinds = [r["gebeurtenis"] for r in csv.DictReader(open(os.path.join(tmp, "events.csv"), encoding="utf-8"))]
assert kinds == ["VRIJGEKOMEN", "WEER_VOL", "WEER_VOL", "BOEKING_OPEN"], kinds
rapport.main()
shutil.rmtree(tmp)
print("\nZELFTEST OK")
