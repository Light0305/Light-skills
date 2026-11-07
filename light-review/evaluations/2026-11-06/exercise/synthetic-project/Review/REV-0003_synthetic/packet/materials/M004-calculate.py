import csv, json, statistics, sys
from pathlib import Path
rows = list(csv.DictReader(Path(sys.argv[1]).open(encoding="utf-8")))
a, b = ([float(row[k]) for row in rows] for k in ("A", "B"))
print(json.dumps({"basis":"synthetic descriptive data; no inferential test",
 "mean_A":statistics.mean(a), "mean_B":statistics.mean(b),
 "A_below_B":[r["site"] for r in rows if float(r["A"]) < float(r["B"])]}))
