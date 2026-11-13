"""Per-model accuracy for the shipped AfSIS bundle, as the report needs it."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

for path in ("export_afsis_real", "export_afsis_notexture"):
    r = json.loads((Path(path) / "results.json").read_text(encoding="utf-8"))
    res = r["results"]
    print(f"\n=== {path}")
    print("  results keys:", list(res)[:12])
    for k, v in res.items():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "model" in v[0]:
            print(f"  [{k}] rows={len(v)} fields={list(v[0])}")
            for row in v:
                if row.get("split") in (None, "spatial") or "split" not in row:
                    print("   ", {kk: (round(vv, 4) if isinstance(vv, float) else vv)
                                  for kk, vv in row.items()})
            break
    d = r.get("data", {})
    print("  data:", {k: d[k] for k in list(d)[:8]})
    print("  target:", r.get("target"))
