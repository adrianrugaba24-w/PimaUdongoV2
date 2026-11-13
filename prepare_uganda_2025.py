"""
Build a canonical Ugandan dataset for `afsis_experiment.py`.

Why this exists
---------------
`Soil of Farmers 2025 Reviewed.xlsx` is the first soil dataset in this project
that was actually sampled in Uganda.  It arrives in the shape a field workbook
has, not the shape the pipeline consumes, and four things in it would break the
existing loader silently:

  * the sheet is 282 rows but only 258 of them are samples.  Row 0 is a units
    row ('%', 'ppm', 'Cmol/kg'), 12 rows are in-sheet `Average` / `Critical
    Value` subtotals, two are blank and seven are a pH rating legend pasted
    below the table.  Every one of those rows carries a number in some column,
    so no numeric test separates them: they are separated on `No`, which is a
    sample number only on real rows;
  * the sample numbers arrive as integers at the top of the sheet and as text
    ('56') from row 58 onwards - an Excel formatting artefact, not a duplicate;
  * one latitude is typed with a trailing apostrophe ("2.475420'"), which
    `pd.to_numeric` turns into NaN and `clean()` would then drop as missing
    coordinates;
  * there is no total carbon column.  The workbook measures organic matter (OM,
    %), so the target has to be derived - see "Target" below - and there is no
    EC column at all.

This script writes the same two-folder layout `prepare_afsis_real.py` writes, so
`afsis_data.load_raw`, `detect_schema` and `clean` serve it unchanged.  No
pipeline code is changed.

Three deliberate choices
------------------------
1. No column is named `SiteID` or `ProfileID`.  `clean()` deduplicates on
   `[group_key, lab]` with `keep="first"`, so a group key coarser than one row
   per sample would keep one row per farm and silently discard the rest.  The
   sample is the group (`SSN`); the host travels as `SiteName` for reporting
   only, and the fold group stays one sample.
2. The 24 non-sample rows are removed here *and counted*, rather than left for
   `clean()`.  Their numbers are averages and guideline values that look like
   measurements; a ledger entry naming them is more honest than letting them be
   dropped for some incidental reason such as a missing coordinate.
3. Nothing is imputed, nothing is aggregated across samples, and no value is
   clamped.  A value outside a physical bound is left for `clean()` to report,
   so the ledger shows what the source actually contained.

What the workbook contains that it should not
---------------------------------------------
Ten of the eleven chemistry columns (OM, N, P, K, Na, Ca, Mg, sand, clay, silt)
repeat verbatim in blocks of 16-23 rows, while pH differs from row to row:
214 of the 258 samples share their OM..Silt vector with another sample, and
there are only 79 distinct vectors in the whole table.  That is a filled-down
look-up table, not 258 measured soils.  Nothing here deletes or repairs it - the
source is the source - but every row is stamped with a `record_pattern` id, the
count is written to the manifest, and `known_defect` says plainly that a
cross-validated score computed from this root is inflated, because identical
rows land in different folds.  The workbook needs correcting, or a run needs to
group on `record_pattern`, before a score from it means anything.

Target: total carbon, estimated from organic matter
---------------------------------------------------
The pipeline's target is total carbon (g/100 g).  This workbook does not
measure carbon.  It measures organic matter, and the conventional conversion is
OM / 1.724 (the Van Bemmelen factor, 1/0.58).  The derived column is written
with a `carbon_source` column beside it so no reader has to guess, and the
manifest states the conversion and its limitation: OM/1.724 estimates *organic*
carbon, while AfSIS reports *total* carbon including any inorganic fraction.
Treating them as the same scale is an assumption, not a measurement.  It is
supported here, not proved, by the pH distribution: carbonate is not expected in
these soils below about pH 6.5, and the manifest reports how many samples sit
above that line.

EC is absent at source
----------------------
The AfSIS feature set is pH, EC, clay, sand, silt.  This workbook has no
electrical conductivity column, so `EC` is written as an empty column.  It is
kept rather than omitted so the table matches the project's five inputs and the
gap is visible in the data rather than in a conversation.  A model trained with
EC cannot score these rows; a run has to pass `--drop-features EC` to use them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path("Soil of Farmers 2025 Reviewed.xlsx")
SHEET = "Sheet1"
OUT = Path("data/uganda_2025")
LAB = "FARMERS2025"

# The canonical set `prepare_afsis_real.py` writes.  Same names, same order, so
# the same detector and the same run command serve both datasets.
FEATURES = ["pH_H2O", "EC", "Clay percent", "Sand percent", "Silt percent"]
TARGET = "Total carbon"

# OM % -> C % .  1/0.58 is the Van Bemmelen factor.  Named here so the manifest
# and the tests quote the same number.
OM_TO_C = 1.0 / 0.58

# Cell values that are units, not measurements.  Used only to classify the
# non-sample rows for the ledger.
UNIT_TOKENS = {"%", "ppm", "Cmol/kg", "mg/kg", "meq/100g", "cmol/kg"}

# Physical bounds, mirroring afsis_data.BOUNDS.  Used for the report only: the
# table is written as it was read, and clean() decides what to do.
BOUNDS = {"pH_H2O": (0.0, 14.0), "EC": (0.0, 50.0),
          "Clay percent": (0.0, 100.0), "Sand percent": (0.0, 100.0),
          "Silt percent": (0.0, 100.0), TARGET: (0.0, 100.0)}

# Columns that turned out to be entered in repeated blocks rather than per farm.
# They are compared as a vector to give every distinct measurement record a name.
REPEAT_CHECK_COLUMNS = ["OM", "N", "P", "K", "Na", "Ca", "Mg",
                        "Sand", "Clay", "Silt"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def numbers(s: pd.Series) -> pd.Series:
    """
    Coerce one column to numbers, keeping what the cell meant.

    Handles the three things this workbook does that `pd.to_numeric` refuses:
    a trailing apostrophe on a coordinate, a detection-limit prefix ('<0.005'
    becomes 0.005, the reported bound), and numbers stored as text.
    """
    t = s.astype(str).str.strip()
    t = t.str.replace(r"[\u2032'\"]+$", "", regex=True)   # 2.475420' -> 2.475420
    t = t.str.replace(r"^\s*[<>]\s*", "", regex=True)     # '<0.005'  -> 0.005
    t = t.replace({"": np.nan, "nan": np.nan, "NaN": np.nan, "None": np.nan})
    return pd.to_numeric(t, errors="coerce")


def split_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Keep the sample rows; name and count every other kind of row."""
    sample_no = numbers(df["No"])
    is_sample = sample_no.notna() & sample_no.between(1, 100_000)

    kept = df[is_sample.to_numpy()].copy()
    kept.insert(0, "SampleNo", sample_no[is_sample.to_numpy()].astype(int))

    kinds: dict = {}
    for _, r in df[~is_sample.to_numpy()].iterrows():
        label = r.get("No")
        if r.isna().all():
            kind = "blank rows"
        elif isinstance(label, str) and label.strip().lower().startswith(
                ("average", "critical")):
            kind = "in-sheet subtotals (Average / Critical Value)"
        elif sum(isinstance(v, str) and v.strip() in UNIT_TOKENS for v in r.values) >= 3:
            kind = "units row"
        else:
            kind = "rating legend below the table"
        kinds[kind] = kinds.get(kind, 0) + 1
    return kept.reset_index(drop=True), kinds


def build(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return (georeferences, wet chemistry, quality report)."""
    n_sheet = len(df)
    kept, dropped = split_rows(df)

    dup = int(kept["SampleNo"].duplicated().sum())
    if dup:
        raise ValueError(f"{dup} duplicated sample numbers; the sample is the group "
                         f"key, so it has to be unique")

    ssn = "UG25-" + kept["SampleNo"].map(lambda n: f"{n:03d}")

    lat = numbers(kept["Latitude"])
    lon = numbers(kept["Longitude"])

    geo = pd.DataFrame({
        "SSN": ssn,
        "Latitude": lat,
        "Longitude": lon,
        "Country": "Uganda",
        "SiteName": kept["Demo host"].astype("string").str.strip(),
        "Agronomist": kept["Agronomist"].astype("string").str.strip(),
        "Crop": kept["Crop on Demo"].astype("string").str.strip(),
        "SampleNo": kept["SampleNo"].astype(int),
    })

    om = numbers(kept["OM"])
    ph = numbers(kept["pH"])

    wet = pd.DataFrame({
        "SSN": ssn,
        "pH_H2O": ph,
        "EC": np.nan,                       # absent at source, see module docstring
        "Clay percent": numbers(kept["Clay"]),
        "Sand percent": numbers(kept["Sand"]),
        "Silt percent": numbers(kept["Silt"]),
        TARGET: om / OM_TO_C,
        "OM percent": om,
        "carbon_source": f"OM percent / {OM_TO_C:.3f}",
    })

    # Name every distinct measurement record.  Ten of the eleven chemistry
    # columns repeat verbatim in blocks of 16-23 rows while pH varies, which is
    # a filled-down look-up table rather than 258 measured soils.  The pattern
    # id keeps the fact visible in the data instead of only in this docstring.
    repeat_key = (kept[REPEAT_CHECK_COLUMNS]
                  .apply(pd.to_numeric, errors="coerce").round(6)
                  .apply(lambda r: "|".join("" if pd.isna(v) else f"{v:g}" for v in r),
                         axis=1))
    codes, uniques = pd.factorize(repeat_key, sort=True)
    wet["record_pattern"] = [f"P{c + 1:03d}" for c in codes]

    # --- quality report: what the source contained, before anything is dropped
    q: dict = {
        "rows_in_sheet": n_sheet,
        "rows_dropped_as_not_samples": dropped,
        "duplicate_sample_numbers": dup,
        "sample_rows": int(len(kept)),
        "coordinate_defects": {
            "missing": int((lat.isna() | lon.isna()).sum()),
            "out_of_range": int(((lat.abs() > 90) | (lon.abs() > 180)).sum()),
            "out_of_range_values": [float(v) for v in lon[lon.abs() > 180].dropna()],
            "repaired_trailing_apostrophe": int(
                kept["Latitude"].astype(str).str.strip().str.match(r"^-?[\d.]+[\u2032'\"]+$").sum()),
        },
        "non_numeric_cells": {},
        "out_of_bounds_values": {},
        "texture_sum": {},
        "om": {}, "carbon": {},
    }
    for col in ["pH", "OM", "Clay", "Sand", "Silt"]:
        q["non_numeric_cells"][col] = int(
            (numbers(kept[col]).isna() & kept[col].notna()).sum())
    for col, (lo, hi) in BOUNDS.items():
        if col not in wet.columns:
            continue
        v = pd.to_numeric(wet[col], errors="coerce")
        q["out_of_bounds_values"][col] = int(((v < lo) | (v > hi)).sum())

    total = wet[["Clay percent", "Sand percent", "Silt percent"]].sum(axis=1, min_count=3)
    q["texture_sum"] = {
        "complete_rows": int(total.notna().sum()),
        "off_by_more_than_5": int(((total - 100).abs() > 5).sum()),
        "min": float(total.min()), "max": float(total.max()),
    }
    if om.notna().any():
        q["om"] = {"median_percent": round(float(om.median()), 3),
                   "min_percent": float(om.min()), "max_percent": float(om.max()),
                   "complete_rows": int(om.notna().sum())}
        carbon = om / OM_TO_C
        q["carbon"] = {
            "factor_om_to_c": round(OM_TO_C, 4),
            "median_percent": round(float(carbon.median()), 3),
            "measured": False,
        }
    q["ph"] = {"median": round(float(ph.median()), 2) if ph.notna().any() else None,
               "max": float(ph.max()) if ph.notna().any() else None,
               "rows_above_ph_6.5_where_carbonates_are_possible":
                   int((ph > 6.5).sum())}
    q["complete_rows_all_five_inputs"] = int(
        wet[FEATURES].notna().all(axis=1).sum())
    q["complete_rows_four_inputs_no_ec"] = int(
        wet[[f for f in FEATURES if f != "EC"]].notna().all(axis=1).sum())
    q["rows_with_target"] = int(wet[TARGET].notna().sum())

    sizes = pd.Series(codes).value_counts()
    q["repeated_records"] = {
        "columns_compared": REPEAT_CHECK_COLUMNS,
        "rows": int(len(codes)),
        "distinct_patterns": int(len(uniques)),
        "surplus_rows": int(len(codes) - len(uniques)),
        "rows_in_a_repeated_pattern": int(sizes[sizes > 1].sum()),
        "largest_pattern": int(sizes.max()),
        "patterns_appearing_once": int((sizes == 1).sum()),
        "note": "the ten OM..Silt columns repeat verbatim in blocks of 16-23 rows "
                "while pH varies, so they carry a filled-down value rather than a "
                "per-farm measurement. record_pattern names each distinct vector: "
                "identical rows must share a fold, or a cross-validated score "
                "measures recall of that table instead of prediction.",
    }
    return geo, wet, q


def write(geo: pd.DataFrame, wet: pd.DataFrame, q: dict) -> dict:
    geo_dir = OUT / "Georeferences"
    lab_dir = OUT / "Wet_Chemistry" / LAB
    geo_dir.mkdir(parents=True, exist_ok=True)
    lab_dir.mkdir(parents=True, exist_ok=True)

    geo_p = geo_dir / "georeferences.csv"
    wet_p = lab_dir / f"Wet_Chemistry_{LAB}.csv"
    geo.to_csv(geo_p, index=False, lineterminator="\n")
    wet.to_csv(wet_p, index=False, lineterminator="\n")

    joined = geo.merge(wet, on="SSN", how="inner")
    manifest = {
        "purpose": "canonical Ugandan dataset for afsis_experiment.py",
        "source": {
            "file": SRC.name,
            "sheet": SHEET,
            "sha256": sha256_file(SRC),
        },
        "column_map": {
            "No": "SSN (UG25-<sample number>)",
            "Latitude": "Latitude", "Longitude": "Longitude",
            "pH": "pH_H2O",
            "Clay": "Clay percent", "Sand": "Sand percent", "Silt": "Silt percent",
            "OM": f"OM percent, and {TARGET} = OM / {OM_TO_C:.3f}",
            "Demo host": "SiteName (reporting only)",
            "Agronomist": "Agronomist (reporting only)",
            "Crop on Demo": "Crop (reporting only)",
        },
        "absent_at_source": {
            "EC": "the workbook has no electrical conductivity column; EC is "
                  "written empty so the table keeps the project's five inputs",
        },
        "derived_target": {
            "column": TARGET,
            "from": "OM percent",
            "formula": f"OM percent / {OM_TO_C:.4f} (Van Bemmelen, 1/0.58)",
            "measured": False,
            "why": "the workbook measures organic matter, not carbon; the pipeline "
                   "targets total carbon, so a conversion is required or the "
                   "dataset has no target at all",
            "limitation": "OM/1.724 estimates organic carbon; AfSIS total carbon "
                          "includes any inorganic fraction, so the two scales are "
                          "assumed equal here, not proved equal",
            "support": "carbonate is not expected below about pH 6.5; the count of "
                       "samples above that line is reported in quality.ph",
            "traceability": "carbon_source column repeats the conversion per row",
        },
        "layout": {
            "georeferences": "Georeferences/georeferences.csv",
            "wet_chemistry": f"Wet_Chemistry/{LAB}/Wet_Chemistry_{LAB}.csv",
            "join": "SSN, one row per sample",
        },
        "grouping": "SSN, one row per sample. SiteName (demo host) is reported but "
                    "is deliberately not named SiteID: clean() deduplicates on "
                    "[group key, lab], so a coarser key would keep one row per "
                    "farm and discard the rest.",
        "cleaning": "nothing imputed, aggregated or clamped here; out-of-bounds "
                    "values are left for afsis_data.clean() to report",
        "counts": {
            "joined_rows": int(len(joined)),
            "with_coordinates": int((geo["Latitude"].notna() & geo["Longitude"].notna()).sum()),
            "distinct_hosts": int(geo["SiteName"].nunique()),
            "distinct_crops": int(geo["Crop"].nunique()),
        },
        "quality": q,
        "target": TARGET,
        "target_note": "not measured: estimated from organic matter, see derived_target",
        "attribution": {
            "credit": "2025 farmer demonstration soils; the agronomists who collected "
                       "them are named in the Georeferences table",
            "warning": "afsis_experiment.py labels any root without a synthetic marker "
                       "as 'afsis_real' and prints the AfSIS credit, which is the wrong "
                       "attribution for this dataset. Until a run can be told this "
                       "source kind, a bundle produced from this root must not be "
                       "cited.",
        },
        "run": "python afsis_experiment.py --root data/uganda_2025 "
               f'--target "{TARGET}" --drop-features EC',
        "run_note": "--drop-features EC is required: EC is absent at source, so a "
                    "five-feature model cannot score or train on these rows",
        "known_defect": "the repeated chemistry blocks in quality.repeated_records "
                        "inflate any cross-validated score computed from this root, "
                        "because identical rows are split across folds; the workbook "
                        "needs correcting, or the run needs to group on "
                        "record_pattern, before a score from it means anything",
    }
    (OUT / "COALESCE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return manifest


def check() -> None:
    """Prove the result loads, detects and cleans through the project's own code."""
    import afsis_data as A
    import afsis_validation as V

    df, manifest = A.load_raw(OUT)
    print(f"\n[check] load_raw   : {len(df)} rows from {len(manifest)} files")
    schema = A.detect_schema(df, {"target": TARGET})
    print(f"[check] target     : {schema.target} ({schema.origin['target']})")
    print(f"[check] features   : {schema.features}")
    print(f"[check] group key  : {schema.group_key()}")
    print(f"[check] lat/lon    : {schema.lat} / {schema.lon}")
    missing = [f for f in FEATURES if f not in schema.features]
    if missing or schema.target != TARGET:
        raise SystemExit(f"[check] FAILED: features missing {missing}")
    cleaned, log = A.clean(df, schema, {"depth": A.DEPTH_TARGET_CM,
                                        "lab_dupes": "first", "target_units": "auto"})
    print(f"[check] clean      : {len(df)} -> {len(cleaned)} rows")
    for e in log:
        if e["n_removed"]:
            print(f"          - {e['step']}: -{e['n_removed']} ({e['reason']})")
    unit = next((e for e in log if e["step"] == "final"), {})
    print(f"[check] target units: {unit.get('target_units')} "
          f"({unit.get('units_basis')})")
    coords = cleaned[[schema.lat, schema.lon]].to_numpy(float)
    groups, diag = V.spatial_groups(coords, cleaned[schema.group_key()].to_numpy(),
                                    blocks=5, seed=20261104)
    print(f"[check] blocks     : {len(set(groups))} spatial groups, "
          f"sizes {sorted(np.bincount(groups))}")
    print(f"[check] block diag : {diag}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="after writing, load the result through afsis_data and print "
                         "the schema and the cleaning ledger")
    a = ap.parse_args()

    if not SRC.is_file():
        raise SystemExit(f"{SRC} not found; run this from the project root")
    df = pd.read_excel(SRC, sheet_name=SHEET)
    geo, wet, quality = build(df)
    manifest = write(geo, wet, quality)

    print(f"source          : {SRC.name} ({quality['rows_in_sheet']} rows)")
    for kind, n in quality["rows_dropped_as_not_samples"].items():
        print(f"  not a sample  : {kind} ({n})")
    print(f"samples         : {quality['sample_rows']} -> {len(wet)} rows written")
    print(f"target          : {TARGET} = OM percent / {OM_TO_C:.3f} "
          f"(median {quality['carbon'].get('median_percent')} g/100 g) "
          f"- ESTIMATED, NOT MEASURED")
    print(f"EC              : absent at source, written empty")
    print(f"missing coords  : {quality['coordinate_defects']['missing']}")
    print(f"out of range lon: {quality['coordinate_defects']['out_of_range']} "
          f"{quality['coordinate_defects']['out_of_range_values']}")
    print(f"texture sum 100 : {quality['texture_sum']['complete_rows']} rows, "
          f"{quality['texture_sum']['off_by_more_than_5']} off by more than 5")
    print(f"complete (4/5)  : {quality['complete_rows_four_inputs_no_ec']} rows")
    rr = quality["repeated_records"]
    print(f"repeated blocks : {rr['distinct_patterns']} distinct records in "
          f"{rr['rows']} rows ({rr['rows_in_a_repeated_pattern']} rows share a "
          f"pattern; largest {rr['largest_pattern']})")
    print(f"attribution     : outputs from this root are labelled afsis_real by the "
          f"pipeline; see COALESCE_MANIFEST.json -> attribution")
    print(f"written         : {OUT}/  ->  Georeferences/, Wet_Chemistry/{LAB}/, "
          f"COALESCE_MANIFEST.json")
    print(f"run with        : {manifest['run']}")

    if a.check:
        check()


if __name__ == "__main__":
    main()
