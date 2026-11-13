"""Compact accuracy extract for the email: main table minus tuned params."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

FIELDS = ("model", "cv", "r2_mean", "r2_sd", "rmse_mean", "mae_mean", "rpiq_mean")

for path in ("export_afsis_real", "_smoke/uganda_pattern"):
    r = json.loads((Path(path) / "results.json").read_text(encoding="utf-8"))
    print(f"\n=== {path}")
    for row in r["results"]["main"]:
        if row.get("noise") not in (0.0, None):
            continue
        vals = []
        for f in FIELDS:
            v = row.get(f)
            vals.append(f"{v:.4f}" if isinstance(v, float) else str(v))
        print("  " + " | ".join(vals))
    iv = r["results"].get("interval")
    print("  interval:", json.dumps(iv) if not isinstance(iv, dict) else
          {k: iv[k] for k in list(iv) if k in ("model", "nominal", "coverage",
                                               "width", "width_mean", "cv")})
    v = r["results"].get("validation_gap")
    if isinstance(v, list):
        for row in v:
            print("  gap:", {k: (round(x, 4) if isinstance(x, float) else x)
                             for k, x in row.items() if k in ("model", "gap", "r2_spatial", "r2_random")})
