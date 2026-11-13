# Dataset review register

Purpose: decide which datasets can carry the pathway — measure → predict → recommend —
and which cannot, before any code is written for a new bundle.

Verified facts are marked with a source. Anything marked **TBC** has not been checked and
must be checked by running the command in section 5, not assumed.

---

## 1. The review axis

A recommendation needs three different things, and almost no dataset supplies more than
the first:

| Layer | What it is | Who supplies it |
|---|---|---|
| **L1 Status** | Measured indicator values: pH, OC, N, P, K, CEC, texture, EC | Soil profile databases |
| **L2 Thresholds** | What counts as low / adequate / high, per indicator and crop | Literature and national guidance, not databases |
| **L3 Response** | What happens to the crop if the farmer acts | Fertiliser trial networks |

AfSIS supplies L1 only, for one target. Replacing it with another L1 database leaves
layers 2 and 3 exactly where they are. That is the test each candidate is scored against.

Practical criteria, weighted equally:
1. Ugandan rows
2. Indicator breadth
3. Measured vs modelled
4. Licence clarity
5. Effort to integrate

---

## 2. Longlist

| # | Dataset | What it holds | Coverage | Licence | Layer | Verdict |
|---|---|---|---|---|---|---|
| S1 | **AfSIS Phase I** (held in `afsis/`) | 926 georeferenced samples, 58 sites, 19 countries; M3 P/K/Ca/Mg/S/Zn/B, ExBas+ExAc, total N, total C, pH, EC, texture | 32 Ugandan rows | ODC-By | L1 | **Retain** as validation evidence |
| S2 | **Africa Soil Profiles Database v1.2** (ISRIC) | 18,532 unique profiles; analytical data for 15,564; 14,197 georeferenced; 38 countries; temporal extent 1925–2011 | Uganda **TBC** | Not stated on the record — confirm | L1 | **Shortlist** |
| S3 | **WoSIS** (ISRIC) | 230,000+ profiles, 174 countries, 900,000+ layers, harmonised and quality-assessed | Uganda **TBC** | Per snapshot — confirm | L1 | **Shortlist** |
| S4 | **iSDAsoil 30 m** | ~23 properties, two depths, predicted surfaces across Africa | Modelled everywhere | Confirm at download | Modelled | Covariates only |
| S5 | **SoilGrids 250 m** | Predicted properties, global | Modelled everywhere | CC-BY (confirm) | Modelled | Covariates only |
| S6 | **GSOCmap / GSOCseq** (FAO) | Modelled soil organic carbon, policy resolution | Global | Open | Modelled | Context figure only |
| S7 | **NARO Kawanda soil fertility data** | Ugandan measured profiles and fertility trials | Uganda | By request | L1 + L3 | **Shortlist** |
| S8 | **Uganda National Soil Survey / MAAIF district surveys** | Legacy memoirs and district maps, 1960s–90s, mostly qualitative classes | Uganda | Public documents, not data files | L1 (weak) | Background only |
| S9 | **OFRA / AGRA / NARO fertiliser response trials** | Yield response to nutrient application by site | Africa-wide, site-specific | By request | **L3** | **Critical dependency** |
| S10 | **Africa RISING / CIMMYT trial data** (Dataverse) | Trial-level yield and management data, includes Ugandan sites | Uganda **TBC** | Per dataset | L3 | Shortlist for L3 |
| S11 | UBOS annual agricultural survey | Farm and area statistics, no soil | Uganda | Open | — | Reject |
| S12 | LUCAS Soil (EU) | Rich, measured, multi-indicator | Europe | Open | L1 | Reject — geography |
| S13 | **Soil of Farmers 2025 Reviewed** (held in `Soil of Farmers 2025 Reviewed.xlsx`) | 258 farmer demo plots, 224 hosts, 11 crops; pH, OM, N, P, K, Na, Ca, Mg, sand/clay/silt, Fe, Zn, S, B; no EC | Uganda (258 rows) | Not stated on the record — confirm | L1 | **Loadable, not yet usable** — see 4a |

---

## 3. Shortlist, scored

Scores 0–3 per criterion; totals out of 15.

| Dataset | Uganda rows | Breadth | Measured | Licence | Effort | Total |
|---|---|---|---|---|---|---|
| S2 AfSP v1.2 | TBC | 3 | 2 (legacy, mixed methods) | 1 | 2 | **TBC** |
| S3 WoSIS | TBC | 3 | 3 (harmonised) | 1 | 2 | **TBC** |
| S7 NARO | 3 (if granted) | 3 | 3 | 0 (request) | 0 (slow) | **TBC** |
| S1 AfSIS (retained) | 1 | 3 | 3 | 3 | 3 | **13 / 15** |

No total is quoted until the Uganda counts are known. Filling them in is the first action.

---

## 4. What each shortlisted source can support

**S2 AfSP v1.2 — the best African-context fit.**
18,532 profiles with analytical data on 15,564, from 38 countries. Legacy data means old
methods, uneven sampling density and no management history, so it supports a *status
index* and a nationwide picture, not a response model. Its 1925–2011 temporal extent also
means no time series per site in practice.

**S3 WoSIS — the deepest, but you must subset hard.**
230,000 profiles harmonised to standard procedures is the highest-quality L1 available.
Uganda is a small slice of it; the work is subsetting, harmonising units against S2, and
recording which laboratory method produced each value.

**S7 NARO — the only genuinely Ugandan measured L1.**
Access is the whole risk. If granted, it becomes the primary source and AfSP/WoSIS become
comparison sets.

**S9/S10 — the only route to a recommendation.**
Without a response layer, any action the app suggests is a threshold judgement, not an
evidenced outcome. This must be stated plainly on the poster, or the recommendation
section should not claim outcome benefit.

---

## 4a. S13, the 2025 farmer workbook

Prepared by `prepare_uganda_2025.py` into `data/uganda_2025/`, in the same layout as
S1, so `afsis_data.load_raw` / `detect_schema` / `clean` serve it unchanged.
258 samples survive cleaning at 254 (three have no coordinates, one longitude reads
3244196 — a projected value, not a degree).

What it supplies: the most Ugandan field context in the project, and the only source
whose pH, texture and organic matter come from named farms.

What it cannot supply yet:

1. **No EC.** The five-feature model cannot score these rows; a run must pass
   `--drop-features EC`.
2. **No measured carbon.** The target is `Total carbon = OM / 1.724` (Van Bemmelen).
   The manifest marks it `measured: false` and says why the two scales are assumed
   equal: below about pH 6.5 carbonate is not expected, and 10 of 254 samples sit
   above that line.
3. **The chemistry columns are a filled-down table, not measurements.** OM, N, P, K,
   Na, Ca, Mg, sand, clay and silt repeat verbatim in blocks of 16–23 rows while pH
   varies: 79 distinct vectors across 258 rows, 214 rows sharing one. Every row carries
   a `record_pattern` id, and the manifest records the defect under `known_defect`.
   Until the workbook is corrected, or folds are grouped on `record_pattern`, a
   cross-validated score from this root is inflated and must not be quoted.

Verdict: keep as the Ugandan *context* source and the template for what a corrected
sheet must contain. Do not treat a model score from it as evidence.

---

## 5. Verification to run before any decision

Download (S2): `https://files.isric.org/public/afsp/AF-AfSP1.2.zip`
Download (S3): via the WoSIS dashboard snapshot for the current year.

Then, for each:

```python
import pandas as pd
p = pd.read_csv("AF-AfSP1.2/...site.csv")          # name to confirm after unzip
print(p["COUNTRY"].value_counts().head(20))
print("Uganda profiles:", (p["COUNTRY"] == "Uganda").sum())
lay = pd.read_csv("AF-AfSP1.2/...layer.csv")
print(lay.isna().sum().sort_values().head(30))
```

Record in this file, per source: Ugandan profile count, non-null counts for pH, OC,
total N, P, exchangeable K, CEC and texture, and the method/code columns that say how
each was measured. A profile count without an indicator count is not enough.

Checks that will decide suitability:
1. Fewer than ~100 Ugandan profiles with both P and OC → too thin for an index; S3 or S7
   must carry it.
2. Method codes mixing Olsen and Mehlich-3 P → must be separated, never pooled.
3. Depth increments missing → topsoil subset undefined; document what was used.

---

## 6. Proposed outcome

Keep **S1** as the validation chapter — finished, tested, and the only source that
supports the two-design comparison.

Add one new L1 bundle from **S2 or S3** (whichever has usable Ugandan coverage) plus, if
granted, **S7**. Build the index on that. Declare the L3 gap explicitly and cite the
literature for L2.

A clean break from AfSIS would discard the finished result and still leave the
recommendation layer unsupported. The register says so on its face: no shortlisted
dataset supplies L3.

---

## 7. Next actions

1. Download S2, run section 5, fill the Uganda counts. Half a day.
2. Ask NARO Kawanda and MAAIF for S7 access; ask in writing the same day, since the reply
   is the long pole.
3. Confirm licences for S2 and S3 from their own files, not from this document.
4. Only then decide between S2 and S3, and write the new schema.
