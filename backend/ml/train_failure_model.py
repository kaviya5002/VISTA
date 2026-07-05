import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# ── Step 1: Load Dataset ──────────────────────────────────────────────────────
df = pd.read_csv("D:/innovent/ai4i2020.csv")
print("Dataset Shape:", df.shape)
print(df.head())

# ── Step 2: Remove Useless Columns ───────────────────────────────────────────
df = df.drop(columns=["UDI", "Product ID"])

# ── Step 3: Encode Categorical Column ────────────────────────────────────────
le = LabelEncoder()
df["Type"] = le.fit_transform(df["Type"])

# ── Step 4: Features & Target ─────────────────────────────────────────────────
X = df.drop("Machine failure", axis=1)
y = df["Machine failure"]

print("\nClass Distribution:")
print(y.value_counts())
print(f"Failure Rate: {y.mean() * 100:.2f}%")

# ── Step 5: Train-Test Split ──────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y          # preserves imbalance ratio in both splits
)

# ── Step 6: Train Random Forest ───────────────────────────────────────────────
# class_weight="balanced" handles the imbalance — prevents model from
# predicting "No Failure" for everything just to get 97% accuracy
model = RandomForestClassifier(
    n_estimators=300,
    max_depth=15,
    class_weight="balanced",   # key fix for imbalanced dataset
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)
print("\nModel trained successfully.")

# ── Step 7: Accuracy ──────────────────────────────────────────────────────────
pred = model.predict(X_test)
accuracy = accuracy_score(y_test, pred)
print(f"\nAccuracy: {accuracy * 100:.2f}%")

# ── Step 8: Detailed Metrics ──────────────────────────────────────────────────
# Precision = of all predicted failures, how many were real
# Recall    = of all real failures, how many did we catch
# F1        = balance between precision and recall
print("\nClassification Report:")
print(classification_report(y_test, pred, target_names=["No Failure", "Failure"]))

# ── Step 9: Confusion Matrix ──────────────────────────────────────────────────
cm = confusion_matrix(y_test, pred)
print("\nConfusion Matrix:")
print(cm)

plt.figure(figsize=(6, 4))
sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    cmap="Reds",
    xticklabels=["No Failure", "Failure"],
    yticklabels=["No Failure", "Failure"]
)
plt.title("Confusion Matrix — Failure Prediction")
plt.ylabel("Actual")
plt.xlabel("Predicted")
plt.tight_layout()
plt.savefig("confusion_matrix.png")
print("\nConfusion matrix saved as confusion_matrix.png")

# ── Feature Importance ────────────────────────────────────────────────────────
importances = pd.Series(model.feature_importances_, index=X.columns)
importances = importances.sort_values(ascending=False)

print("\nTop Feature Importances:")
print(importances)

plt.figure(figsize=(8, 5))
importances.plot(kind="bar", color="orange")
plt.title("Feature Importance — What Drives Failures?")
plt.tight_layout()
plt.savefig("feature_importance.png")
print("Feature importance chart saved as feature_importance.png")

# ── Step 10: Save Model ───────────────────────────────────────────────────────
joblib.dump(model, "failure_model.pkl")
print("\nModel saved as failure_model.pkl")
print("Done.")
