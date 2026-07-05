"""
AutoML — Fleet Priority Optimizer
Run from: backend/ml/
    python automl/train_fleet_automl.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import joblib
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from base_trainer import AutoMLTrainer

df = pd.read_csv("fleet_training_dataset.csv")

FEATURES = [
    "health_score", "failure_probability", "rul_days",
    "repair_cost", "failure_cost", "potential_savings",
]

encoder = LabelEncoder()
y = encoder.fit_transform(df["priority"])

# Encoder must be available before the service loads the model
os.makedirs(os.path.join("models", "fleet"), exist_ok=True)
enc_path = os.path.join("models", "fleet", "encoder.pkl")
joblib.dump(encoder, enc_path)
print(f"Encoder saved → {enc_path}  classes: {list(encoder.classes_)}")

AutoMLTrainer(
    X            = df[FEATURES],
    y            = y,
    model_name   = "fleet",
    task         = "classification",
    feature_names= FEATURES,
    dataset_name = "Fleet Synthetic",
).run()
