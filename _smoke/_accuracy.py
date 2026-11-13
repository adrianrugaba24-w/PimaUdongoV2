"""Print the accuracy figures needed for the report, straight from the bundles."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BUNDLES = [
    ("AfSIS, five inputs (shipped)", "export_afsis_real"),
    ("AfSIS, pH + EC only", "export_afsis_notexture"),
    ("AfSIS, EC removed", "_smoke/afsis_noec"),
    ("AfSIS, EC imputed", "_smoke/afsis_ec_imputed_run"),
    ("Uganda, grouped per sample", "_smoke/uganda_ssn"),
    ("Uganda, grouped per chemistry pattern", "_smoke/uganda_pattern"),
]

for label, path in BUNDLES:
    p = Path(path) / "results.json"
    if not p.is_file():
        print(f"\n{label}: MISSING ({p})")
        continue
    r = json.loads(p.read_text(encoding="utf-8"))
    h = r.get("headline", {})
    print(f"\n=== {label}  [{path}]")
    print(f"  rows: {r.get('n_rows')}  features: {len(r.get('features', []))}")
    print(f"  headline model: {h.get('model')}")
    for k in ("r2_spatial", "ramse"):  # placeholder, replaced below
        pass
    for k in ("r2_spatial", "rmse_spatial", "mae_spatial", "rpiq_spatial",
              "r2_random", "rmse_random", "rpiq_random", "beats_field_mean_spatially"):
        if k in h:
            print(f"  {k:32s} {h[k]}")
    cv = r.get("conformal") or r.get("interval") or {}
    if isinstance(cv, dict):
        for k in ("model", "coverage", "width", "nominal"):
            if k in cv:
                print(f"  conformal.{k:22s} {cv[k]}")
