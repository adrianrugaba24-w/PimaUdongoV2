"""Diagnostics for the EC / Ugandan-set alignment question.

1. How many Ugandan samples fall inside the AfSIS 5th-95th percentile on the
   four shared inputs?  (The reliability gate's rule, applied in bulk.)
2. If EC is imputed from the other four inputs, how well can it be predicted
   under spatial blocking?  The auxiliary model in "impute EC" has to beat this
   to be worth anything.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline

import afsis_data as A
import afsis_validation as V

sys.stdout.reconfigure(encoding="utf-8")

A_ROOT = Path("_smoke/afsis_real_fixed")
U_ROOT = Path("data/uganda_2025")
SHARED = ["pH_H2O", "Clay percent", "Sand percent", "Silt percent"]
FIVE = SHARED + ["EC"]


def load(root, target="Total carbon", features=FIVE):
    df, _ = A.load_raw(root)
    schema = A.detect_schema(df, {"target": target, "features": features})
    d, _ = A.clean(df, schema, dict(depth=A.DEPTH_TARGET_CM,
                                    target_units="auto", lab_dupes="first"))
    return d, schema


a, sa = load(A_ROOT)
ranges = {f: (float(np.nanpercentile(a[f], 5)), float(np.nanpercentile(a[f], 95)))
          for f in SHARED}
print("AfSIS training range (p5, p95):")
for f, (lo, hi) in ranges.items():
    print(f"  {f:15s} {lo:9.3f} .. {hi:9.3f}")

u, su = load(U_ROOT, features=SHARED)          # EC absent, so 4 inputs
print(f"\nUgandan rows usable for a four-input model: {len(u)}")

inside = pd.Series(True, index=u.index)
for f, (lo, hi) in ranges.items():
    ok = u[f].between(lo, hi)
    outside = int((~ok).sum())
    print(f"  {f:15s} outside the AfSIS range: {outside:4d} rows  "
          f"({outside / len(u):5.1%})")
    inside &= ok
print(f"\nrows inside ALL four ranges: {int(inside.sum())} of {len(u)} "
      f"({inside.mean():.1%})")

# ---- 2. can EC be recovered from the other four? -------------------------
X = a[SHARED].to_numpy(float)
y = a["EC"].to_numpy(float)
ids = a[sa.group_key()].to_numpy()
coords = a[[sa.lat, sa.lon]].to_numpy(float)
groups, _ = V.spatial_groups(coords, ids, 10, 20261104)

pipe = Pipeline([("impute", SimpleImputer(strategy="median")),
                 ("model", RandomForestRegressor(n_estimators=100,
                                                 min_samples_leaf=3,
                                                 max_features=0.5,
                                                 random_state=20261104, n_jobs=1))])
pred = np.full(len(y), np.nan)
for tr, te in GroupKFold(5).split(X, y, groups):
    p = pipe.fit(X[tr], y[tr])
    pred[te] = p.predict(X[te])

ok = np.isfinite(pred) & np.isfinite(y)
resid = pred[ok] - y[ok]
sst = float(((y[ok] - y[ok].mean()) ** 2).sum())
print("\nAuxiliary model: EC from pH + clay + sand + silt, spatial CV")
print(f"  R2 (blocked)  : {1 - float((resid ** 2).sum()) / sst:+.3f}")
print(f"  RMSE dS/m     : {float(np.sqrt((resid ** 2).mean())):.3f}  "
      f"(EC median {float(np.median(y)):.3f}, p95 {float(np.percentile(y, 95)):.3f})")
print(f"  rows          : {int(ok.sum())}")
