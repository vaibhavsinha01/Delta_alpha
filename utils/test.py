import pandas as pd
df = pd.read_csv(r"C:\Users\vaibh\OneDrive\Desktop\alhem_2\trading_binance\Delta_Final.csv")
df = df[['time','close','RF_Filter','RF_BuySignal','RF_SellSignal','Signal_Final']]
print(df)

df.to_csv(f"rf_close_data.csv")