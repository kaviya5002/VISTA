"""
AutoML — Root Cause Classification
Run from: backend/ml/
    python automl/train_rootcause_automl.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from sklearn.preprocessing import LabelEncoder
from base_trainer import AutoMLTrainer

df = pd.read_csv("D:/innovent/ai4i2020.csv")
df = df.drop(columns=["UDI", "Product ID"])
df["Type"] = LabelEncoder().fit_transform(df["Type"])

def _label(row):
    if row["TWF"] == 1: return "Tool Wear"
    if row["HDF"] == 1: return "Heat Dissipation"
    if row["PWF"] == 1: return "Power Failure"
    if row["OSF"] == 1: return "Overstrain"
    if row["RNF"] == 1: return "Random Failure"
    return "No Failure"

df["root_cause"] = df.apply(_label, axis=1)

FEATURES = [
    "Type",
    "Air temperature [K]", "Process temperature [K]",
    "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]",
]

AutoMLTrainer(
    X            = df[FEATURES],
    y            = df["root_cause"],
    model_name   = "rootcause",
    task         = "classification",
    feature_names= FEATURES,
    dataset_name = "AI4I 2020",
).run()
