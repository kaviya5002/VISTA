"""
AutoML — Health Score Prediction
Run from: backend/ml/
    python automl/train_health_automl.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from sklearn.preprocessing import LabelEncoder
from base_trainer import AutoMLTrainer

df = pd.read_csv("D:/innovent/ai4i2020.csv")
df = df.drop(columns=["UDI", "Product ID"])
df["Type"] = LabelEncoder().fit_transform(df["Type"])

df["health_score"] = 100
for col in ["HDF", "PWF", "TWF", "OSF", "RNF"]:
    df.loc[df[col] == 1, "health_score"] -= 20
df["health_score"] -= (df["Tool wear [min]"] / 250) * 10
df["health_score"] -= ((df["Torque [Nm]"] - 40) / 40).clip(0, 1) * 5
df["health_score"] -= ((df["Process temperature [K]"] - 310) / 10).clip(0, 1) * 5
df["health_score"] = df["health_score"].clip(5, 100).round(2)

FEATURES = [
    "Type",
    "Air temperature [K]", "Process temperature [K]",
    "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]",
    "TWF", "HDF", "PWF", "OSF", "RNF",
]

AutoMLTrainer(
    X            = df[FEATURES],
    y            = df["health_score"],
    model_name   = "health",
    task         = "regression",
    feature_names= FEATURES,
    dataset_name = "AI4I 2020",
).run()
