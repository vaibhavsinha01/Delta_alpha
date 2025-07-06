import os
import requests
import pandas as pd
import numpy as np
import time
import hmac
import hashlib
from urllib.parse import urlencode
from utils.binance_client import BinanceClient as Client

class BinanceClient:
    def __init__(self, api_key, api_secret_key, testnet=1):
        self.api_key = api_key
        self.api_secret_key = api_secret_key
        if testnet == 1:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"

        self.client = Client(api_key, api_secret_key)

    def get_history(self):
        return self.client.futures_income_history()
    
    def get_klines(self, symbol, interval='1m', limit=20):
        url = f"{self.base_url}/fapi/v1/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        response = requests.get(url, params=params)
        data = response.json()
        return data

    def get_symbol_info(self, symbol):
        url = f"{self.base_url}/fapi/v1/exchangeInfo"
        response = requests.get(url)
        data = response.json()
        
        for s in data['symbols']:
            if s['symbol'] == symbol:
                print(s)
                # Extracting minQty, stepSize, and quantityPrecision
                min_qty = None
                step_size = None
                quantity_precision = s.get('quantityPrecision', None)
                price_precision = s.get('pricePrecision', 0)
                
                # Iterate through filters to get minQty and stepSize from LOT_SIZE filter
                for f in s['filters']:
                    if f['filterType'] == 'PRICE_FILTER':
                        tick_size = float(f['tickSize'])
                    if f['filterType'] == 'LOT_SIZE':
                        min_qty = float(f['minQty'])
                        step_size = float(f['stepSize'])
                        break
                
                return {
                    'symbol': symbol,
                    'min_qty': min_qty,
                    'step_size': step_size,
                    'quantity_precision': quantity_precision,
                    'tick_size': tick_size,
                    'price_precision': price_precision
                }
        
        return None

    def generate_signature(self, query_string):
        return hmac.new(
            self.api_secret_key.encode('utf-8'), 
            query_string.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def login(self):
        endpoint = "/fapi/v2/account"
        timestamp = int(time.time() * 1000)
        params = {
            "timestamp": timestamp,
        }
        query_string = urlencode(params)
        signature = self.generate_signature(query_string)
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        params["signature"] = signature
        response = requests.get(f"{self.base_url}{endpoint}", headers=headers, params=params)

        if response.status_code == 200:
            print("Login successful! API key is correct.")
            return True
        else:
            print("Login failed. Check your API key and secret.")
            print(response.json())
            return False

    def cancel_trade(self, symbol, order_id):
        """Cancel a specific trade order by order ID."""
        url = f"{self.base_url}/fapi/v1/order"
        timestamp = int(time.time() * 1000)
        params = {
            "symbol": symbol,
            "orderId": order_id,
            "timestamp": timestamp,
        }
        query_string = urlencode(params)
        signature = self.generate_signature(query_string)
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        params["signature"] = signature
        response = requests.delete(url, headers=headers, params=params)
        response_data = response.json()

        if response.status_code == 200:
            print(f"Order {order_id} canceled successfully:", response_data)
        else:
            print(f"Failed to cancel order {order_id}: {response_data.get('msg', 'Error')}")

    def get_account_balance(self):
        endpoint = "/fapi/v2/balance"
        timestamp = int(time.time() * 1000)
        params = {
            "timestamp": timestamp,
        }
        query_string = urlencode(params)
        signature = self.generate_signature(query_string)
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        params["signature"] = signature
        response = requests.get(f"{self.base_url}{endpoint}", headers=headers, params=params)
        balance_info = response.json()
        
        try:
            for account in balance_info:
                if account['asset'] == 'USDT':
                    print(account['balance'])
                    return float(account['balance'])
        except Exception as e:
            print(e)
        return 0.0

    def place_stoploss_order(self, symbol, side, quantity, stop_price):
        url = f"{self.base_url}/fapi/v1/order"
        timestamp = int(time.time() * 1000)
        params = {
            "symbol": symbol,
            "side": side,
            "type": "STOP_MARKET",
            "stopPrice": str(stop_price),
            "quantity": str(quantity),
            "timestamp": timestamp,
            "closePosition": "true",
        }
        query_string = urlencode(params)
        signature = self.generate_signature(query_string)
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        params["signature"] = signature
        response = requests.post(url, headers=headers, params=params)
        response_data = response.json()

        if response.status_code == 200:
            print("Stop loss order placed successfully", response_data)
        else:
            print(f"Stop loss order failed: {response_data.get('msg', 'Unknown error')}")
        return response_data

    def place_order(self, symbol, side, type, quantity, price=None):
        url = f"{self.base_url}/fapi/v1/order"
        timestamp = int(time.time() * 1000)
        params = {
            "symbol": symbol,
            "side": side,
            "type": type,
            "quantity": str(quantity),
            "timestamp": timestamp,
        }
        
        if price is not None:
            params["price"] = str(price)
            params["timeInForce"] = "GTC"

        query_string = urlencode(params)
        signature = self.generate_signature(query_string)
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        params["signature"] = signature
        response = requests.post(url, headers=headers, params=params)
        response_data = response.json()

        if response.status_code == 200:
            print("Order placed successfully", response_data)
        else:
            print(f"Order failed: {response_data.get('msg', 'Unknown error')}")
        return response_data

    def close_position(self, symbol, side, type, quantity):
        """Close an open position with a market order using reduceOnly."""
        url = f"{self.base_url}/fapi/v1/order"
        timestamp = int(time.time() * 1000)
        params = {
            "symbol": symbol,
            "side": side,
            "type": type,
            "quantity": str(quantity),
            "reduceOnly": "true",
            "timestamp": timestamp
        }
        query_string = urlencode(params)
        signature = self.generate_signature(query_string)
        
        headers = {"X-MBX-APIKEY": self.api_key}
        params["signature"] = signature
        response = requests.post(url, headers=headers, params=params)
        response_data = response.json()

        if response.status_code == 200:
            print("Position closed successfully:", response_data)
        else:
            print(f"Failed to close position: {response_data.get('msg', 'Unknown error')}")

    def check_and_place_order(self, symbol, side, type, quantity, price=None):
        balance_info = self.get_account_balance()
        sufficient_balance = True  # Replace with actual logic based on balance_info

        if sufficient_balance:
            self.place_order(symbol, side, type, quantity, price)
        else:
            print("Insufficient balance to place order.")

    def set_leverage(self, symbol, leverage):
        endpoint = "/fapi/v1/leverage"
        timestamp = int(time.time() * 1000)
        params = {
            "symbol": symbol,
            "leverage": int(leverage),
            "timestamp": timestamp,
        }
        query_string = urlencode(params)
        signature = self.generate_signature(query_string)
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        params["signature"] = signature
        response = requests.post(f"{self.base_url}{endpoint}", headers=headers, params=params)
        
        if response.status_code == 200:
            print(f"Leverage set to {leverage} for {symbol}")
            return True
        else:
            print("Failed to set leverage:", response.json())
            return False
        
    def place_oco_order(self, symbol, side, type, quantity, current_price):
        url = f"{self.base_url}/fapi/v1/order"
        timestamp = int(time.time() * 1000)
        
        # Calculate TP/SL with 1% difference from current price
        if side.upper() == "BUY":
            take_profit_price = current_price * 1.01  # 1% above current price
            stop_price = current_price * 0.99         # 1% below current price
            stop_limit_price = current_price * 0.985  # Slightly below stop price
        else:  # SELL
            take_profit_price = current_price * 0.99  # 1% below current price
            stop_price = current_price * 1.01         # 1% above current price
            stop_limit_price = current_price * 1.015  # Slightly above stop price
        
        params = {
            "symbol": symbol,
            "side": side,
            "type":type,
            "quantity": quantity,
            "price": take_profit_price,
            "stopLimitPrice": stop_limit_price,
            "timeInForce": "GTC",
            "stopLimitTimeInForce": "GTC",
            "timestamp": timestamp,
        }
        
        query_string = '&'.join([f"{key}={params[key]}" for key in params])
        signature = self.generate_signature(query_string)
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        params["signature"] = signature
        
        response = requests.post(url, headers=headers, params=params)
        response_data = response.json()
        
        if response.status_code == 200:
            print("OCO Order placed successfully", response_data)
        else:
            print(f"OCO Order failed: {response_data['msg']}")
        
        return response_data

if __name__ == "__main__":
    # Test API keys (replace with your actual keys)
    api_key = "PNEz62B9brZhp9JU2IuGlEuikqLySbgqVYgRlfEgi3qQwkRdjuHV7UqfNfLhUCN1"
    api_secret_key = "aGVtwY93qKAzPjHnqhpYyiY3oBoDCHrA3r9jUfmeGLUBJPGdNeydGSzJkol6G5FW"
    
    client = BinanceClient(api_key, api_secret_key)
    
    if client.login():
        # Test leverage setting
        success = client.set_leverage(symbol='BTCUSDT', leverage=50)
        if success:
            print("Leverage set successfully!")
        
        # Test getting klines
        res = client.get_klines(symbol='BTCUSDT', interval='5m', limit=20)
        print("Kline data retrieved:", len(res), "candles")
        
        # Test account balance
        balance = client.get_account_balance()
        print(f"Account balance: {balance} USDT")
        
        # Test placing a market order (uncomment to test actual trading)
        # symbol = "BTCUSDT"
        # side = "BUY"
        # type = "MARKET"
        # quantity = 0.01
        # client.check_and_place_order(symbol, side, type, quantity)
    else:
        print("Cannot proceed without valid API credentials.")