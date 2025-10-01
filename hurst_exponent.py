import pandas as pd
import numpy as np

# Load the CSV
file_path = r"C:\Users\vaibh\OneDrive\Desktop\alhem_2\trading_binance\Delta_Final.csv"
df = pd.read_csv(file_path)

# Ensure 'close' column is float
df['close'] = df['close'].astype(float)

# Function to calculate Hurst Exponent
def hurst_exponent(ts):
    lags = range(2, 100)
    tau = [np.std(ts[lag:] - ts[:-lag]) for lag in lags]
    hurst = np.polyfit(np.log(lags), np.log(tau), 1)[0]
    return hurst

# Calculate Hurst Exponent on the 'close' prices
hurst = hurst_exponent(df['close'].values)
print(f"Hurst Exponent: {hurst:.4f}")

# Interpretation (optional)
if hurst < 0.5:
    print("Mean reverting behavior (e.g., pairs trading).")
elif hurst == 0.5:
    print("Random walk (Brownian motion).")
else:
    print("Trending behavior (e.g., momentum strategy).")
