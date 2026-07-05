import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler

# ── Step 1: Load Dataset ──────────────────────────────────────────────────────
columns = [
    "engine_id", "cycle",
    "op1", "op2", "op3",
    "s1","s2","s3","s4","s5","s6","s7","s8","s9",
    "s10","s11","s12","s13","s14","s15","s16","s17","s18","s19","s20","s21"
]

df = pd.read_csv(
    r"C:\Users\kaviy\OneDrive\Desktop\archive (6)\train_FD001.txt",
    sep=r"\s+",
    header=None,
    names=columns
)

print("Shape:", df.shape)
print(df.head())

# ── Step 2: Calculate RUL for each row ───────────────────────────────────────
# RUL = max cycle for that engine - current cycle
max_cycles = df.groupby("engine_id")["cycle"].max().reset_index()
max_cycles.columns = ["engine_id", "max_cycle"]
df = df.merge(max_cycles, on="engine_id")
df["RUL"] = df["max_cycle"] - df["cycle"]
df = df.drop(columns=["max_cycle"])

# Cap RUL at 125 — beyond that, engine is healthy enough, no need to predict precisely
df["RUL"] = df["RUL"].clip(upper=125)

print("\nRUL Distribution:")
print(df["RUL"].describe())

# ── Step 3: Drop constant sensors (no info) ───────────────────────────────────
drop_cols = ["engine_id", "cycle", "op3", "s1", "s5", "s10", "s16", "s18", "s19"]
df = df.drop(columns=drop_cols)

# ── Step 4: Features & Target ─────────────────────────────────────────────────
X = df.drop("RUL", axis=1)
y = df["RUL"]

# ── Step 5: Scale Features ────────────────────────────────────────────────────
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# ── Step 6: Train-Test Split ──────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42
)

# ── Step 7: Train Model ───────────────────────────────────────────────────────
model = RandomForestRegressor(
    n_estimators=200,
    max_depth=15,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)
print("\nRUL Model trained.")

# ── Step 8: Evaluate ──────────────────────────────────────────────────────────
pred = model.predict(X_test)
mae  = mean_absolute_error(y_test, pred)
rmse = np.sqrt(mean_squared_error(y_test, pred))
r2   = r2_score(y_test, pred)

print(f"\nMAE  : {mae:.2f} cycles")
print(f"RMSE : {rmse:.2f} cycles")
print(f"R²   : {r2:.4f}")

# ── Step 9: Plot Actual vs Predicted ─────────────────────────────────────────
plt.figure(figsize=(8, 5))
plt.scatter(y_test[:500], pred[:500], alpha=0.4, color="orange")
plt.plot([0, 125], [0, 125], "r--", label="Perfect prediction")
plt.xlabel("Actual RUL")
plt.ylabel("Predicted RUL")
plt.title("NASA CMAPSS — RUL Prediction")
plt.legend()
plt.tight_layout()
plt.savefig("rul_prediction.png")
print("Plot saved as rul_prediction.png")

# ── Step 10: Save Model & Scaler ─────────────────────────────────────────────
joblib.dump(model, "rul_model.pkl")
joblib.dump(scaler, "rul_scaler.pkl")
print("Model saved as rul_model.pkl")
print("Scaler saved as rul_scaler.pkl")
print("\nDone.")
