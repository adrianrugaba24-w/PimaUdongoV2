"""Temporary: measure whether the real AfSIS tables can supply one complete row.

The loader concatenates the lab CSVs and joins them to Georeferences on SSN.
This checks the consequence: which columns survive, how much is missing per lab,
whether a target exists at all, and whether the depth column is numeric.
"""
import re

import numpy as np
import pandas as pd

import afsis_data as A

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)

df, manifest = A.load_raw("afsis")
print(f"merged rows={len(df)}  files={len(manifest)}  unique SSN={df['SSN'].nunique()}")
print("\nrows per lab:\n" + df["lab"].value_counts().to_string())

cands = [c for c in df.columns
         if re.search(r"(?i)^%c$|organic|total carbon|acidified|^ph$|^ec$|psa|clay|silt|sand", str(c))]
print(f"\ncandidate chemistry columns ({len(cands)}):")
print("  " + ", ".join(repr(c) for c in cands))

print("\nnon-null counts overall and per lab:")
for c in cands:
    per = df.groupby("lab")[c].apply(lambda s: int(s.notna().sum()))
    print(f"  {c!r:28s} total={int(df[c].notna().sum()):5d}   "
          + "  ".join(f"{lab}={n}" for lab, n in per.items()))

print("\nDepth column:")
d = df["Depth"]
print(f"  dtype={d.dtype}  unique={d.nunique()}")
print("  sample:", d.dropna().astype(str).unique()[:8].tolist())

# Coalesce across labs per SSN: does one complete vector exist per sample?
print("\ncoalesce-across-labs coverage (one value per SSN):")
for c in cands:
    n = df.groupby("SSN")[c].apply(lambda s: int(s.notna().any())).sum()
    if n:
        print(f"  {c!r:28s} SSNs with a value = {n}")

# What a plausible feature set would look like after coalescing.
picks = {}
for c in cands:
    key = ("carbon" if re.search(r"(?i)^%c$|organic|total carbon", str(c)) else
           "ph" if re.match(r"(?i)^\s*ph\s*$", str(c)) else
           "ec" if re.match(r"(?i)^\s*ec\s*$", str(c)) else
           "clay" if re.search(r"(?i)clay", str(c)) else
           "sand" if re.search(r"(?i)sand", str(c)) else
           "silt" if re.search(r"(?i)silt", str(c)) else None)
    if key:
        picks.setdefault(key, []).append(c)
print("\nrole -> columns found:")
for k, v in picks.items():
    print(f"  {k:7s} {v}")

if "ec" in picks:
    ec = pd.to_numeric(df["EC"], errors="coerce")
    print(f"\nEC: n={ec.notna().sum()} min={ec.min():.4g} median={ec.median():.4g} "
          f"max={ec.max():.4g} (units unconfirmed: dS/m vs uS/cm changes the scale 1000x)")
