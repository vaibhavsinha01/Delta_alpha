import os
import requests
import pandas as pd
import numpy as np
import time
import hmac
import hashlib
from utils.binance_client import BinanceClient as Client

class BinanceClient:
    def __init__(self, api_key, api_secret_key,testnet=1):
        self.api_key = api_key
        self.api_secret_key = api_secret_key
        if testnet==1:
            self.base_url ="https://testnet.binancefuture.com"
        else:
            self.base_url="https://fapi.binance.com"
            
        self.client = Client(api_key,api_secret_key)

    def get_klines(self, symbol, interval='1m', limit=20):
        url = f"{self.base_url}/fapi/v1/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        response = requests.get(url, params=params)
        data = response.json()
        # Print only open, high, low, and close values
        # for entry in data:
        #     print(f"Open: {entry[1]}, High: {entry[2]}, Low: {entry[3]}, Close: {entry[4]}")
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
                price_precision=s.get('pricePrecision',0)
                
                # Iterate through filters to get minQty and stepSize from LOT_SIZE filter
                for f in s['filters']:
                    if f['filterType'] == 'PRICE_FILTER':
                        tick_size = float(f['tickSize'])
                    if f['filterType'] == 'LOT_SIZE':
                        min_qty = float(f['minQty'])
                        step_size = float(f['stepSize'])
                        break
                
                # Return as a structured dictionary]
                # print(symbol,min_qty,step_size,quantity_precision)
                return {
                    'symbol': symbol,
                    'min_qty': min_qty,
                    'step_size': step_size,
                    'quantity_precision': quantity_precision,
                    'tick_size':tick_size,
                    'price_precision':price_precision
                }
        
        # If symbol is not found
        return None

    def generate_signature(self, query_string):
        return hmac.new(self.api_secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    def login(self):
        endpoint = "/fapi/v2/account"
        timestamp = int(time.time() * 1000)
        params = {
            "timestamp": timestamp,
        }
        query_string = '&'.join([f"{key}={params[key]}" for key in params])
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
        """
        Cancel a specific trade order by order ID.
        """
        url = f"{self.base_url}/fapi/v1/order"
        timestamp = int(time.time() * 1000)
        params = {
            "symbol": symbol,
            "orderId": order_id,
            "timestamp": timestamp,
        }
        query_string = '&'.join([f"{key}={params[key]}" for key in params])
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
        query_string = '&'.join([f"{key}={params[key]}" for key in params])
        signature = self.generate_signature(query_string)
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        params["signature"] = signature
        response = requests.get(f"{self.base_url}{endpoint}", headers=headers, params=params)
        balance_info = response.json()
        #print("Account Balance:", balance_info)
        try:
            for account in balance_info:
                if account['asset'] == 'USDT':
                    print(account['balance'])
                    return float(account['balance'])  # Convert balance to float for calculations
        except Exception as e:
            print(e)
        return 0.0  # Return 0 if USDT is not found
    # def get_symbol_info(self,symbol):
    #     #GETS THE MINIMUM Quantity  and using that round the digits 
    def place_stoploss_order(self,symbol, side, quantity, stop_price):
        url = f"{self.base_url}/fapi/v1/order"
        timestamp = int(time.time() * 1000)
        params = {
            "symbol": symbol,
            "side": side,
            "type": "STOP_MARKET",
            "stopPrice": stop_price,
            "quantity": quantity,
            "timestamp": timestamp,
            "closePosition": True,
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
            print("Order placed successfully", response_data)
        else:
            print(f"Order failed: {response_data['msg']}")
        return response_data
    
    def place_order(self, symbol, side, type, quantity, price=None):
        url = f"{self.base_url}/fapi/v1/order"
        timestamp = int(time.time() * 1000)
        params = {
            "symbol": symbol,
            "side": side,
            "type": type,
            "quantity": quantity,
            "timestamp": timestamp,
        }
        if price is not None:
            params["price"] = price
            params["timeInForce"] = "GTC"

        query_string = '&'.join([f"{key}={params[key]}" for key in params])
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
            print(f"Order failed: {response_data['msg']}")
        return response_data
    
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
    
    def close_position(self, symbol, side,type, quantity):
        """
        Close an open position with a market order using reduceOnly.
        """
        url = f"{self.base_url}/fapi/v1/order"
        timestamp = int(time.time() * 1000)
        params = {
            "symbol": symbol,
            "side": side,
            "type": type,
            "quantity": quantity,
            "reduceOnly": "true",  # Close the existing position
            "timestamp": timestamp
        }
        query_string = '&'.join([f"{key}={params[key]}" for key in params])
        signature = self.generate_signature(query_string)
        headers = {"X-MBX-APIKEY": self.api_key}
        params["signature"] = signature
        response = requests.post(url, headers=headers, params=params)
        response_data = response.json()

        if response.status_code == 200:
            print("Position closed successfully:", response_data)
        else:
            print(f"Failed to close position: {response_data['msg']}")

    def check_and_place_order(self, symbol, side, type, quantity, price=None):
        balance_info = self.get_account_balance()
        # Example check to ensure there's enough balance
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
            "leverage": leverage,
            "timestamp": timestamp,
        }
        query_string = '&'.join([f"{key}={params[key]}" for key in params])
        signature = self.generate_signature(query_string)
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        params["signature"] = signature
        response = requests.post(f"{self.base_url}{endpoint}", headers=headers, params=params)
        
        if response.status_code == 200:
            print(f"Leverage set to {leverage} for {symbol}")
        else:
            print("Failed to set leverage:", response.json())

if __name__ == "__main__":
    # Securely load API keys from environment variables
    api_key = '1ff87751c4a5a314b617856c252f342ee4aeff38797361ab676088330b1c26b1'  # Your Binance API key
    api_secret_key = '4a924ff228b870e760d42891db0a6b50a61139453232de53d7b80b7d3a7744ef'  # Your Binance API secret

    client = BinanceClient(api_key, api_secret_key)
    client.set_leverage(symbol='BTCUSDT',leverage=50)
    res = client.get_klines(symbol='BTCUSDT',interval='5m',limit=20)
    print(res)

    if client.login():
        symbol = "BTCUSDT"  # Example symbol
        side = "BUY"
        type = "MARKET"  # Changed to MARKET order type
        quantity = 0.01
        current_price = 104500
        #levarge to 100
        # No need to set a price for a MARKET order
        client.get_account_balance()
        time.sleep(2)
        client.place_order(symbol, side, type, quantity,current_price)
        # client.check_and_place_order(symbol, side, type, quantity)
        client.place_oco_order(symbol=symbol,side=side,type="LIMIT",quantity=quantity,current_price=current_price)
        # client.client.client
    else:
        print("Cannot proceed without valid API credentials.")

