"""
Build a canonical AfSIS Phase I dataset for `afsis_experiment.py`.

Why this exists
---------------
`afsis_data.detect_schema` recognises a fixed set of column patterns. The
published AfSIS tables use different names, and three of them fail silently:

  * the target patterns (`^soc$`, `organic.?c`, `^t(otal)?_?c$`, `^c$`) do not
    match `Total carbon`, so no target is found and `clean()` raises KeyError;
  * `^depth$` matches the `Depth` column, whose values are the labels `top` and
    `sub`, so `pd.to_numeric` turns every row into NaN and the depth step
    deletes the whole dataset;
  * `^clay`/`^sand`/`^silt` do not match `Psa aclay`, `Psa asand`, `Psa asilt`.

The wet-chemistry tables are also disjoint: pH and EC live in CROPNUTS, texture
and total carbon in ICRAF, organic carbon in RRES, with one row per sample per
lab. No single source table carries the full feature set.

This script coalesces them to one row per sample, renames columns to the
canonical set, and writes the result as a SINGLE lab table, so the existing
detector and the existing cleaning pass serve both the synthetic stand-in and
the real data. No pipeline code is changed.

Why one table and not three
---------------------------
`clean()` keeps one row per record: `multi_lab_replicates` drops duplicates on
the record key with `mode="first"`, which keeps the alphabetically first lab.
With CROPNUTS and ICRAF as separate files, CROPNUTS wins and the texture and
carbon columns are discarded, leaving no target at all. The coalesce therefore
has to happen here, and the pipeline must see one row per sample.

Three deliberate choices
------------------------
1. Depth is selected here, on the label, and the label is carried forward as
   `DepthLabel`. That name is not matched by any depth pattern, so
   `_select_surface` reports `applied=False` rather than coercing labels to NaN.
   AfSIS records a categorical depth, not an interval, so the 0-5 cm rule in the
   pipeline genuinely cannot be applied; the ledger says so instead of
   pretending otherwise.
2. No column is named `SiteID` or `ProfileID`. A group key coarser than one row
   per sample is unsafe while `clean()` deduplicates on `[group_key, lab]`. The
   site and cluster identifiers travel as `SiteName` and `ClusterCode`, for
   reporting only; the fold group is `SSN`.
3. The two lab tables are outer-joined, not inner-joined, so a sample that was
   measured by one lab only survives to be counted and explained by the cleaning
   ledger rather than disappearing before it.

Target: total carbon. Organic carbon is counted but not used, because the choice
between the two is a research decision and not a data-cleaning one: total carbon
includes inorganic carbon, and the two columns disagree on a minority of samples.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

SRC = Path("afsis")
OUT = Path("data/afsis_real")

# Columns kept from each lab table, and the canonical name each becomes.
CROPNUTS_MAP = {"PH": "pH_H2O", "EC": "EC"}
ICRAF_MAP = {"Psa aclay": "Clay percent", "Psa asand": "Sand percent",
             "Psa asilt": "Silt percent", "Total carbon": "Total carbon"}
FEATURES = ["pH_H2O", "EC", "Clay percent", "Sand percent", "Silt percent"]
TARGET = "Total carbon"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def coalesce(df: pd.DataFrame, mapping: dict, lab: str) -> pd.DataFrame:
    """One row per SSN: first non-null value of each mapped column."""
    keep = {"SSN": "SSN", **mapping}
    missing = [c for c in keep if c not in df.columns]
    if missing:
        raise KeyError(f"{lab}: expected columns {missing}, found {list(df.columns)[:12]}")
    d = df[list(keep)].dropna(subset=["SSN"])
    d = d.groupby("SSN").first().reset_index()
    return d.rename(columns=keep)[list(keep.values())]


def main() -> None:
    geo = pd.read_csv(SRC / "Georeferences" / "georeferences.csv", low_memory=False)
    n_geo_rows = len(geo)
    geo = geo.drop_duplicates(subset=["SSN"], keep="first")

    depth = geo["Depth"].astype(str).str.strip().str.lower()
    top = geo[depth == "top"].copy()

    # Identifiers the detector must not mistake for a grouping column.
    geo_out = pd.DataFrame({
        "SSN": top["SSN"].astype(str),
        "Latitude": pd.to_numeric(top["Latitude"], errors="coerce"),
        "Longitude": pd.to_numeric(top["Longitude"], errors="coerce"),
        "Country": top["Country"],
        "ClusterCode": top["Cluster"],
        "SiteName": top["Site"],
        "DepthLabel": top["Depth"],
    })

    labs = {}
    for path in sorted((SRC / "Wet_Chemistry").glob("*/Wet_Chemistry_*.csv")):
        labs[path.parent.name] = pd.read_csv(path, low_memory=False)

    cropnuts = coalesce(labs["CROPNUTS"], CROPNUTS_MAP, "CROPNUTS")
    icraf = coalesce(labs["ICRAF"], ICRAF_MAP, "ICRAF")

    # Outer join: a one-lab sample must reach the cleaning ledger, not vanish here.
    merged = cropnuts.merge(icraf, on="SSN", how="outer")
    in_c = set(cropnuts["SSN"])
    in_i = set(icraf["SSN"])
    merged["lab_sources"] = merged["SSN"].map(
        lambda s: "+".join(n for n, ok in (("CROPNUTS", s in in_c), ("ICRAF", s in in_i)) if ok))
    merged = merged[["SSN"] + FEATURES + [TARGET, "lab_sources"]]

    n_org = int(labs["RRES"]["C % Org"].notna().sum()) if "C % Org" in labs["RRES"] else 0

    lab_dir = OUT / "Wet_Chemistry" / "COALESCED"
    (OUT / "Georeferences").mkdir(parents=True, exist_ok=True)
    lab_dir.mkdir(parents=True, exist_ok=True)

    geo_out.to_csv(OUT / "Georeferences" / "georeferences.csv", index=False,
                   lineterminator="\n")
    merged.to_csv(lab_dir / "Wet_Chemistry_COALESCED.csv", index=False,
                  lineterminator="\n")

    # Cross-check against counts computed independently from the raw files.
    joined = geo_out.merge(merged, on="SSN", how="inner")
    complete = joined.dropna(subset=FEATURES + [TARGET])

    manifest = {
        "purpose": "canonical AfSIS Phase I dataset for afsis_experiment.py",
        "source_root": str(SRC),
        "source_files": {str(p.relative_to(SRC)).replace("\\", "/"): sha256_file(p)
                         for p in sorted(SRC.rglob("*.csv"))},
        "coalesce": {
            "rule": "one row per SSN; first non-null value per column per lab; "
                    "CROPNUTS and ICRAF outer-joined",
            "single_table": "Wet_Chemistry/COALESCED/Wet_Chemistry_COALESCED.csv",
            "why_single_table": "clean() keeps one row per record with "
                                "mode='first', which would keep CROPNUTS and drop "
                                "the ICRAF texture and carbon columns",
            "CROPNUTS": CROPNUTS_MAP,
            "ICRAF": ICRAF_MAP,
            "unused": {"RRES": "C % Org (organic carbon), counted, not used"},
        },
        "depth_policy": "topsoil selected on the AfSIS depth label; the 0-5 cm "
                        "interval rule cannot be applied because the source "
                        "records a categorical label, so the label travels as "
                        "DepthLabel and the pipeline reports applied=False",
        "grouping": "SSN. Site and cluster travel as SiteName/ClusterCode for "
                    "reporting only.",
        "target": TARGET,
        "target_note": "total carbon, not organic carbon; see module docstring",
        "counts": {
            "geo_rows_raw": n_geo_rows,
            "geo_unique_ssn": int(geo["SSN"].nunique()),
            "topsoil_rows": int(len(geo_out)),
            "joined_rows": int(len(joined)),
            "complete_rows": int(len(complete)),
            "complete_clusters": int(complete["ClusterCode"].nunique()),
            "complete_sites": int(complete["SiteName"].nunique()),
            "complete_countries": int(complete["Country"].nunique()),
            "organic_carbon_rows_unused": n_org,
        },
    }
    (OUT / "COALESCE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    print(json.dumps(manifest["counts"], indent=2))
    print(f"\nwritten to {OUT}/  ->  Georeferences/, Wet_Chemistry/COALESCED/")
    print(f"geo columns     : {list(geo_out.columns)}")
    print(f"coalesced columns: {list(merged.columns)}")


if __name__ == "__main__":
    main()
