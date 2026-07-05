import os, warnings
warnings.filterwarnings("ignore")
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, r2_score, mean_absolute_error

VEHICLE_CSV = r"C:\Users\kaviy\OneDrive\Desktop\vehicle_maintenance_data.csv"
AI4I_CSV    = r"C:\Users\kaviy\OneDrive\Desktop\ai4i2020.csv"
NASA_DIR    = r"C:\Users\kaviy\OneDrive\Desktop\archive (6)"
OUT         = os.path.dirname(os.path.abspath(__file__))

cond_map = {"New": 0, "Good": 1, "Worn Out": 2}
bat_map  = {"Good": 0, "Weak": 1, "Dead": 2}

def encode_vm(df):
    df = df.copy()
    df["tire"]       = df["Tire_Condition"].map(cond_map).fillna(1).astype(int)
    df["brake"]      = df["Brake_Condition"].map(cond_map).fillna(1).astype(int)
    df["bat"]        = df["Battery_Status"].map(bat_map).fillna(1).astype(int)
    df["fuel"]       = LabelEncoder().fit_transform(df["Fuel_Type"].fillna("Petrol"))
    df["trans"]      = LabelEncoder().fit_transform(df["Transmission_Type"].fillna("Manual"))
    df["owner"]      = LabelEncoder().fit_transform(df["Owner_Type"].fillna("First"))
    df["model_enc"]  = LabelEncoder().fit_transform(df["Vehicle_Model"].fillna("Car"))
    df["maint_hist"] = LabelEncoder().fit_transform(df["Maintenance_History"].fillna("None"))
    return df

FEATS = ["model_enc","Mileage","Vehicle_Age","Engine_Size","Odometer_Reading",
         "Reported_Issues","Service_History","Accident_History","Fuel_Efficiency",
         "Insurance_Premium","tire","brake","bat","fuel","trans","owner","maint_hist"]

# ── 1. FAILURE MODEL ─────────────────────────────────────────────────────────
print("\n=== 1. FAILURE MODEL ===")
vm = encode_vm(pd.read_csv(VEHICLE_CSV))
X_f = vm[FEATS]
y_f = vm["Need_Maintenance"]
X_tr, X_te, y_tr, y_te = train_test_split(X_f, y_f, test_size=0.2, random_state=42, stratify=y_f)
failure_model = RandomForestClassifier(
    n_estimators=300, max_depth=None, min_samples_leaf=1,
    random_state=42, n_jobs=-1
)
failure_model.fit(X_tr, y_tr)
acc_f = accuracy_score(y_te, failure_model.predict(X_te))
print(f"Failure Accuracy: {acc_f*100:.2f}%")
joblib.dump(failure_model, os.path.join(OUT, "failure_model_v2.pkl"))
joblib.dump(FEATS,         os.path.join(OUT, "failure_features.pkl"))
print("Saved failure_model_v2.pkl")

# ── 2. HEALTH MODEL ──────────────────────────────────────────────────────────
print("\n=== 2. HEALTH MODEL ===")
vm2 = encode_vm(pd.read_csv(VEHICLE_CSV))
vm2["health_score"] = (
    100
    - vm2["tire"] * 10
    - vm2["brake"] * 10
    - vm2["bat"] * 15
    - (vm2["Reported_Issues"] * 5).clip(0, 20)
    - (vm2["Accident_History"] * 5).clip(0, 15)
    - ((vm2["Odometer_Reading"] / vm2["Odometer_Reading"].max()) * 10)
).clip(5, 100).round(1)
X_h = vm2[FEATS]
y_h = vm2["health_score"]
X_tr2, X_te2, y_tr2, y_te2 = train_test_split(X_h, y_h, test_size=0.2, random_state=42)
health_model = RandomForestRegressor(
    n_estimators=300, max_depth=None, min_samples_leaf=1,
    random_state=42, n_jobs=-1
)
health_model.fit(X_tr2, y_tr2)
r2_h  = r2_score(y_te2, health_model.predict(X_te2))
mae_h = mean_absolute_error(y_te2, health_model.predict(X_te2))
print(f"Health R2: {r2_h:.4f}  MAE: {mae_h:.2f}")
joblib.dump(health_model, os.path.join(OUT, "health_model_v2.pkl"))
print("Saved health_model_v2.pkl")

# ── 3. RUL MODEL ─────────────────────────────────────────────────────────────
print("\n=== 3. RUL MODEL ===")
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
max_c.columns = ["engine_id", "max_cycle"]
nasa = nasa.merge(max_c, on="engine_id")
nasa["RUL"] = (nasa["max_cycle"] - nasa["cycle"]).clip(upper=125)
nasa = nasa.drop(columns=["engine_id","cycle","op3","s1","s5","s10","s16","s18","s19","max_cycle"])
X_r = nasa.drop("RUL", axis=1)
y_r = nasa["RUL"]
scaler = MinMaxScaler()
X_r_sc = scaler.fit_transform(X_r)
X_tr3, X_te3, y_tr3, y_te3 = train_test_split(X_r_sc, y_r, test_size=0.2, random_state=42)
rul_model = RandomForestRegressor(
    n_estimators=300, max_depth=None, min_samples_leaf=1,
    random_state=42, n_jobs=-1
)
rul_model.fit(X_tr3, y_tr3)
r2_r  = r2_score(y_te3, rul_model.predict(X_te3))
mae_r = mean_absolute_error(y_te3, rul_model.predict(X_te3))
print(f"RUL R2: {r2_r:.4f}  MAE: {mae_r:.2f} cycles")
joblib.dump(rul_model, os.path.join(OUT, "rul_model.pkl"))
joblib.dump(scaler,    os.path.join(OUT, "rul_scaler.pkl"))
print("Saved rul_model.pkl + rul_scaler.pkl")

# ── 4. ROOT CAUSE MODEL ───────────────────────────────────────────────────────
print("\n=== 4. ROOT CAUSE MODEL ===")
rc = pd.read_csv(AI4I_CSV).drop(columns=["UDI","Product ID"])
rc["Type"] = LabelEncoder().fit_transform(rc["Type"])
def get_rc(row):
    if row["TWF"]==1: return "Tool Wear"
    if row["HDF"]==1: return "Heat Dissipation"
    if row["PWF"]==1: return "Power Failure"
    if row["OSF"]==1: return "Overstrain"
    if row["RNF"]==1: return "Random Failure"
    return "No Failure"
rc["root_cause"] = rc.apply(get_rc, axis=1)
rc_feats = ["Type","Air temperature [K]","Process temperature [K]",
            "Rotational speed [rpm]","Torque [Nm]","Tool wear [min]"]
X_rc = rc[rc_feats]
y_rc = rc["root_cause"]
X_tr4, X_te4, y_tr4, y_te4 = train_test_split(X_rc, y_rc, test_size=0.2, random_state=42, stratify=y_rc)
rc_model = RandomForestClassifier(
    n_estimators=300, max_depth=None, min_samples_leaf=1,
    class_weight="balanced", random_state=42, n_jobs=-1
)
rc_model.fit(X_tr4, y_tr4)
acc_rc = accuracy_score(y_te4, rc_model.predict(X_te4))
print(f"Root Cause Accuracy: {acc_rc*100:.2f}%")
joblib.dump(rc_model, os.path.join(OUT, "root_cause_model.pkl"))
print("Saved root_cause_model.pkl")

# ── 5. FLEET OPTIMIZER ────────────────────────────────────────────────────────
print("\n=== 5. FLEET OPTIMIZER ===")
vm4 = encode_vm(pd.read_csv(VEHICLE_CSV))
vm4["health_score"]        = (100 - vm4["tire"]*10 - vm4["brake"]*10 - vm4["bat"]*15 - (vm4["Reported_Issues"]*5).clip(0,20)).clip(5,100)
vm4["failure_probability"] = (vm4["tire"]*15 + vm4["brake"]*15 + vm4["bat"]*20 + vm4["Reported_Issues"]*5).clip(0,100)
vm4["rul_days"]            = ((vm4["health_score"]/100)*30).round().clip(1,30)
vm4["repair_cost"]         = 5000 + vm4["Reported_Issues"]*2000 + vm4["Accident_History"]*3000
vm4["failure_cost"]        = vm4["repair_cost"] * 3
vm4["potential_savings"]   = vm4["failure_cost"] - vm4["repair_cost"]
def assign_priority(row):
    s = row["failure_probability"] + (100 - row["health_score"])
    if s >= 140: return "Immediate"
    if s >= 100: return "High"
    if s >= 60:  return "Medium"
    return "Low"
vm4["priority"] = vm4.apply(assign_priority, axis=1)
fl_feats = ["health_score","failure_probability","rul_days","repair_cost","failure_cost","potential_savings"]
X_fl = vm4[fl_feats]
le_fl = LabelEncoder()
y_fl = le_fl.fit_transform(vm4["priority"])
X_tr5, X_te5, y_tr5, y_te5 = train_test_split(X_fl, y_fl, test_size=0.2, random_state=42, stratify=y_fl)
fleet_model = RandomForestClassifier(
    n_estimators=300, max_depth=None, min_samples_leaf=1,
    random_state=42, n_jobs=-1
)
fleet_model.fit(X_tr5, y_tr5)
acc_fl = accuracy_score(y_te5, fleet_model.predict(X_te5))
print(f"Fleet Optimizer Accuracy: {acc_fl*100:.2f}%")
joblib.dump(fleet_model, os.path.join(OUT, "fleet_optimizer.pkl"))
joblib.dump(le_fl,       os.path.join(OUT, "fleet_priority_encoder.pkl"))
print("Saved fleet_optimizer.pkl")

print("\n" + "="*50)
print(f"  Failure   : {acc_f*100:.2f}%")
print(f"  Health    : R2={r2_h:.4f}  MAE={mae_h:.2f}")
print(f"  RUL       : R2={r2_r:.4f}  MAE={mae_r:.2f}")
print(f"  Root Cause: {acc_rc*100:.2f}%")
print(f"  Fleet     : {acc_fl*100:.2f}%")
print("="*50)
print("Now update services and restart: uvicorn main:app --reload")
