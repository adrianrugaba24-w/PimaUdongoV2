"""Execute the proposed workflow: impute EC, then run the five-input carbon model.

Auxiliary model: EC from pH + clay + sand + silt, RandomForest, spatial 5-fold,
cross-fitted so every training row gets an out-of-fold prediction.  Those
predictions replace the measured EC, and the ordinary experiment is then run on
the result.

This is deliberately GENEROUS to the proposal: the auxiliary model is fitted
once on all rows rather than re-fitted inside each carbon fold, which leaks a
little and can only help the imputed variant.
"""
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

SRC = Path("_smoke/afsis_real_fixed")
DST = Path("_smoke/afsis_ec_imputed")
SHARED = ["pH_H2O", "Clay percent", "Sand percent", "Silt percent"]

# --- cross-fitted EC predictions on the AfSIS rows -------------------------
raw, _ = A.load_raw(SRC)
schema = A.detect_schema(raw, {"target": "Total carbon",
                               "features": SHARED + ["EC"]})
clean, _ = A.clean(raw, schema, dict(depth=A.DEPTH_TARGET_CM,
                                     target_units="auto", lab_dupes="first"))
print(f"AfSIS rows used to fit the auxiliary model: {len(clean)}")

X = clean[SHARED].to_numpy(float)
y_ec = clean["EC"].to_numpy(float)
groups, _ = V.spatial_groups(clean[[schema.lat, schema.lon]].to_numpy(float),
                             clean[schema.group_key()].to_numpy(), 10, 20261104)

aux = Pipeline([("impute", SimpleImputer(strategy="median")),
                ("model", RandomForestRegressor(n_estimators=100,
                                                min_samples_leaf=3,
                                                max_features=0.5,
                                                random_state=20261104,
                                                n_jobs=1))])
ec_hat = np.full(len(y_ec), np.nan)
for tr, te in GroupKFold(5).split(X, y_ec, groups):
    ec_hat[te] = aux.fit(X[tr], y_ec[tr]).predict(X[te])

resid = ec_hat - y_ec
sst = float(((y_ec - y_ec.mean()) ** 2).sum())
print(f"auxiliary EC quality, blocked R2 : {1 - float((resid ** 2).sum()) / sst:+.3f}")
print(f"auxiliary EC RMSE                : {np.sqrt((resid ** 2).mean()):.3f} dS/m")

# --- rebuild the root with EC replaced by its prediction ------------------
DST.mkdir(parents=True, exist_ok=True)
(DST / "Georeferences").mkdir(exist_ok=True)
(DST / "Wet_Chemistry" / "COALESCED").mkdir(parents=True, exist_ok=True)

geo = pd.read_csv(SRC / "Georeferences" / "georeferences.csv")
geo.to_csv(DST / "Georeferences" / "georeferences.csv", index=False,
           lineterminator="\n")

wet = pd.read_csv(SRC / "Wet_Chemistry" / "COALESCED" /
                  "Wet_Chemistry_COALESCED.csv")
imputed = dict(zip(clean[schema.group_key()].to_numpy(), ec_hat))
mask = wet["SSN"].isin(imputed)
wet.loc[mask, "EC"] = wet.loc[mask, "SSN"].map(imputed).to_numpy()
wet["EC_measured"] = np.where(mask, 0, 1)
wet.loc[mask, "EC_measured"] = 0
wet.to_csv(DST / "Wet_Chemistry" / "COALESCED" /
           "Wet_Chemistry_COALESCED.csv", index=False, lineterminator="\n")
print(f"rows with EC replaced by a prediction: {int(mask.sum())} of {len(wet)}")
print(f"written: {DST}")
