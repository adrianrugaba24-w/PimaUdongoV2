"""Why training on the Ugandan sheet yields no signal.

Counts what is actually independent in the 258-row sheet: how many distinct
input vectors exist once the repeated chemistry is honoured, and how much the
target varies across them.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

WET = Path("data/uganda_2025/Wet_Chemistry/FARMERS2025/"
           "Wet_Chemistry_FARMERS2025.csv")
sys.stdout.reconfigure(encoding="utf-8")

w = pd.read_csv(WET)
TEX = ["Clay percent", "Sand percent", "Silt percent"]

print(f"rows in the table                 : {len(w)}")
print(f"distinct record_pattern values    : {w['record_pattern'].nunique()}")
print(f"rows in a repeated pattern        : "
      f"{int(w['record_pattern'].value_counts().gt(1).mul(
          w['record_pattern'].value_counts()).sum())}")

print("\nwithin one record_pattern:")
for c in ["OM percent", "Total carbon"] + TEX:
    n = w.groupby("record_pattern")[c].nunique()
    print(f"  {c:16s} max distinct values per pattern = {int(n.max())}")
n = w.groupby("record_pattern")["pH_H2O"].nunique()
print(f"  {'pH_H2O':16s} max distinct values per pattern = {int(n.max())}  "
      f"(mean {n.mean():.1f})")

# one row per pattern = the most information the sheet can support
g = w.groupby("record_pattern").agg(
    **{c: (c, "first") for c in TEX},
    om=("OM percent", "first"),
    carbon=("Total carbon", "first"),
    ph=("pH_H2O", "mean"),
    n_rows=("SSN", "size"),
).reset_index()

print(f"\nrecords after collapsing to one per pattern: {len(g)}")
print(f"distinct texture vectors among them        : "
      f"{g[TEX].drop_duplicates().shape[0]}")
print(f"distinct (texture + target) combinations   : "
      f"{g[TEX + ['carbon']].drop_duplicates().shape[0]}")

print("\nhow much the target varies across those records:")
print(f"  carbon mean {g.carbon.mean():.3f}  sd {g.carbon.std():.3f}  "
      f"min {g.carbon.min():.3f}  max {g.carbon.max():.3f}")
print(f"  OM     mean {g.om.mean():.3f}  sd {g.om.std():.3f}  "
      f"min {g.om.min():.3f}  max {g.om.max():.3f}")

print("\nrank correlation of the target with each available input "
      f"(n={len(g)}):")
for c in TEX + ["ph"]:
    c_ok = g[[c, "carbon"]].dropna()
    if c_ok[c].nunique() > 1:
        r = c_ok[c].corr(c_ok["carbon"], method="spearman")
        print(f"  {c:16s} {r:+.3f}")

print("\nrows per pattern: median %d, max %d" % (g.n_rows.median(), g.n_rows.max()))
print("scan: how many patterns share the single commonest texture triple")
top = g[TEX].value_counts().head(3)
print(top.to_string())
