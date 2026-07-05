"""
Master retraining script — uses all real CSV datasets
Targets 97%+ accuracy with fast inference (no heavy ensembles)
Run from: d:\\innovent\\backend\\ml
"""
import os, warnings
import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, r2_score, mean_absolute_error

warnings.filterwarnings("ignore")

NASA_TRAIN  = r"C:\Users\kaviy\OneDrive\Desktop\archive (6)\train_FD001.txt"
AI4I_CSV    = r"C:\Users\kaviy\OneDrive\Desktop\ai4i2020.csv"
VEHICLE_CSV = r"C:\Users\kaviy\OneDrive\Desktop\vehicle_maintenance_data.csv"

OUT = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────────────────────────────────────
# 1. FAILURE MODEL  (ai4i2020 + vehicle_maintenance_data)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("1. FAILURE MODEL")
print("="*60)

ai4i = pd.read_csv(AI4I_CSV)
ai4i = ai4i.drop(columns=["UDI", "Product ID"])
le_type = LabelEncoder()
ai4i["Type"] = le_type.fit_transform(ai4i["Type"])

# vehicle_maintenance_data — map to same feature space
vm = pd.read_csv(VEHICLE_CSV)
cond_map = {"New": 0, "Good": 1, "Worn Out": 2}
bat_map  = {"Good": 0, "Weak": 1, "Dead": 2}
vm["tire_enc"]  = vm["Tire_Condition"].map(cond_map).fillna(1)
vm["brake_enc"] = vm["Brake_Condition"].map(cond_map).fillna(1)
vm["bat_enc"]   = vm["Battery_Status"].map(bat_map).fillna(1)

# Map vehicle_maintenance columns → ai4i feature space
vm_mapped = pd.DataFrame({
    "Type":                        (vm["bat_enc"] + vm["brake_enc"]) // 2,
    "Air temperature [K]":         295 + (vm["Mileage"] / vm["Mileage"].max()) * 15,
    "Process temperature [K]":     305 + (vm["Mileage"] / vm["Mileage"].max()) * 10,
    "Rotational speed [rpm]":      1200 + (vm["Engine_Size"] / vm["Engine_Size"].max()) * 1500,
    "Torque [Nm]":                 20 + vm["tire_enc"] * 10 + vm["brake_enc"] * 10,
    "Tool wear [min]":             (vm["Odometer_Reading"] / vm["Odometer_Reading"].max() * 200).round(),
    "TWF":                         (vm["tire_enc"] == 2).astype(int),
    "HDF":                         (vm["brake_enc"] == 2).astype(int),
    "PWF":                         (vm["bat_enc"] >= 1).astype(int),
    "OSF":                         vm["Reported_Issues"].clip(0, 1),
    "RNF":                         0,
    "Machine failure":             vm["Need_Maintenance"],
})

feat_cols = ["Type","Air temperature [K]","Process temperature [K]",
             "Rotational speed [rpm]","Torque [Nm]","Tool wear [min]",
             "TWF","HDF","PWF","OSF","RNF"]

combined = pd.concat([
    ai4i[feat_cols + ["Machine failure"]],
    vm_mapped
], ignore_index=True)

X_f = combined[feat_cols]
y_f = combined["Machine failure"]

X_tr, X_te, y_tr, y_te = train_test_split(X_f, y_f, test_size=0.2, random_state=42, stratify=y_f)

# GradientBoosting — fast inference, high accuracy
failure_model = GradientBoostingClassifier(
    n_estimators=200, max_depth=5, learning_rate=0.1,
    subsample=0.8, random_state=42
)
failure_model.fit(X_tr, y_tr)
acc = accuracy_score(y_te, failure_model.predict(X_te))
print(f"Failure Model Accuracy: {acc*100:.2f}%")

joblib.dump(failure_model, os.path.join(OUT, "failure_model.pkl"))
print("Saved failure_model.pkl")


# ─────────────────────────────────────────────────────────────────────────────
# 2. HEALTH MODEL  (ai4i2020 + vehicle_maintenance_data)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("2. HEALTH MODEL")
print("="*60)

ai4i2 = pd.read_csv(AI4I_CSV).drop(columns=["UDI","Product ID"])
ai4i2["Type"] = LabelEncoder().fit_transform(ai4i2["Type"])

# Build health score target
ai4i2["health_score"] = 100
ai4i2.loc[ai4i2["HDF"]==1, "health_score"] -= 20
ai4i2.loc[ai4i2["PWF"]==1, "health_score"] -= 20
ai4i2.loc[ai4i2["TWF"]==1, "health_score"] -= 20
ai4i2.loc[ai4i2["OSF"]==1, "health_score"] -= 20
ai4i2.loc[ai4i2["RNF"]==1, "health_score"] -= 20
ai4i2["health_score"] -= (ai4i2["Tool wear [min]"] / 250) * 10
ai4i2["health_score"] -= ((ai4i2["Torque [Nm]"] - 40) / 40).clip(0,1) * 5
ai4i2["health_score"] -= ((ai4i2["Process temperature [K]"] - 310) / 10).clip(0,1) * 5
ai4i2["health_score"] = ai4i2["health_score"].clip(5, 100).round(2)

# Add vehicle_maintenance rows as health targets
vm2 = pd.read_csv(VEHICLE_CSV)
vm2["tire_enc"]  = vm2["Tire_Condition"].map(cond_map).fillna(1)
vm2["brake_enc"] = vm2["Brake_Condition"].map(cond_map).fillna(1)
vm2["bat_enc"]   = vm2["Battery_Status"].map(bat_map).fillna(1)
vm2["health_score"] = (
    100
    - vm2["tire_enc"] * 10
    - vm2["brake_enc"] * 10
    - vm2["bat_enc"] * 15
    - (vm2["Reported_Issues"] * 5).clip(0, 20)
    - (vm2["Accident_History"] * 5).clip(0, 15)
).clip(5, 100)

vm2_mapped = pd.DataFrame({
    "Type":                        (vm2["bat_enc"] + vm2["brake_enc"]) // 2,
    "Air temperature [K]":         295 + (vm2["Mileage"] / vm2["Mileage"].max()) * 15,
    "Process temperature [K]":     305 + (vm2["Mileage"] / vm2["Mileage"].max()) * 10,
    "Rotational speed [rpm]":      1200 + (vm2["Engine_Size"] / vm2["Engine_Size"].max()) * 1500,
    "Torque [Nm]":                 20 + vm2["tire_enc"] * 10 + vm2["brake_enc"] * 10,
    "Tool wear [min]":             (vm2["Odometer_Reading"] / vm2["Odometer_Reading"].max() * 200).round(),
    "TWF":                         (vm2["tire_enc"] == 2).astype(int),
    "HDF":                         (vm2["brake_enc"] == 2).astype(int),
    "PWF":                         (vm2["bat_enc"] >= 1).astype(int),
    "OSF":                         vm2["Reported_Issues"].clip(0,1),
    "RNF":                         0,
    "health_score":                vm2["health_score"],
})

h_combined = pd.concat([
    ai4i2[feat_cols + ["health_score"]],
    vm2_mapped
], ignore_index=True)

X_h = h_combined[feat_cols]
y_h = h_combined["health_score"]

X_tr2, X_te2, y_tr2, y_te2 = train_test_split(X_h, y_h, test_size=0.2, random_state=42)

health_model = GradientBoostingRegressor(
    n_estimators=200, max_depth=5, learning_rate=0.1,
    subsample=0.8, random_state=42
)
health_model.fit(X_tr2, y_tr2)
r2  = r2_score(y_te2, health_model.predict(X_te2))
mae = mean_absolute_error(y_te2, health_model.predict(X_te2))
print(f"Health Model  R²: {r2:.4f}  MAE: {mae:.2f}")

joblib.dump(health_model, os.path.join(OUT, "health_model.pkl"))
print("Saved health_model.pkl")


# ─────────────────────────────────────────────────────────────────────────────
# 3. RUL MODEL  (NASA CMAPSS FD001 — all 4 datasets combined)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("3. RUL MODEL  (NASA CMAPSS)")
print("="*60)

nasa_cols = ["engine_id","cycle","op1","op2","op3",
             "s1","s2","s3","s4","s5","s6","s7","s8","s9","s10",
             "s11","s12","s13","s14","s15","s16","s17","s18","s19","s20","s21"]

nasa_frames = []
for fname in ["train_FD001.txt","train_FD002.txt","train_FD003.txt","train_FD004.txt"]:
    fpath = os.path.join(r"C:\Users\kaviy\OneDrive\Desktop\archive (6)", fname)
    if os.path.exists(fpath):
        tmp = pd.read_csv(fpath, sep=r"\s+", header=None, names=nasa_cols)
        nasa_frames.append(tmp)

nasa = pd.concat(nasa_frames, ignore_index=True)
print(f"NASA combined shape: {nasa.shape}")

max_c = nasa.groupby("engine_id")["cycle"].max().reset_index()
max_c.columns = ["engine_id","max_cycle"]
nasa = nasa.merge(max_c, on="engine_id")
nasa["RUL"] = (nasa["max_cycle"] - nasa["cycle"]).clip(upper=125)

drop_cols = ["engine_id","cycle","op3","s1","s5","s10","s16","s18","s19","max_cycle"]
nasa = nasa.drop(columns=drop_cols)

X_r = nasa.drop("RUL", axis=1)
y_r = nasa["RUL"]

scaler = MinMaxScaler()
X_r_scaled = scaler.fit_transform(X_r)

X_tr3, X_te3, y_tr3, y_te3 = train_test_split(X_r_scaled, y_r, test_size=0.2, random_state=42)

rul_model = GradientBoostingRegressor(
    n_estimators=200, max_depth=5, learning_rate=0.1,
    subsample=0.8, random_state=42
)
rul_model.fit(X_tr3, y_tr3)
r2_r  = r2_score(y_te3, rul_model.predict(X_te3))
mae_r = mean_absolute_error(y_te3, rul_model.predict(X_te3))
print(f"RUL Model  R²: {r2_r:.4f}  MAE: {mae_r:.2f} cycles")

joblib.dump(rul_model, os.path.join(OUT, "rul_model.pkl"))
joblib.dump(scaler,    os.path.join(OUT, "rul_scaler.pkl"))
print("Saved rul_model.pkl + rul_scaler.pkl")


# ─────────────────────────────────────────────────────────────────────────────
# 4. ROOT CAUSE MODEL  (ai4i2020 failure modes)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("4. ROOT CAUSE MODEL")
print("="*60)

rc = pd.read_csv(AI4I_CSV).drop(columns=["UDI","Product ID"])
rc["Type"] = LabelEncoder().fit_transform(rc["Type"])

# Only rows with at least one failure mode
failure_modes = ["TWF","HDF","PWF","OSF","RNF"]
rc_fail = rc[rc[failure_modes].sum(axis=1) > 0].copy()

def get_root_cause(row):
    for m in failure_modes:
        if row[m] == 1:
            return m
    return "Unknown"

rc_fail["root_cause"] = rc_fail.apply(get_root_cause, axis=1)
le_rc = LabelEncoder()
rc_fail["root_cause_enc"] = le_rc.fit_transform(rc_fail["root_cause"])

# Augment with synthetic rows to get enough samples
np.random.seed(42)
n_aug = 5000
aug = rc_fail.sample(n=n_aug, replace=True, random_state=42).copy()
aug[feat_cols] += np.random.normal(0, 0.5, aug[feat_cols].shape)
rc_all = pd.concat([rc_fail, aug], ignore_index=True)

X_rc = rc_all[feat_cols]
y_rc = rc_all["root_cause_enc"]

X_tr4, X_te4, y_tr4, y_te4 = train_test_split(X_rc, y_rc, test_size=0.2, random_state=42, stratify=y_rc)

rc_model = RandomForestClassifier(
    n_estimators=200, max_depth=10, class_weight="balanced",
    random_state=42, n_jobs=-1
)
rc_model.fit(X_tr4, y_tr4)
acc_rc = accuracy_score(y_te4, rc_model.predict(X_te4))
print(f"Root Cause Accuracy: {acc_rc*100:.2f}%")

joblib.dump(rc_model, os.path.join(OUT, "root_cause_model.pkl"))
joblib.dump(le_rc,    os.path.join(OUT, "root_cause_encoder.pkl"))
print("Saved root_cause_model.pkl")


# ─────────────────────────────────────────────────────────────────────────────
# 5. FLEET OPTIMIZER  (vehicle_maintenance_data — priority classification)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("5. FLEET OPTIMIZER MODEL")
print("="*60)

vm3 = pd.read_csv(VEHICLE_CSV)
vm3["tire_enc"]  = vm3["Tire_Condition"].map(cond_map).fillna(1)
vm3["brake_enc"] = vm3["Brake_Condition"].map(cond_map).fillna(1)
vm3["bat_enc"]   = vm3["Battery_Status"].map(bat_map).fillna(1)

vm3["health_score"]        = (100 - vm3["tire_enc"]*10 - vm3["brake_enc"]*10 - vm3["bat_enc"]*15 - (vm3["Reported_Issues"]*5).clip(0,20)).clip(5,100)
vm3["failure_probability"] = (vm3["tire_enc"]*15 + vm3["brake_enc"]*15 + vm3["bat_enc"]*20 + vm3["Reported_Issues"]*5).clip(0,100)
vm3["rul_days"]            = ((vm3["health_score"] / 100) * 30).round().clip(1, 30)
vm3["repair_cost"]         = 5000 + vm3["Reported_Issues"] * 2000 + vm3["Accident_History"] * 3000
vm3["failure_cost"]        = vm3["repair_cost"] * 3
vm3["potential_savings"]   = vm3["failure_cost"] - vm3["repair_cost"]

def assign_priority(row):
    score = row["failure_probability"] + (100 - row["health_score"])
    if score >= 140: return "Critical"
    if score >= 100: return "High"
    if score >= 60:  return "Medium"
    return "Low"

vm3["priority"] = vm3.apply(assign_priority, axis=1)
print("Priority distribution:\n", vm3["priority"].value_counts())

fleet_feats = ["health_score","failure_probability","rul_days","repair_cost","failure_cost","potential_savings"]
X_fl = vm3[fleet_feats]
le_fl = LabelEncoder()
y_fl = le_fl.fit_transform(vm3["priority"])

X_tr5, X_te5, y_tr5, y_te5 = train_test_split(X_fl, y_fl, test_size=0.2, random_state=42, stratify=y_fl)

fleet_model = GradientBoostingClassifier(
    n_estimators=200, max_depth=5, learning_rate=0.1,
    subsample=0.8, random_state=42
)
fleet_model.fit(X_tr5, y_tr5)
acc_fl = accuracy_score(y_te5, fleet_model.predict(X_te5))
print(f"Fleet Optimizer Accuracy: {acc_fl*100:.2f}%")

joblib.dump(fleet_model, os.path.join(OUT, "fleet_optimizer.pkl"))
joblib.dump(le_fl,       os.path.join(OUT, "fleet_priority_encoder.pkl"))
print("Saved fleet_optimizer.pkl")


# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ALL MODELS TRAINED AND SAVED")
print("="*60)
print(f"  Failure Model Accuracy : {acc*100:.2f}%")
print(f"  Health Model R²        : {r2:.4f}")
print(f"  RUL Model R²           : {r2_r:.4f}")
print(f"  Root Cause Accuracy    : {acc_rc*100:.2f}%")
print(f"  Fleet Optimizer Acc    : {acc_fl*100:.2f}%")
print("\nRestart backend: uvicorn main:app --reload")
