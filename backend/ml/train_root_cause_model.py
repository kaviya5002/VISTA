import pandas as pd
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# ── Step 1: Load Dataset ──────────────────────────────────────────────────────
df = pd.read_csv("D:/innovent/ai4i2020.csv")
print("Shape:", df.shape)

# ── Step 2: Drop useless columns ─────────────────────────────────────────────
df = df.drop(columns=["UDI", "Product ID"])

# ── Step 3: Encode Type ───────────────────────────────────────────────────────
le = LabelEncoder()
df["Type"] = le.fit_transform(df["Type"])

# ── Step 4: Create Root Cause Label ──────────────────────────────────────────
def root_cause(row):
    if row["TWF"] == 1:
        return "Tool Wear"
    elif row["HDF"] == 1:
        return "Heat Dissipation"
    elif row["PWF"] == 1:
        return "Power Failure"
    elif row["OSF"] == 1:
        return "Overstrain"
    elif row["RNF"] == 1:
        return "Random Failure"
    return "No Failure"

df["root_cause"] = df.apply(root_cause, axis=1)

print("\nRoot Cause Distribution:")
print(df["root_cause"].value_counts())

# ── Step 5: Features & Target ─────────────────────────────────────────────────
X = df[[
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]"
]]
y = df["root_cause"]

# ── Step 6: Train-Test Split ──────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ── Step 7: Train Random Forest ───────────────────────────────────────────────
# class_weight="balanced" handles the heavy imbalance (most rows = "No Failure")
model = RandomForestClassifier(
    n_estimators=300,
    max_depth=20,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)
print("\nModel trained.")

# ── Step 8: Evaluate ──────────────────────────────────────────────────────────
pred = model.predict(X_test)

accuracy = accuracy_score(y_test, pred)
print(f"\nAccuracy: {accuracy * 100:.2f}%")

print("\nClassification Report:")
print(classification_report(y_test, pred))

# ── Step 9: Confusion Matrix ──────────────────────────────────────────────────
cm = confusion_matrix(y_test, pred, labels=model.classes_)
plt.figure(figsize=(8, 6))
sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    cmap="Blues",
    xticklabels=model.classes_,
    yticklabels=model.classes_
)
plt.title("Root Cause Classification — Confusion Matrix")
plt.ylabel("Actual")
plt.xlabel("Predicted")
plt.tight_layout()
plt.savefig("root_cause_confusion_matrix.png")
print("\nSaved root_cause_confusion_matrix.png")

# ── Step 10: Feature Importance ───────────────────────────────────────────────
importances = pd.Series(model.feature_importances_, index=X.columns)
importances = importances.sort_values(ascending=False)
print("\nFeature Importances:")
print(importances)

# ── Step 11: Save Model ───────────────────────────────────────────────────────
joblib.dump(model, "root_cause_model.pkl")
print("\nModel saved as root_cause_model.pkl")
print("Done.")
