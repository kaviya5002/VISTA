"""
Retrain RUL model with current sklearn version using synthetic NASA-style data.
Produces rul_model.pkl compatible with the existing rul_scaler.pkl feature space.
"""
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, r2_score

FEATURES = ["op1","op2","s2","s3","s4","s6","s7","s8","s9",
            "s11","s12","s13","s14","s15","s17","s20","s21"]

np.random.seed(42)
N = 15000

# Simulate degradation: RUL 0-125 cycles
rul = np.random.uniform(0, 125, N)

# Sensor values degrade as RUL decreases (health worsens)
health = rul / 125.0  # 0=failing, 1=healthy

op1  = np.random.normal(0, 0.002, N)
op2  = np.random.normal(0, 0.002, N)
s2   = 645  + (1 - health) * 5  + np.random.normal(0, 1, N)
s3   = 1590 + (1 - health) * 15 + np.random.normal(0, 2, N)
s4   = 1410 + (1 - health) * 10 + np.random.normal(0, 2, N)
s6   = 21.6 + (1 - health) * 1.5 + np.random.normal(0, 0.1, N)
s7   = 554  + (1 - health) * 8  + np.random.normal(0, 1, N)
s8   = 2388 + (1 - health) * 3  + np.random.normal(0, 0.5, N)
s9   = 9050 + (1 - health) * 200 + np.random.normal(0, 20, N)
s11  = 47.5 + (1 - health) * 3  + np.random.normal(0, 0.3, N)
s12  = 522  + (1 - health) * 3  + np.random.normal(0, 0.5, N)
s13  = 2388 + (1 - health) * 2  + np.random.normal(0, 0.3, N)
s14  = 8150 + (1 - health) * 100 + np.random.normal(0, 10, N)
s15  = 8.4  + (1 - health) * 0.3 + np.random.normal(0, 0.05, N)
s17  = 393  + (1 - health) * 5  + np.random.normal(0, 1, N)
s20  = 38   - (1 - health) * 3  + np.random.normal(0, 0.3, N)
s21  = 23.2 + (1 - health) * 1  + np.random.normal(0, 0.2, N)

X = pd.DataFrame({
    "op1": op1, "op2": op2, "s2": s2, "s3": s3, "s4": s4,
    "s6": s6, "s7": s7, "s8": s8, "s9": s9, "s11": s11,
    "s12": s12, "s13": s13, "s14": s14, "s15": s15,
    "s17": s17, "s20": s20, "s21": s21
})
y = rul

# Fit a fresh scaler on this data
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)

pred = model.predict(X_test)
print(f"MAE : {mean_absolute_error(y_test, pred):.2f}")
print(f"R2  : {r2_score(y_test, pred):.4f}")

joblib.dump(model,  "rul_model.pkl")
joblib.dump(scaler, "rul_scaler.pkl")
print("Saved rul_model.pkl and rul_scaler.pkl")
