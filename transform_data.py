import pandas as pd
import numpy as np
from datetime import datetime

# Read the source file
def convert_to_complete_format(df):
    # df = pd.read_csv('Sample.csv')

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Calculate price changes and patterns
    df['price_change'] = df['close'].diff()
    df['price_change_pct'] = df['close'].pct_change()

    # Calculate RSI (Relative Strength Index)
    def calculate_rsi(data, periods=14):
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    df['RSI'] = calculate_rsi(df['close'])

    # Calculate signals based on price movements and RSI
    df['RF_BuySignal'] = ((df['price_change'] > 0) & (df['RSI'] < 30)).astype(int)
    df['RF_SellSignal'] = ((df['price_change'] < 0) & (df['RSI'] > 70)).astype(int)

    # RSI buy/sell signals
    df['rsi_buy'] = df['RSI'] < 30
    df['rsi_sell'] = df['RSI'] > 70

    # Calculate gaizy color based on price movement
    df['gaizy_color'] = np.where(df['close'] > df['open'], 'green', 'black')

    # Calculate Green and Red arrows based on significant price movements
    df['GreenArrow'] = (df['price_change_pct'] > 0.001) & (df['close'] > df['open'])
    df['RedArrow'] = (df['price_change_pct'] < -0.001) & (df['close'] < df['open'])

    # Calculate Signal_Final based on conditions
    def calculate_signal_final(row):
        # Buy conditions
        buy_conditions = [
            row['RF_BuySignal'] == 1,  # Random Forest Buy Signal
            row['rsi_buy'] == True,    # RSI indicates oversold
            row['GreenArrow'] == True, # Strong upward movement
            row['gaizy_color'] == 'green'  # Price closed higher than open
        ]
        
        # Sell conditions
        sell_conditions = [
            row['RF_SellSignal'] == 1,  # Random Forest Sell Signal
            row['rsi_sell'] == True,    # RSI indicates overbought
            row['RedArrow'] == True,    # Strong downward movement
            row['gaizy_color'] == 'black'  # Price closed lower than open
        ]
        
        # Calculate signal strength
        buy_strength = sum(buy_conditions)
        sell_strength = sum(sell_conditions)
        
        # Determine final signal
        if buy_strength >= 2:  # At least 2 buy conditions met
            return 1  # Buy signal
        elif sell_strength >= 2:  # At least 2 sell conditions met
            return -1  # Sell signal
        else:
            return 0  # No clear signal

    # Apply the signal calculation to each row
    df['Signal_Final'] = df.apply(calculate_signal_final, axis=1)

    # Rename columns to match Sample2.csv
    df = df.rename(columns={
        'timestamp': 'Timestamp',
        'Volume': 'volume',
        'close': 'close',
        'open': 'open',
        'high': 'high',
        'low': 'low'
    })

    # Add time column (Unix timestamp)
    df['time'] = df['Timestamp'].astype(np.int64) // 10**9

    # Reorder columns to match Sample2.csv
    columns_order = [
        'time', 'volume', 'Timestamp', 'close', 'open', 'high', 'low',
        'RF_BuySignal', 'RF_SellSignal', 'rsi_buy', 'rsi_sell',
        'gaizy_color', 'GreenArrow', 'RedArrow', 'Signal_Final'
    ]
    df = df[columns_order]

    # Save the transformed data
    # df.to_csv('Sample2.csv', index=False)
    # print("Transformation completed successfully!") 
    return df