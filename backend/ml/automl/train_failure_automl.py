"""
AutoML — Failure Prediction
Run from: backend/ml/
    python automl/train_failure_automl.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from sklearn.preprocessing import LabelEncoder
from base_trainer import AutoMLTrainer

df = pd.read_csv("D:/innovent/ai4i2020.csv")
df = df.drop(columns=["UDI", "Product ID"])
df["Type"] = LabelEncoder().fit_transform(df["Type"])

FEATURES = [
    "Type",
    "Air temperature [K]", "Process temperature [K]",
    "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]",
    "TWF", "HDF", "PWF", "OSF", "RNF",
]

AutoMLTrainer(
    X            = df[FEATURES],
    y            = df["Machine failure"],
    model_name   = "failure",
    task         = "classification",
    feature_names= FEATURES,
    dataset_name = "AI4I 2020",
).run()
