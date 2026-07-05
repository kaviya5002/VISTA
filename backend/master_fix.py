"""
MASTER FIX SCRIPT
- Retrains all 5 ML models using real CSV data (fast inference models)
- Seeds fleet.db from vehicle_maintenance_data.csv (real vehicle data)
Run from: d:\\innovent\\backend
"""
import os, sys, warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import joblib
import sqlite3

from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, r2_score, mean_absolute_error

# ── Paths ─────────────────────────────────────────────────────────────────────
VEHICLE_CSV = r"C:\Users\kaviy\OneDrive\Desktop\vehicle_maintenance_data.csv"
AI4I_CSV    = r"C:\Users\kaviy\OneDrive\Desktop\ai4i2020.csv"
NASA_DIR    = r"C:\Users\kaviy\OneDrive\Desktop\archive (6)"
ML_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml")
DB_PATH     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "fleet.db")

cond_map = {"New": 0, "Good": 1, "Worn Out": 2}
bat_map  = {"Good": 0, "Weak": 1, "Dead": 2}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — SEED DATABASE FROM REAL CSV
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 1: SEEDING DATABASE FROM vehicle_maintenance_data.csv")
print("="*60)

vm = pd.read_csv(VEHICLE_CSV)
vm["tire_enc"]  = vm["Tire_Condition"].map(cond_map).fillna(1)
vm["brake_enc"] = vm["Brake_Condition"].map(cond_map).fillna(1)
vm["bat_enc"]   = vm["Battery_Status"].map(bat_map).fillna(1)

# Map CSV columns → vehicle sensor columns used by backend
# battery_voltage: Good=13.5, Weak=11.5, Dead=9.5
vm["battery_voltage"] = vm["bat_enc"].map({0: 13.5, 1: 11.5, 2: 9.5})
vm["battery_voltage"] += np.random.uniform(-0.3, 0.3, len(vm))
vm["battery_voltage"] = vm["battery_voltage"].round(2).clip(9.0, 14.0)

# temperature: from tire/brake condition + mileage
vm["temperature"] = (
    30
    + vm["tire_enc"] * 15
    + vm["brake_enc"] * 15
    + (vm["Mileage"] / vm["Mileage"].max()) * 40
    + np.random.uniform(-5, 5, len(vm))
).round(1).clip(20, 120)

# rpm: from engine size + reported issues
vm["rpm"] = (
    1500
    + (vm["Engine_Size"] / vm["Engine_Size"].max()) * 3000
    + vm["Reported_Issues"] * 300
    + np.random.randint(-200, 200, len(vm))
).clip(500, 7000).astype(int)

# speed: from mileage + fuel efficiency
vm["speed"] = (
    30
    + (vm["Fuel_Efficiency"] / vm["Fuel_Efficiency"].max()) * 60
    + np.random.randint(-10, 10, len(vm))
).clip(0, 120).astype(int)

# Use first 100 rows as fleet vehicles
fleet_df = vm[["battery_voltage", "temperature", "rpm", "speed"]].head(100).reset_index(drop=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id INTEGER PRIMARY KEY,
    battery_voltage REAL,
    temperature REAL,
    rpm INTEGER,
    speed INTEGER
)
""")
for i, row in fleet_df.iterrows():
    cursor.execute(
        "INSERT OR REPLACE INTO vehicles VALUES (?, ?, ?, ?, ?)",
        (i + 1, row["battery_voltage"], row["temperature"], int(row["rpm"]), int(row["speed"]))
    )
conn.commit()
conn.close()
print(f"Seeded {len(fleet_df)} vehicles into fleet.db from real CSV data")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — FAILURE MODEL (vehicle_maintenance_data — 50k rows, rich features)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 2: FAILURE MODEL")
print("="*60)

vm2 = pd.read_csv(VEHICLE_CSV)
vm2["tire_enc"]  = vm2["Tire_Condition"].map(cond_map).fillna(1)
vm2["brake_enc"] = vm2["Brake_Condition"].map(cond_map).fillna(1)
vm2["bat_enc"]   = vm2["Battery_Status"].map(bat_map).fillna(1)

# Map to ai4i feature space (what failure_model_service.py expects)
ai4i_f = pd.read_csv(AI4I_CSV).drop(columns=["UDI","Product ID"])
ai4i_f["Type"] = LabelEncoder().fit_transform(ai4i_f["Type"])

vm2_feat = pd.DataFrame({
    "Type":                       (vm2["bat_enc"] + vm2["brake_enc"]) // 2,
    "Air temperature [K]":        295 + (vm2["Mileage"] / vm2["Mileage"].max()) * 15,
    "Process temperature [K]":    305 + (vm2["Mileage"] / vm2["Mileage"].max()) * 10,
    "Rotational speed [rpm]":     1200 + (vm2["Engine_Size"] / vm2["Engine_Size"].max()) * 1500,
    "Torque [Nm]":                20 + vm2["tire_enc"] * 10 + vm2["brake_enc"] * 10,
    "Tool wear [min]":            (vm2["Odometer_Reading"] / vm2["Odometer_Reading"].max() * 200).round(),
    "TWF":                        (vm2["tire_enc"] == 2).astype(int),
    "HDF":                        (vm2["brake_enc"] == 2).astype(int),
    "PWF":                        (vm2["bat_enc"] >= 1).astype(int),
    "OSF":                        vm2["Reported_Issues"].clip(0, 1),
    "RNF":                        0,
    "Machine failure":            vm2["Need_Maintenance"],
})

feat_cols = ["Type","Air temperature [K]","Process temperature [K]",
             "Rotational speed [rpm]","Torque [Nm]","Tool wear [min]",
             "TWF","HDF","PWF","OSF","RNF"]

combined_f = pd.concat([ai4i_f[feat_cols + ["Machine failure"]], vm2_feat], ignore_index=True)
X_f = combined_f[feat_cols]
y_f = combined_f["Machine failure"]

X_tr, X_te, y_tr, y_te = train_test_split(X_f, y_f, test_size=0.2, random_state=42, stratify=y_f)

failure_model = GradientBoostingClassifier(
    n_estimators=150, max_depth=5, learning_rate=0.15,
    subsample=0.8, random_state=42
)
failure_model.fit(X_tr, y_tr)
acc_f = accuracy_score(y_te, failure_model.predict(X_te))
print(f"Failure Model Accuracy: {acc_f*100:.2f}%")
joblib.dump(failure_model, os.path.join(ML_DIR, "failure_model.pkl"))
print("Saved failure_model.pkl")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — HEALTH MODEL
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 3: HEALTH MODEL")
print("="*60)

ai4i_h = pd.read_csv(AI4I_CSV).drop(columns=["UDI","Product ID"])
ai4i_h["Type"] = LabelEncoder().fit_transform(ai4i_h["Type"])
ai4i_h["health_score"] = 100
for col, penalty in [("HDF",20),("PWF",20),("TWF",20),("OSF",20),("RNF",20)]:
    ai4i_h.loc[ai4i_h[col]==1, "health_score"] -= penalty
ai4i_h["health_score"] -= (ai4i_h["Tool wear [min]"] / 250) * 10
ai4i_h["health_score"] -= ((ai4i_h["Torque [Nm]"] - 40) / 40).clip(0,1) * 5
ai4i_h["health_score"] -= ((ai4i_h["Process temperature [K]"] - 310) / 10).clip(0,1) * 5
ai4i_h["health_score"] = ai4i_h["health_score"].clip(5, 100).round(2)

vm3 = pd.read_csv(VEHICLE_CSV)
vm3["tire_enc"]  = vm3["Tire_Condition"].map(cond_map).fillna(1)
vm3["brake_enc"] = vm3["Brake_Condition"].map(cond_map).fillna(1)
vm3["bat_enc"]   = vm3["Battery_Status"].map(bat_map).fillna(1)
vm3["health_score"] = (
    100 - vm3["tire_enc"]*10 - vm3["brake_enc"]*10 - vm3["bat_enc"]*15
    - (vm3["Reported_Issues"]*5).clip(0,20) - (vm3["Accident_History"]*5).clip(0,15)
).clip(5, 100)

vm3_feat = pd.DataFrame({
    "Type":                       (vm3["bat_enc"] + vm3["brake_enc"]) // 2,
    "Air temperature [K]":        295 + (vm3["Mileage"] / vm3["Mileage"].max()) * 15,
    "Process temperature [K]":    305 + (vm3["Mileage"] / vm3["Mileage"].max()) * 10,
    "Rotational speed [rpm]":     1200 + (vm3["Engine_Size"] / vm3["Engine_Size"].max()) * 1500,
    "Torque [Nm]":                20 + vm3["tire_enc"] * 10 + vm3["brake_enc"] * 10,
    "Tool wear [min]":            (vm3["Odometer_Reading"] / vm3["Odometer_Reading"].max() * 200).round(),
    "TWF":                        (vm3["tire_enc"] == 2).astype(int),
    "HDF":                        (vm3["brake_enc"] == 2).astype(int),
    "PWF":                        (vm3["bat_enc"] >= 1).astype(int),
    "OSF":                        vm3["Reported_Issues"].clip(0,1),
    "RNF":                        0,
    "health_score":               vm3["health_score"],
})

combined_h = pd.concat([ai4i_h[feat_cols + ["health_score"]], vm3_feat], ignore_index=True)
X_h = combined_h[feat_cols]
y_h = combined_h["health_score"]

X_tr2, X_te2, y_tr2, y_te2 = train_test_split(X_h, y_h, test_size=0.2, random_state=42)

health_model = GradientBoostingRegressor(
    n_estimators=150, max_depth=5, learning_rate=0.15,
    subsample=0.8, random_state=42
)
health_model.fit(X_tr2, y_tr2)
r2_h  = r2_score(y_te2, health_model.predict(X_te2))
mae_h = mean_absolute_error(y_te2, health_model.predict(X_te2))
print(f"Health Model R²: {r2_h:.4f}  MAE: {mae_h:.2f}")
joblib.dump(health_model, os.path.join(ML_DIR, "health_model.pkl"))
print("Saved health_model.pkl")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — RUL MODEL (NASA CMAPSS all 4 datasets)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 4: RUL MODEL (NASA CMAPSS)")
print("="*60)

nasa_cols = ["engine_id","cycle","op1","op2","op3",
             "s1","s2","s3","s4","s5","s6","s7","s8","s9","s10",
             "s11","s12","s13","s14","s15","s16","s17","s18","s19","s20","s21"]

frames = []
for f in ["train_FD001.txt","train_FD002.txt","train_FD003.txt","train_FD004.txt"]:
    p = os.path.join(NASA_DIR, f)
    if os.path.exists(p):
        frames.append(pd.read_csv(p, sep=r"\s+", header=None, names=nasa_cols))

nasa = pd.concat(frames, ignore_index=True)
max_c = nasa.groupby("engine_id")["cycle"].max().reset_index()
max_c.columns = ["engine_id","max_cycle"]
nasa = nasa.merge(max_c, on="engine_id")
nasa["RUL"] = (nasa["max_cycle"] - nasa["cycle"]).clip(upper=125)
nasa = nasa.drop(columns=["engine_id","cycle","op3","s1","s5","s10","s16","s18","s19","max_cycle"])

X_r = nasa.drop("RUL", axis=1)
y_r = nasa["RUL"]
scaler = MinMaxScaler()
X_r_sc = scaler.fit_transform(X_r)

X_tr3, X_te3, y_tr3, y_te3 = train_test_split(X_r_sc, y_r, test_size=0.2, random_state=42)

rul_model = GradientBoostingRegressor(
    n_estimators=150, max_depth=5, learning_rate=0.15,
    subsample=0.8, random_state=42
)
rul_model.fit(X_tr3, y_tr3)
r2_r  = r2_score(y_te3, rul_model.predict(X_te3))
mae_r = mean_absolute_error(y_te3, rul_model.predict(X_te3))
print(f"RUL Model R²: {r2_r:.4f}  MAE: {mae_r:.2f} cycles")
joblib.dump(rul_model, os.path.join(ML_DIR, "rul_model.pkl"))
joblib.dump(scaler,    os.path.join(ML_DIR, "rul_scaler.pkl"))
print("Saved rul_model.pkl + rul_scaler.pkl")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — ROOT CAUSE MODEL
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 5: ROOT CAUSE MODEL")
print("="*60)

rc = pd.read_csv(AI4I_CSV).drop(columns=["UDI","Product ID"])
rc["Type"] = LabelEncoder().fit_transform(rc["Type"])

def get_root_cause(row):
    if row["TWF"]==1: return "Tool Wear"
    if row["HDF"]==1: return "Heat Dissipation"
    if row["PWF"]==1: return "Power Failure"
    if row["OSF"]==1: return "Overstrain"
    if row["RNF"]==1: return "Random Failure"
    return "No Failure"

rc["root_cause"] = rc.apply(get_root_cause, axis=1)
rc_feat = ["Type","Air temperature [K]","Process temperature [K]",
           "Rotational speed [rpm]","Torque [Nm]","Tool wear [min]"]

X_rc = rc[rc_feat]
y_rc = rc["root_cause"]

X_tr4, X_te4, y_tr4, y_te4 = train_test_split(X_rc, y_rc, test_size=0.2, random_state=42, stratify=y_rc)

rc_model = RandomForestClassifier(
    n_estimators=100, max_depth=10, class_weight="balanced",
    random_state=42, n_jobs=-1
)
rc_model.fit(X_tr4, y_tr4)
acc_rc = accuracy_score(y_te4, rc_model.predict(X_te4))
print(f"Root Cause Accuracy: {acc_rc*100:.2f}%")
joblib.dump(rc_model, os.path.join(ML_DIR, "root_cause_model.pkl"))
print("Saved root_cause_model.pkl")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — FLEET OPTIMIZER (vehicle_maintenance_data — 50k rows)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 6: FLEET OPTIMIZER MODEL")
print("="*60)

vm4 = pd.read_csv(VEHICLE_CSV)
vm4["tire_enc"]  = vm4["Tire_Condition"].map(cond_map).fillna(1)
vm4["brake_enc"] = vm4["Brake_Condition"].map(cond_map).fillna(1)
vm4["bat_enc"]   = vm4["Battery_Status"].map(bat_map).fillna(1)

vm4["health_score"]        = (100 - vm4["tire_enc"]*10 - vm4["brake_enc"]*10 - vm4["bat_enc"]*15 - (vm4["Reported_Issues"]*5).clip(0,20)).clip(5,100)
vm4["failure_probability"] = (vm4["tire_enc"]*15 + vm4["brake_enc"]*15 + vm4["bat_enc"]*20 + vm4["Reported_Issues"]*5).clip(0,100)
vm4["rul_days"]            = ((vm4["health_score"] / 100) * 30).round().clip(1, 30)
vm4["repair_cost"]         = 5000 + vm4["Reported_Issues"] * 2000 + vm4["Accident_History"] * 3000
vm4["failure_cost"]        = vm4["repair_cost"] * 3
vm4["potential_savings"]   = vm4["failure_cost"] - vm4["repair_cost"]

def assign_priority(row):
    score = row["failure_probability"] + (100 - row["health_score"])
    if score >= 140: return "Immediate"
    if score >= 100: return "High"
    if score >= 60:  return "Medium"
    return "Low"

vm4["priority"] = vm4.apply(assign_priority, axis=1)

fl_feats = ["health_score","failure_probability","rul_days","repair_cost","failure_cost","potential_savings"]
X_fl = vm4[fl_feats]
le_fl = LabelEncoder()
y_fl = le_fl.fit_transform(vm4["priority"])

X_tr5, X_te5, y_tr5, y_te5 = train_test_split(X_fl, y_fl, test_size=0.2, random_state=42, stratify=y_fl)

fleet_model = GradientBoostingClassifier(
    n_estimators=150, max_depth=5, learning_rate=0.15,
    subsample=0.8, random_state=42
)
fleet_model.fit(X_tr5, y_tr5)
acc_fl = accuracy_score(y_te5, fleet_model.predict(X_te5))
print(f"Fleet Optimizer Accuracy: {acc_fl*100:.2f}%")
joblib.dump(fleet_model, os.path.join(ML_DIR, "fleet_optimizer.pkl"))
joblib.dump(le_fl,       os.path.join(ML_DIR, "fleet_priority_encoder.pkl"))
print("Saved fleet_optimizer.pkl")


# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ALL DONE")
print("="*60)
print(f"  DB seeded with 100 real vehicles")
print(f"  Failure Model  : {acc_f*100:.2f}%")
print(f"  Health Model   : R²={r2_h:.4f}")
print(f"  RUL Model      : R²={r2_r:.4f}")
print(f"  Root Cause     : {acc_rc*100:.2f}%")
print(f"  Fleet Optimizer: {acc_fl*100:.2f}%")
print("\nNow run: uvicorn main:app --reload")
