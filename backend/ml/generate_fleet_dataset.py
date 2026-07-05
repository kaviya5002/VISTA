import pandas as pd
import numpy as np

np.random.seed(42)

rows = 20000
data = []

for _ in range(rows):
    health       = np.random.randint(0, 101)
    failure_prob = np.random.randint(0, 101)
    rul          = np.random.randint(1, 120)
    repair_cost  = np.random.randint(3000, 25000)
    failure_cost = repair_cost + np.random.randint(10000, 100000)
    savings      = failure_cost - repair_cost

    if health < 30 or failure_prob > 85 or rul < 7:
        priority = "Immediate"
    elif health < 50 or failure_prob > 60 or rul < 20:
        priority = "High"
    elif health < 70 or failure_prob > 35 or rul < 40:
        priority = "Medium"
    else:
        priority = "Low"

    data.append([health, failure_prob, rul, repair_cost, failure_cost, savings, priority])

df = pd.DataFrame(data, columns=[
    "health_score",
    "failure_probability",
    "rul_days",
    "repair_cost",
    "failure_cost",
    "potential_savings",
    "priority"
])

print("Shape:", df.shape)
print("\nFirst 5 rows:")
print(df.head())
print("\nPriority Distribution:")
print(df["priority"].value_counts())

df.to_csv("fleet_training_dataset.csv", index=False)
print("\nDataset saved as fleet_training_dataset.csv")
