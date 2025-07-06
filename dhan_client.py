import os
import requests
import pandas as pd
import numpy as np
import time
import hmac
import hashlib
from dhanhq import dhanhq

class DhanClient:
    def __init__(self, client_id, access_token, testnet=1):
        self.client_id = client_id
        self.access_token = access_token
        if testnet == 1:
            self.base_url = "https://sandbox.dhan.co/v2"  # Dhan uses same URL for live and paper trading
        else:
            self.base_url = "https://api.dhan.co/v2"
            
        self.client = dhanhq(client_id, access_token)

    def get_klines(self, symbol, interval='1', limit=20):
        """
        Get historical data from Dhan API
        symbol: NSE_EQ|INE002A01018 format or similar
        interval: '1', '5', '15', '30', '60', 'D' (1min, 5min, 15min, 30min, 1hour, Daily)
        """
        try:
            
            # Get historical data
            historical_data = self.client.historical_minute_charts(
                symbol=symbol,
                exchange_segment='NSE_FNO',  # or NSE_EQ based on instrument
                instrument_type='FUTIDX',   # FUTIDX for futures, OPTIDX for options
                expiry_code=0,
                from_date='2024-01-01',
                to_date='2024-12-31'
            )
            
            if historical_data['status'] == 'success':
                data = historical_data['data'][-limit:]  # Get last 'limit' records
                # Convert to Binance-like format [timestamp, open, high, low, close, volume]
                formatted_data = []
                for candle in data:
                    formatted_data.append([
                        int(time.mktime(time.strptime(candle['timestamp'], '%Y-%m-%d %H:%M:%S')) * 1000),
                        str(candle['open']),
                        str(candle['high']),
                        str(candle['low']),
                        str(candle['close']),
                        str(candle['volume'])
                    ])
                return formatted_data
            else:
                print(f"Error getting historical data: {historical_data}")
                return []
        except Exception as e:
            print(f"Error in get_klines: {e}")
            return []

    def get_symbol_info(self, symbol):
        """
        Get symbol information from Dhan API
        """
        try:
            # Get trading symbols
            symbols = self.client.get_trading_symbols()
            
            if symbols['status'] == 'success':
                for s in symbols['data']:
                    if s['tradingsymbol'] == symbol or s['SEM_SMST_SECURITY_ID'] == symbol:
                        print(s)
                        # Extract relevant information
                        min_qty = s.get('lot_size', 1)
                        step_size = 1  # Dhan typically uses step size of 1
                        quantity_precision = 0  # Integer quantities
                        tick_size = s.get('tick_size', 0.05)
                        price_precision = 2  # Typically 2 decimal places
                        
                        return {
                            'symbol': symbol,
                            'min_qty': min_qty,
                            'step_size': step_size,
                            'quantity_precision': quantity_precision,
                            'tick_size': tick_size,
                            'price_precision': price_precision
                        }
            
            # If symbol is not found
            return None
        except Exception as e:
            print(f"Error getting symbol info: {e}")
            return None

    def generate_signature(self, query_string):
        # Dhan doesn't use HMAC signatures like Binance
        # This method is kept for compatibility but not used
        return ""

    def login(self):
        """
        Verify Dhan API credentials
        """
        try:
            # Test API by getting funds
            funds = self.client.get_fund_limits()
            
            if funds['status'] == 'success':
                print("Login successful! API credentials are correct.")
                return True
            else:
                print("Login failed. Check your client ID and access token.")
                print(funds)
                return False
        except Exception as e:
            print(f"Login failed: {e}")
            return False
    
    def cancel_trade(self, symbol, order_id):
        """
        Cancel a specific trade order by order ID.
        """
        try:
            result = self.client.cancel_order(order_id)
            
            if result['status'] == 'success':
                print(f"Order {order_id} canceled successfully:", result)
                return result
            else:
                print(f"Failed to cancel order {order_id}: {result.get('remarks', 'Error')}")
                return None
        except Exception as e:
            print(f"Error canceling order {order_id}: {e}")
            return None

    def get_account_balance(self):
        """
        Get account balance from Dhan API
        """
        try:
            funds = self.client.get_fund_limits()
            
            if funds['status'] == 'success':
                available_balance = funds['data']['availabelBalance']
                print(f"Available Balance: {available_balance}")
                return float(available_balance)
            else:
                print("Failed to get account balance:", funds)
                return 0.0
        except Exception as e:
            print(f"Error getting balance: {e}")
            return 0.0
    
    def place_stoploss_order(self, symbol, side, quantity, stop_price):
        """
        Place stop loss order
        """
        try:
            # Convert side to Dhan format
            transaction_type = dhanhq.BUY if side == "BUY" else dhanhq.SELL
            
            result = self.client.place_order(
                tag='stop_loss',
                transaction_type=transaction_type,
                exchange_segment=dhanhq.NSE_FNO,
                product_type=dhanhq.INTRA,
                order_type=dhanhq.SL,
                validity=dhanhq.DAY,
                security_id=symbol,
                quantity=int(quantity),
                disclosed_quantity=0,
                price=0.0,
                trigger_price=float(stop_price),
                after_market_order=False,
                amo_time=dhanhq.OPEN,
                bolt_flag=False
            )
            
            if result['status'] == 'success':
                print("Stop Loss Order placed successfully", result)
                return result
            else:
                print(f"Stop Loss Order failed: {result.get('remarks', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"Error placing stop loss order: {e}")
            return None
    
    def place_order(self, symbol, side, type, quantity, price=None):
        """
        Place order on Dhan
        """
        try:
            # Convert parameters to Dhan format
            transaction_type = dhanhq.BUY if side == "BUY" else dhanhq.SELL
            
            # Convert order type
            order_type_map = {
                'MARKET': dhanhq.MARKET,
                'LIMIT': dhanhq.LIMIT,
                'STOP_MARKET': dhanhq.SL,
                'STOP_LIMIT': dhanhq.SL_M
            }
            dhan_order_type = order_type_map.get(type, dhanhq.MARKET)
            
            # Set price based on order type
            order_price = float(price) if price and type == 'LIMIT' else 0.0
            trigger_price = float(price) if price and 'STOP' in type else 0.0
            
            result = self.client.place_order(
                tag='',
                transaction_type=transaction_type,
                exchange_segment=dhanhq.NSE_FNO,
                product_type=dhanhq.INTRA,
                order_type=dhan_order_type,
                validity=dhanhq.DAY,
                security_id=symbol,
                quantity=int(quantity),
                disclosed_quantity=0,
                price=order_price,
                trigger_price=trigger_price,
                after_market_order=False,
                amo_time=dhanhq.OPEN,
                bolt_flag=False
            )
            
            if result['status'] == 'success':
                print("Order placed successfully", result)
                return result
            else:
                print(f"Order failed: {result.get('remarks', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"Error placing order: {e}")
            return None

    def close_position(self, symbol, side, type, quantity):
        """
        Close an open position with a market order.
        In Dhan, this is typically done by placing an opposite order
        """
        try:
            # Reverse the side to close position
            close_side = "SELL" if side == "BUY" else "BUY"
            
            result = self.place_order(symbol, close_side, "MARKET", quantity)
            
            if result:
                print("Position closed successfully:", result)
                return result
            else:
                print("Failed to close position")
                return None
        except Exception as e:
            print(f"Error closing position: {e}")
            return None

    def check_and_place_order(self, symbol, side, type, quantity, price=None):
        balance_info = self.get_account_balance()
        # Example check to ensure there's enough balance
        sufficient_balance = balance_info > 1000  # Basic check, adjust as needed

        if sufficient_balance:
            self.place_order(symbol, side, type, quantity, price)
        else:
            print("Insufficient balance to place order.")

    def set_leverage(self, symbol, leverage):
        """
        Set leverage - Note: Dhan doesn't have direct leverage setting like Binance
        Leverage is typically inherent in the instrument type (futures/options)
        This method is kept for compatibility
        """
        try:
            print(f"Note: Leverage setting not directly applicable in Dhan API")
            print(f"Leverage is inherent in the instrument type for {symbol}")
            print(f"Requested leverage: {leverage}")
            return True
        except Exception as e:
            print(f"Error in set_leverage: {e}")
            return False

if __name__ == "__main__":
    # Dhan API credentials
    client_id = 'your_client_id'  # Your Dhan Client ID
    access_token = 'your_access_token'  # Your Dhan Access Token

    client = DhanClient(client_id, access_token)
    client.set_leverage(symbol='NSE_FNO|26000', leverage=50)  # Example security ID
    res = client.get_klines(symbol='NSE_FNO|26000', interval='5m', limit=20)
    print(res)

    if client.login():
        symbol = "NSE_FNO|26000"  # Example Nifty Future security ID
        side = "BUY"
        type = "MARKET"
        quantity = 25  # Lot size for Nifty futures
        current_price = 25000
        
        client.get_account_balance()
        time.sleep(2)
        client.place_order(symbol, side, type, quantity, current_price)
        # client.check_and_place_order(symbol, side, type, quantity)
    else:
        print("Cannot proceed without valid API credentials.")