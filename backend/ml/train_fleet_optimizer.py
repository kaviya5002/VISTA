import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# ── Step 1: Load Dataset ──────────────────────────────────────────────────────
df = pd.read_csv("fleet_training_dataset.csv")
print("Shape:", df.shape)
print("\nFirst 5 rows:")
print(df.head())
print("\nPriority Distribution:")
print(df["priority"].value_counts())

# ── Step 2: Features & Target ─────────────────────────────────────────────────
X = df[[
    "health_score",
    "failure_probability",
    "rul_days",
    "repair_cost",
    "failure_cost",
    "potential_savings"
]]

encoder = LabelEncoder()
y = encoder.fit_transform(df["priority"])
print("\nEncoded Classes:", list(encoder.classes_))

# ── Step 3: Train-Test Split ──────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ── Step 4: Train Model ───────────────────────────────────────────────────────
model = RandomForestClassifier(
    n_estimators=400,
    max_depth=15,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1
)

model.fit(X_train, y_train)
print("\nModel trained.")

# ── Step 5: Evaluate ──────────────────────────────────────────────────────────
pred = model.predict(X_test)

accuracy = accuracy_score(y_test, pred)
print(f"\nAccuracy: {accuracy * 100:.2f}%")

print("\nClassification Report:")
print(classification_report(y_test, pred, target_names=encoder.classes_))

print("Confusion Matrix:")
print(confusion_matrix(y_test, pred))

# ── Step 6: Feature Importance ────────────────────────────────────────────────
importance = pd.Series(
    model.feature_importances_,
    index=X.columns
).sort_values(ascending=False)

print("\nFeature Importance:")
print(importance)

# ── Step 7: Save Model & Encoder ─────────────────────────────────────────────
joblib.dump(model,   "fleet_optimizer.pkl")
joblib.dump(encoder, "fleet_priority_encoder.pkl")
print("\nFleet Optimizer Model saved as fleet_optimizer.pkl")
print("Encoder saved as fleet_priority_encoder.pkl")
print("Done.")
