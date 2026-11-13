"""Build a loadable copy of the afsis_real root without touching the original.

The working copy of Wet_Chemistry_COALESCED.csv has its first column named `u`
instead of `SSN` (the committed version has `SSN`), so afsis_data.load_raw
cannot join on it.  This copies the two files, renames that one column, and
writes them with LF endings so a hashed version is stable.
"""
import shutil
from pathlib import Path

SRC = Path("data/afsis_real")
DST = Path("_smoke/afsis_real_fixed")

for part in ("Georeferences", "Wet_Chemistry/COALESCED"):
    (DST / part).mkdir(parents=True, exist_ok=True)

geo = (SRC / "Georeferences/georeferences.csv").read_text(encoding="utf-8")
(DST / "Georeferences/georeferences.csv").write_text(geo, encoding="utf-8", newline="\n")

src_wet = SRC / "Wet_Chemistry/COALESCED/Wet_Chemistry_COALESCED.csv"
lines = src_wet.read_text(encoding="utf-8").splitlines()
head = lines[0].split(",")
if head[0] != "SSN":
    print(f"repairing header: {head[0]!r} -> 'SSN'")
    head[0] = "SSN"
lines[0] = ",".join(head)
(DST / "Wet_Chemistry/COALESCED/Wet_Chemistry_COALESCED.csv").write_text(
    "\n".join(lines) + "\n", encoding="utf-8", newline="\n")

print("rows:", len(lines) - 1)
print("written:", DST)
