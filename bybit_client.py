import requests
import pandas as pd
from config import *

class BybitClient:
    def __init__(self):
        self.api_key = BYBIT_API_KEY
        self.secret_key = BYBIT_API_SECRET
        self.base_url = "https://api.bybit.com"

    def get_klines(self, symbol="ETHUSDT", category="linear", interval="15", limit=200):
        """
        Fetch OHLCV data using Bybit v5 API.
        
        Args:
            symbol: Symbol name (e.g., "ETHUSDT" for linear, "ETHUSD" for inverse)
            category: Product type - "spot", "linear", "inverse"
            interval: Kline interval - 1,3,5,15,30,60,120,240,360,720,D,M,W
            limit: Number of candles to fetch (max 1000)
        """
        # Correct v5 endpoint
        endpoint = f"{self.base_url}/v5/market/kline"
        
        params = {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }

        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        result = response.json()

        if result.get("retCode", -1) != 0:
            raise Exception(f"Bybit API error: {result.get('retMsg')}")

        data = result.get("result", {}).get("list", [])

        if not data:
            return pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close', 'volume'])

        # Data format: [startTime, open, high, low, close, volume, turnover]
        df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])

        # Convert timestamp (already in milliseconds) to int
        df['time'] = df['time'].astype('int64')

        # Convert price and volume columns to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        # Select only needed columns
        df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
        
        # Sort by time ascending (API returns descending)
        df = df.sort_values('time').reset_index(drop=True)
        
        return df

if __name__ == "__main__":
    client = BybitClient()
    
    # Example 1: Linear perpetual (USDT)
    df_linear = client.get_klines(symbol="ETHUSDT", category="linear", interval="15", limit=100)
    print("Linear (ETHUSDT):")
    print(df_linear.head())
    
    # Example 2: Inverse perpetual
    df_inverse = client.get_klines(symbol="ETHUSD", category="inverse", interval="15", limit=100)
    print("\nInverse (ETHUSD):")
    print(df_inverse.head())