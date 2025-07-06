from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
from datetime import datetime
import time

class BinanceClient:
    def __init__(self, api_key=None, api_secret=None):
        self.client = Client(api_key, api_secret)
        
    def get_historical_klines(self, symbol, interval, start_time, end_time, limit=1000):
        """
        Fetch historical klines/candlestick data from Binance
        
        Args:
            symbol (str): Trading pair symbol (e.g., 'BTCUSDT')
            interval (str): Kline interval (e.g., '1m', '5m', '15m', '1h')
            start_time (int): Start time in milliseconds
            end_time (int): End time in milliseconds
            limit (int): Number of records to fetch
            
        Returns:
            pd.DataFrame: DataFrame with OHLCV data
        """
        try:
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_time,
                end_str=end_time,
                limit=limit
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Convert string values to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
        except BinanceAPIException as e:
            print(f"Binance API Error: {e}")
            return None
            
    def place_order(self, symbol, side, quantity, order_type='MARKET', price=None):
        """
        Place an order on Binance
        
        Args:
            symbol (str): Trading pair symbol
            side (str): 'BUY' or 'SELL'
            quantity (float): Order quantity
            order_type (str): Order type (default: 'MARKET')
            price (float): Price for limit orders
            
        Returns:
            dict: Order response from Binance
        """
        try:
            params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity
            }
            
            if order_type == 'LIMIT' and price:
                params['price'] = price
                params['timeInForce'] = 'GTC'
                
            order = self.client.create_order(**params)
            return order
            
        except BinanceAPIException as e:
            print(f"Binance API Error: {e}")
            return None
            
    def get_account_balance(self, asset=None):
        """
        Get account balance
        
        Args:
            asset (str): Specific asset to get balance for
            
        Returns:
            dict: Account balance information
        """
        try:
            account = self.client.get_account()
            if asset:
                for balance in account['balances']:
                    if balance['asset'] == asset:
                        return balance
            return account['balances']
            
        except BinanceAPIException as e:
            print(f"Binance API Error: {e}")
            return None 