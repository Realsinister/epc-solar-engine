import pandas as pd

df = pd.read_excel('cec_modules.xlsx', header=16)
print("Available columns:")
for col in df.columns:
    print(col)

print("\nSample Row 1:")
print(df.iloc[1])
