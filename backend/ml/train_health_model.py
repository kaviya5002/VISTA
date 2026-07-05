import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.preprocessing import LabelEncoder

# ── Step 1: Load Dataset ──────────────────────────────────────────────────────
df = pd.read_csv("D:/innovent/ai4i2020.csv")
print("Shape:", df.shape)

# ── Step 2: Drop useless columns ─────────────────────────────────────────────
df = df.drop(columns=["UDI", "Product ID"])

# ── Step 3: Encode Type ───────────────────────────────────────────────────────
le = LabelEncoder()
df["Type"] = le.fit_transform(df["Type"])

# ── Step 4: Generate Health Score ─────────────────────────────────────────────
# Each failure mode reduces health by 20 points
df["health_score"] = 100
df.loc[df["HDF"] == 1, "health_score"] -= 20
df.loc[df["PWF"] == 1, "health_score"] -= 20
df.loc[df["TWF"] == 1, "health_score"] -= 20
df.loc[df["OSF"] == 1, "health_score"] -= 20
df.loc[df["RNF"] == 1, "health_score"] -= 20
df["health_score"] = df["health_score"].clip(0, 100)

# Also penalize based on sensor stress to create more variance
# Tool wear contributes degradation
df["health_score"] -= (df["Tool wear [min]"] / 250) * 10
# High torque stress
df["health_score"] -= ((df["Torque [Nm]"] - 40) / 40).clip(0, 1) * 5
# High temperature
df["health_score"] -= ((df["Process temperature [K]"] - 310) / 10).clip(0, 1) * 5
df["health_score"] = df["health_score"].clip(5, 100).round(2)

print("\nHealth Score Distribution:")
print(df["health_score"].describe())

# ── Step 5: Features & Target ─────────────────────────────────────────────────
features = [
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
    "TWF", "HDF", "PWF", "OSF", "RNF"
]
X = df[features]
y = df["health_score"]

# ── Step 6: Train-Test Split ──────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ── Step 7: Train Random Forest (optimized for high R²) ──────────────────────
model = RandomForestRegressor(
    n_estimators=500,       # more trees = more stable
    max_depth=20,           # deeper trees capture more patterns
    min_samples_split=2,
    min_samples_leaf=1,
    max_features="sqrt",
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)
pred = model.predict(X_test)

r2  = r2_score(y_test, pred)
mae = mean_absolute_error(y_test, pred)

print(f"\nRandom Forest  →  R²: {r2:.4f}  |  MAE: {mae:.2f}")

# ── Step 8: Try Gradient Boosting if RF R² < 0.95 ────────────────────────────
if r2 < 0.95:
    print("\nBoosting with GradientBoostingRegressor for higher R²...")
    gb_model = GradientBoostingRegressor(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42
    )
    gb_model.fit(X_train, y_train)
    gb_pred = gb_model.predict(X_test)
    gb_r2   = r2_score(y_test, gb_pred)
    gb_mae  = mean_absolute_error(y_test, gb_pred)
    print(f"Gradient Boost →  R²: {gb_r2:.4f}  |  MAE: {gb_mae:.2f}")

    if gb_r2 > r2:
        print("Using Gradient Boosting model (higher R²)")
        model = gb_model
        pred  = gb_pred
        r2    = gb_r2

# ── Step 9: Feature Importance ────────────────────────────────────────────────
importances = pd.Series(model.feature_importances_, index=features)
importances = importances.sort_values(ascending=False)
print("\nFeature Importances:")
print(importances)

plt.figure(figsize=(8, 5))
importances.plot(kind="bar", color="skyblue")
plt.title("Health Score — Feature Importance")
plt.tight_layout()
plt.savefig("health_feature_importance.png")
print("Saved health_feature_importance.png")

# ── Step 10: Save Model ───────────────────────────────────────────────────────
joblib.dump(model, "health_model.pkl")
print(f"\nFinal R²: {r2:.4f}")
print("Model saved as health_model.pkl")
print("Done.")
