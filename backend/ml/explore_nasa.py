import pandas as pd

df = pd.read_csv(
    r"C:\Users\kaviy\OneDrive\Desktop\archive (6)\train_FD001.txt",
    sep=r"\s+",
    header=None
)

print("Shape:", df.shape)
print("\nFirst 5 rows:")
print(df.head())

print("\nColumn count:", len(df.columns))
print("\nData types:")
print(df.dtypes)
