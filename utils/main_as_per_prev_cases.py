import pandas as pd
import time
from datetime import datetime
from config import *
from module.rf import RangeFilter
from module.ib_indicator import calculate_inside_ib_box
from module.rsi_gaizy import RSIGainzy
from module.rsi_buy_sell import RSIBuySellIndicator
from important import *
import warnings
import requests
import json
from delta_rest_client import DeltaRestClient
from my_logger import get_logger
import hashlib
import hmac
from binance_client_ import BinanceClient

# Suppress specific FutureWarnings from pandas
warnings.simplefilter(action='ignore', category=FutureWarning)
logger = get_logger("main_delta")

fake_loss_amount = 0  # Track accumulated fake losses
fake_loss_amount_maxlimit = DELTA_FAKE_LOSS_MAX_AMOUNT  # Maximum fake loss before increasing martingale level
trade_taken_time = None  # Track when trade was taken
trade_taken_signal = 0  # Track what signal was used for trade
trade_taken_price = 0  # Track entry price for loss calculation
trade_taken_direction = None  # Track trade direction
bracket_tp_order_id = None
bracket_sl_order_id = None
current_bracket_state_tp = None
current_bracket_state_sl = None
fake_trade_flag = 0
candle_entry = None
candle_exit = None
# double_trigger_flag = False # track if double trigger occured
# pending_double_trigger = False # track if next level increase should be double
# DOUBLE_TRIGGER_WINDOW = RENTRY_TIME_BINANCE # for the 15 the timeframe being used for trading - ONE CANDLE ONLY 
DOUBLE_TRIGGER_WINDOW = 15

class DeltaBroker:
    def __init__(self):
        self.api_key = DELTA_API_KEY
        self.api_secret = DELTA_API_SECRET
        # self.base_url = "https://cdn-ind.testnet.deltaex.org"
        self.base_url = "https://api.india.delta.exchange"
        self.broker = DeltaRestClient(base_url=self.base_url, api_key=self.api_key, api_secret=self.api_secret)
        self.product_symbol = DELTA_SYMBOL
        self.product_symbol_place_order = DELTA_SYMBOL_PLACE_ORDER
        self.product_id = DELTA_TOKEN
        self.min_lot = DELTA_MIN_LOT
        self.base_leverage = DELTA_BASE_LEVERAGE
        self.df = None
        self.current_candle_time = None

    def generate_signature(self, secret, message):
        try:
            message = bytes(message, 'utf-8')
            secret = bytes(secret, 'utf-8')
            hash = hmac.new(secret, message, hashlib.sha256)
            return hash.hexdigest()
        except Exception as e:
            print(f"Error occurred in generate_signature: {e}")

    def timestamp_generator(self):
        try:
            import time
            return str(int(time.time()))
        except Exception as e:
            print(f"Error occurred in timestamp_generator: {e}")

    def place_order_market(self, side="buy", size=1):
        """Place a market order"""
        try:
            payload = {
                "product_symbol": self.product_symbol_place_order,
                "size": abs(size),
                "side": side,
                "order_type": "market_order",
                "time_in_force": "gtc"
            }

            method = 'POST'
            path = '/v2/orders'
            url = self.base_url + path
            timestamp = str(int(time.time()))
            query_string = ''
            payload_json = json.dumps(payload, separators=(',', ':'))
            signature_data = method + timestamp + path + query_string + payload_json
            signature = self.generate_signature(self.api_secret, signature_data)

            headers = {
                'api-key': self.api_key,
                'timestamp': timestamp,
                'signature': signature,
                'User-Agent': 'python-rest-client',
                'Content-Type': 'application/json'
            }

            response = requests.post(url, headers=headers, data=payload_json)
            print(f"Market Order Response Code: {response.status_code}")
            result = response.json()
            print(f"Market Order Response: {result}")
            
            if response.status_code == 200 and result.get('success'):
                return result['result']
            return None

        except Exception as e:
            print(f"Error in place_order_market function: {e}")
            return None

    def place_order_bracket(self, side="buy", size=1, entry_price=None, stop_price=None, take_profit_price=None):
        """Place a bracket order with entry, stop loss, and take profit"""
        try:
            # For bracket orders, we need limit prices
            if entry_price is None:
                entry_price = self.get_market_price()

            if side == "buy":
                stop_limit_price = str(float(stop_price) - STOP_LIMIT_PRICE_AMOUNT)  # Slightly lower than stop
                take_profit_limit_price = str(float(take_profit_price) - STOP_LIMIT_PRICE_AMOUNT)  # Slightly lower than TP
            else:
                stop_limit_price = str(float(stop_price) + STOP_LIMIT_PRICE_AMOUNT)  # Slightly higher than stop
                take_profit_limit_price = str(float(take_profit_price) + STOP_LIMIT_PRICE_AMOUNT)  # Slightly higher than TP

            payload = {
                "product_symbol": self.product_symbol_place_order,
                "limit_price": str(entry_price),
                "size": size,
                "side": side,
                "order_type": "limit_order",
                "time_in_force": "gtc",
                "stop_loss_order": {
                    "order_type": "limit_order",
                    "stop_price": str(stop_price),
                    "limit_price": stop_limit_price
                },
                "take_profit_order": {
                    "order_type": "limit_order",
                    "stop_price": str(take_profit_price),
                    "limit_price": take_profit_limit_price
                },
                "bracket_stop_trigger_method": "last_traded_price"
            }

            method = 'POST'
            path = '/v2/orders/bracket'
            url = self.base_url + path
            timestamp = str(int(time.time()))
            query_string = ''
            payload_json = json.dumps(payload, separators=(',', ':'))
            signature_data = method + timestamp + path + query_string + payload_json
            signature = self.generate_signature(self.api_secret, signature_data)

            headers = {
                'api-key': self.api_key,
                'timestamp': timestamp,
                'signature': signature,
                'User-Agent': 'python-rest-client',
                'Content-Type': 'application/json'
            }

            response = requests.post(url, headers=headers, data=payload_json)
            print(f"Bracket Order Response Code: {response.status_code}")
            result = response.json()
            print(f"Bracket Order Response: {result}")
            
            if response.status_code == 200 and result.get('success'):
                # return result['result']
                return result
            return None

        except Exception as e:
            print(f"Error in place_order_bracket function: {e}")
            return None

    def get_market_price_latest(self):
        """Get current market price"""
        try:
            last = self.df.iloc[-1]
            return float(last['close'])
        except Exception as e:
            last = self.df.iloc[-1]
            return float(last['Close'])
        
    def get_market_price(self):
        try:
            # df = self.fetch_data() # HERE I AM FETCHING DATA FROM BINANCE BECAUSE THE DATA FROM DELTA EXCHANGE IS GIVING A LAG OF 1 MINUTE
            df = self.fetch_data_binance()
            last_row = df.iloc[-1]
            last_price = float(last_row['close'])
            return last_price
        except Exception as e:
            try:
                df = self.fetch_data_binance() # HERE I AM FETCHING DATA FROM BINANCE BECAUSE THE DATA FROM DELTA EXCHANGE IS GIVING A LAG OF 1 MINUTE
                last_row = df.iloc[-1]
                last_price = float(last_row['Close'])
                return last_price
            except Exception as e:
                try:
                    return float(self.df.iloc[-1]['close'])
                except Exception as e:
                    return float(self.df.iloc[-1]['Close'])

    def get_active_positions(self):
        """Get active positions from Delta Exchange for ETHUSD (product_id: 1699)""" # 1699 for testnet/3136 for the mainnet
        try:
            method = "GET"
            path = "/v2/positions"
            url = self.base_url + path
            timestamp = str(int(time.time()))
            
            # Build query parameters for ETHUSD
            params = {'product_id': str(DELTA_TOKEN)}
            
            # Build query string
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            
            # Create signature data - ADD '?' before query_string for GET requests with params
            signature_data = method + timestamp + path + '?' + query_string
            signature = self.generate_signature(self.api_secret, signature_data)
            
            headers = {
                "api-key": self.api_key,
                "timestamp": timestamp,
                "signature": signature,
                "User-Agent": "python-rest-client"
            }
            
            # Make the request with query parameters
            response = requests.get(url, headers=headers, params=params)
            
            positions_data = response.json()
            print(f"response is {response}")
            # Print the full response for debugging
            print("Active Positions Response:", positions_data)
            print(f"Current size of positions is: {positions_data['result']['size']}")

            if int(abs(positions_data['result']['size']))>0:
                return False
            else:
                return True
                
        except Exception as e: # don't get the result as success 
            # print(f"Error getting active positions: {e}")
            # import time
            # time.sleep(10) # keep this here - once every 500 times
            # logger.info(f"exception occured in get_active_positions so sleeping for 0 seconds")
            try:
                method = "GET"
                path = "/v2/positions"
                url = self.base_url + path
                timestamp = str(int(time.time()))
                
                # Build query parameters for ETHUSD
                params = {'product_id': str(DELTA_TOKEN)}
                
                # Build query string
                query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                
                # Create signature data - ADD '?' before query_string for GET requests with params
                signature_data = method + timestamp + path + '?' + query_string
                signature = self.generate_signature(self.api_secret, signature_data)
                
                headers = {
                    "api-key": self.api_key,
                    "timestamp": timestamp,
                    "signature": signature,
                    "User-Agent": "python-rest-client"
                }
                
                # Make the request with query parameters
                response = requests.get(url, headers=headers, params=params)
                
                positions_data = response.json()
                print(f"response is {response}")
                # Print the full response for debugging
                print("Active Positions Response:", positions_data)
                print(f"Current size of positions is: {positions_data['result']['size']}")

                if int(abs(positions_data['result']['size']))>0:
                    return False
                else:
                    return True
            except Exception as e:
                print(f"error in getting active position in retry :{e}")
                return None
    
    def get_order_status(self, order_id):
        """Get order status"""
        try:
            method = "GET"
            path = f"/v2/orders/{order_id}"
            url = self.base_url + path
            timestamp = str(int(time.time()))
            query_string = ''
            signature_data = method + timestamp + path + query_string
            signature = self.generate_signature(self.api_secret, signature_data)

            headers = {
                "api-key": self.api_key,
                "timestamp": timestamp,
                "signature": signature,
                "User-Agent": "python-rest-client"
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            print(f"Error in get_order_status: {e}")
            return None

    def get_usd_balance(self):
        """Get USD/USDT balance specifically"""
        try:
            method = "GET"
            path = "/v2/wallet/balances"
            url = self.base_url + path
            timestamp = str(int(time.time()))
            query_string = ''
            signature_data = method + timestamp + path + query_string
            signature = self.generate_signature(self.api_secret, signature_data)

            headers = {
                "api-key": self.api_key,
                "timestamp": timestamp,
                "signature": signature,
                "User-Agent": "python-rest-client"
            }

            response = requests.get(url, headers=headers)
            wallet_data = response.json()
            print(wallet_data['result'][0]['balance'])
            
            return wallet_data['result'][0]['balance']
            
        except Exception as e:
            print(f"Error getting USD balance: {e}")
            return None

    def calculate_trade_size(self, current_price, leverage, base_capital):
        """Calculate trade size based on capital and leverage"""
        try:
            if current_price is None or current_price <= 0:
                return self.min_lot
            
            # Calculate position size: (capital * leverage) / price
            position_value = base_capital * leverage
            quantity = position_value / current_price
            # Ensure minimum quantity
            if quantity < self.min_lot:
                quantity = self.min_lot
                
            print(f"Position sizing calculation:")
            print(f"  Capital: ${base_capital}")
            print(f"  Leverage: {leverage}x")
            print(f"  Price: ${current_price}")
            print(f"  Calculated quantity: {quantity}")
            print(f"  Notional value: ${quantity * current_price}")
            
            return int(quantity)  # Delta typically uses integer quantities
            
        except Exception as e:
            print(f"Error calculating trade size: {e}")
            return self.min_lot

    def set_leverage(self, leverage):
        """Set leverage for the product"""
        try:
            method = "POST"
            path = f"/v2/products/{self.product_id}/orders/leverage"
            url = self.base_url + path
            timestamp = str(int(time.time()))

            payload = {"leverage": str(leverage)}
            payload_json = json.dumps(payload, separators=(',', ':'))
            signature_data = method + timestamp + path + payload_json
            signature = self.generate_signature(self.api_secret, signature_data)

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'api-key': self.api_key,
                'timestamp': timestamp,
                'signature': signature,
                'User-Agent': 'custom-python-client/1.0'
            }

            response = requests.post(url, headers=headers, data=payload_json)
            print(f"Set Leverage status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("Leverage set successfully:", result)
                return True
            else:
                print(response.json())
                print(response)
                print("Failed to set leverage")
                return False

        except Exception as e:
            # import time
            # time.sleep(1)
            print(f"sleeping for 0 seconds because and exception in setting leverage has occured")
            logger.info(f"sleeping for 0 seconds because of exception in setting leverage")
            try:
                method = "POST"
                path = f"/v2/products/{self.product_id}/orders/leverage"
                url = self.base_url + path
                timestamp = str(int(time.time()))

                payload = {"leverage": str(leverage)}
                payload_json = json.dumps(payload, separators=(',', ':'))
                signature_data = method + timestamp + path + payload_json
                signature = self.generate_signature(self.api_secret, signature_data)

                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'api-key': self.api_key,
                    'timestamp': timestamp,
                    'signature': signature,
                    'User-Agent': 'custom-python-client/1.0'
                }

                response = requests.post(url, headers=headers, data=payload_json)
                print(f"Set Leverage status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print("Leverage set successfully:", result)
                    return True
                else:
                    print(response.json())
                    print(response)
                    print("Failed to set leverage")
                    return False
            except Exception as e:
                print(f"Error in set_leverage: {e}")
                return None

    def connect(self):
        """Initialize connection"""
        try:
            res = self.broker._init_session()
            print("Delta connection established:", res)
            return True
        except Exception as e:
            print(f"Error occurred in connection: {e}")
            return False
        
    def get_current_datetime(self):
        """Get current datetime for data fetching"""
        try:
            return datetime.now()
        except Exception as e:
            print(f"Error in get_current_datetime: {e}")
            return None

    def fetch_data(self):
        try:
            # Add datetime info to the data fetching
            current_time = self.get_current_datetime()
            print(f"Fetching data at: {current_time}")
            
            self.df = self.broker.get_ticker_data(symbol=DELTA_SYMBOL,resolution=DELTA_INTERVAL) # current time / other things need to be accounted for
            
            self.df['Timestamp'] = pd.to_datetime(self.df['time'],unit='s')
            self.df.sort_values(by='Timestamp',ascending=False,inplace=True)
            self.df = self.df.iloc[::-1].reset_index(drop=True)
            return self.df
                
        except Exception as e:
            print(f"Error occured in fetching the data : {e}")
            return None
    
    def interval_to_seconds(self,interval):
        try:
            if interval.endswith('m'):
                return int(interval[:-1]) * 60
            elif interval.endswith('h'):
                return int(interval[:-1]) * 60 * 60
            elif interval.endswith('d'):
                return int(interval[:-1]) * 24 * 60 * 60
            else:
                raise ValueError(f"Unsupported interval: {interval}")
        except Exception as e:
            print(f"Error converting interval to seconds: {e}")
            return 60  # Default to 1 minute
    
    def fetch_data_binance(self):
        # from binance_client_ import BinanceClient
        from bybit_client import BybitClient
        # binance_client = BinanceClient(api_key=BINANCE_API_KEY,api_secret_key=BINANCE_API_SECRET,testnet=0)
        binance_client = BybitClient()
        limit = 1000
        interval_seconds = delta_client.interval_to_seconds(DELTA_INTERVAL)
        end_time = int(time.time() * 1000)
        start_time = end_time - (interval_seconds * 1000 * limit)
        # self.df = binance_client.get_klines(symbol=BINANCE_SYMBOL,interval=BINANCE_INTERVAL,limit=199)
        self.df = binance_client.get_klines(symbol="ETHUSD",category="inverse",interval=BYBIT_INTERVAL,limit=200)
        self.df['Timestamp'] = pd.to_datetime(self.df['time'],unit='ms')
        self.df.sort_values(by='Timestamp',ascending=False,inplace=True)
        self.df = self.df.iloc[::-1].reset_index(drop=True)
        return self.df

class RiskManager:
    def __init__(self, sl_buffer_points, tp_percent, initial_capital):
        self.sl_buffer_points = sl_buffer_points
        self.tp_percent = tp_percent
        self.equity = initial_capital
        self.max_drawdown = 0
        self.peak_equity = initial_capital

    def calculate_sl_tp(self, entry_price, direction, prev_row, second_last_row):
        try:
            entry_price = float(entry_price)
            sl_buffer = float(self.sl_buffer_points)
            tp_percent = float(self.tp_percent)
            second_low = float(second_last_row['low'])
            second_high = float(second_last_row['high'])

            if direction == 'buy':
                sl = max(second_low, entry_price - sl_buffer)
                tp = entry_price * (1 + tp_percent / 100)
            else:  # sell
                sl = min(second_high, entry_price + sl_buffer)
                tp = entry_price * (1 - tp_percent / 100)

            return round(sl, 2), round(tp, 2)

        except Exception as e:
            print(f"Error calculating SL/TP: {e}")
            # Fallback logic
            try:
                entry_price = float(entry_price)
                sl_buffer = float(self.sl_buffer_points)
                tp_percent = float(self.tp_percent)

                if direction == 'buy':
                    sl = entry_price - sl_buffer
                    tp = entry_price * (1 + tp_percent / 100)
                else:
                    sl = entry_price + sl_buffer
                    tp = entry_price * (1 - tp_percent / 100)

                return round(sl, 2), round(tp, 2)

            except Exception as e_inner:
                print(f"Fallback also failed: {e_inner}")
                return None, None

class MartingaleManager:
    def __init__(self, base_capital, base_leverage=1):
        self.base_capital = base_capital
        self.base_leverage = base_leverage
        self.current_level = 0
        self.leverage_multipliers = [1, 2, 4, 8, 16]
        self.max_levels = 5
        self.last_trade_result = None
        self.balance_before = None # this value is updated when the trade is taken , used for the opposite trade

        # Position tracking

        self.entry_signal = None
        self.position_order_id = None
        self.last_tp_price = None
        self.last_sl_price = None
        self.last_entry_price = None
        self.last_direction = None
        self.last_quantity = None
        self.h_pos = 0
        # Double trigger tracking
        self.last_loss_timestamp = None
        self.last_loss_type = None  # 'sl' or 'fake'
        self.pending_second_increment = False 
        self.start_elevated_after_martingale = False
        self.double_trigger_occurred_this_cycle = False  # Track if double trigger happened in current martingale cycle
        self.skip_fake_losses_this_cycle = False
        self.in_martingale_cycle = False  # NEW: Track if we're in an active martingale cycle

    def get_leverage(self):
        """Get current leverage based on RM1 system with post-martingale elevation"""
        try:
            # If we just completed martingale and are at level 0, start at level 1 instead
            if self.current_level == 0 and self.start_elevated_after_martingale:
                effective_level = 1  # Start at 20x instead of 10x
                # logger.info(f"POST-MARTINGALE: Starting at elevated level 1 (20x) instead of base")
            else:
                effective_level = self.current_level
                
            leverage = self.base_leverage * self.leverage_multipliers[effective_level]
            
            # Add validation logging
            # logger.info(f"Leverage calculation: Level={self.current_level}, Effective={effective_level}, Leverage={leverage}x")
            
            return leverage
        except Exception as e:
            print(f"Error getting leverage: {e}")
            return self.base_leverage
    
    def can_take_trade(self):
        """Check if we can take a new trade (no existing position)"""
        return self.h_pos == 0
    
    def set_position(self, direction, entry_price, sl_price, tp_price, quantity, entry_signal):
        """Set position status when opening a trade"""
        try:
            if direction == 'buy':
                self.h_pos = 1
            elif direction == 'sell':
                self.h_pos = -1
            
            self.last_entry_price = entry_price
            self.last_sl_price = sl_price
            self.last_tp_price = tp_price
            self.last_direction = direction
            self.last_quantity = quantity
            self.entry_signal = entry_signal
            
            print(f"Position set: h_pos = {self.h_pos} for {direction} trade")
            print(f"  Entry: ${entry_price}, SL: ${sl_price}, TP: ${tp_price}")
        except Exception as e:
            print(f"Error setting position: {e}")
    
    def clear_position(self):
        """Clear position status when trade is closed"""
        try:
            # self.df = pd.read_csv(rf"C:\Users\vaibh\OneDrive\Desktop\alhem_2\trading_binance\Delta_Final.csv")
            # self.df = pd.read_csv(r"Delta_Final.csv")
            self.df = delta_client.fetch_data_binance()
            # self.df = calculate_signals(df)
            self.df = calculate_signals(self.df)
            self.h_pos = 0
            self.entry_signal = None
            self.position_order_id = None
            self.last_tp_price = None
            self.last_sl_price = None
            self.last_entry_price = None
            self.last_direction = None
            self.last_quantity = None
            print("Position cleared: h_pos = 0")
        except Exception as e:
            print(f"Error clearing position: {e}")

    def update_trade_result(self, result, is_fake_trigger=False):
        try:
            import time
            self.last_trade_result = result
            current_time = time.time()
            
            if result == 'win':
                # Handle post-martingale elevation logic
                if self.current_level > 0:
                    # Martingale cycle completed
                    if self.double_trigger_occurred_this_cycle:
                        # Double trigger happened, next trade starts at 20x
                        self.start_elevated_after_martingale = True
                        self.double_trigger_occurred_this_cycle = False
                        logger.info("Martingale with double trigger! Next at 20x")
                    else:
                        # Normal martingale completion, return to base
                        self.start_elevated_after_martingale = False
                        logger.info("Martingale complete, back to base")
                elif self.current_level == 0 and self.start_elevated_after_martingale:
                    # We're at elevated start (20x), next win returns to base (10x)
                    self.start_elevated_after_martingale = False
                    logger.info("Elevated cycle complete, back to 10x")
                
                # Reset all tracking
                self.current_level = 0
                self.last_loss_timestamp = None
                self.last_loss_type = None
                self.pending_second_increment = False
                self.skip_fake_losses_this_cycle = False
                print(f"Trade won! Reset to L0, leverage: {self.get_leverage()}x")
                logger.info(f"WIN: Reset to L0")
                    
            elif result == 'loss':
                loss_type = 'fake' if is_fake_trigger else 'sl'
                logger.info(f"LOSS detected: type={loss_type}, level={self.current_level}")
                
                # Skip fake losses only if double trigger already occurred AND we're at max level
                if is_fake_trigger and self.skip_fake_losses_this_cycle and self.current_level >= self.max_levels - 1:
                    logger.info(f"SKIPPING fake loss - double trigger already occurred and at max level")
                    print(f"Fake loss skipped (double trigger protection active)")
                    return
                
                # Check for double trigger
                if self.last_loss_timestamp is not None:
                    time_diff = current_time - self.last_loss_timestamp
                    
                    if time_diff <= DOUBLE_TRIGGER_WINDOW and self.last_loss_type != loss_type:
                        print(f"DOUBLE TRIGGER! {self.last_loss_type.upper()} + {loss_type.upper()}")
                        logger.info(f"Double trigger detected")

                        # Check if we're at max level - if so, reset everything
                        if self.current_level >= self.max_levels - 1:
                            if self.double_trigger_occurred_this_cycle:
                                logger.info(f"Max level reached with double trigger in cycle, resetting to level 1 (20x)")
                                self.current_level = 1
                            else:
                                logger.info(f"Max level reached without double trigger, resetting to 0")
                                self.current_level = 0
                            self.pending_second_increment = False
                            self.start_elevated_after_martingale = False
                            self.double_trigger_occurred_this_cycle = False
                            self.skip_fake_losses_this_cycle = False
                        else:
                            # New behavior: ignore extra increment caused by fake-loss when SL also occurs
                            # Do NOT change current_level here. We keep only the single increment effect overall
                            # and defer recovery via post-cycle elevation.
                            self.pending_second_increment = False
                            self.double_trigger_occurred_this_cycle = True  # activate elevation after martingale cycle
                            self.skip_fake_losses_this_cycle = True

                        # Clear tracking
                        self.last_loss_timestamp = None
                        self.last_loss_type = None
                        logger.info(f"DOUBLE TRIGGER handled with NO additional level bump; post-cycle elevation queued")
                        return
                
                # Normal increment
                if self.current_level >= self.max_levels - 1:
                    # logger.info(f"Max level reached, resetting to 0")
                    # self.current_level = 0
                    if self.double_trigger_occurred_this_cycle:
                        logger.info(f"Max level reached with double trigger in cycle, resetting to level 1 (20x)")
                        self.current_level = 1
                    else:
                        logger.info(f"Max level reached without double trigger, resetting to 0")
                        self.current_level = 0
                    self.pending_second_increment = False
                    self.start_elevated_after_martingale = False
                    self.double_trigger_occurred_this_cycle = False
                    self.skip_fake_losses_this_cycle = False
                else:
                    self.current_level += 1
                    logger.info(f"LOSS ({loss_type}): Level {self.current_level}")
                
                self.last_loss_timestamp = current_time
                self.last_loss_type = loss_type
                    
            # Add comprehensive logging
            logger.info(f"Status: Level={self.current_level}, Elevated={self.start_elevated_after_martingale}, Pending={self.pending_second_increment}, DoubleTrigger={self.double_trigger_occurred_this_cycle}")
            print(f"Leverage: {self.get_leverage()}x, Level: {self.current_level}")
            
        except Exception as e:
            logger.error(f"Error in update_trade_result: {e}")

    def check_opposite_signal(self):
        """Check for opposite signal, close current position, and re-enter in opposite direction"""
        try:
            import time  # Import at function level to avoid issues
            
            # Get fresh data
            df = delta_client.fetch_data_binance()
            df = calculate_signals(df)
            self.df = df  # Store in self.df for later use
            
            latest_candle = df.iloc[-1]
            current_signal = int(latest_candle['Signal_Final'])     
            
            if self.entry_signal is None:
                return False

            if current_signal == 0:
                return False  # Zero signal is not an opposite signal

            # Check for true opposite signals (different signs, both non-zero)
            if self.h_pos != 0:
                if (self.entry_signal == 2 and current_signal == -2) or \
                (self.entry_signal == -2 and current_signal == 2):    
                
                    logger.info(f" OPPOSITE SIGNAL DETECTED! Entry: {self.entry_signal}, Current: {current_signal}")
                    
                    # CRITICAL: Check if TP/SL already hit before attempting close
                    global bracket_tp_order_id, bracket_sl_order_id
                    try:
                        tp_check = delta_client.get_order_status(order_id=bracket_tp_order_id)
                        sl_check = delta_client.get_order_status(order_id=bracket_sl_order_id)
                        
                        if tp_check and sl_check:
                            tp_state = tp_check['result']['state']
                            sl_state = sl_check['result']['state']
                            
                            if tp_state in ['closed', 'filled'] or sl_state in ['closed', 'filled']:
                                logger.info(f"TP/SL already hit (TP: {tp_state}, SL: {sl_state}), skipping opposite signal close")
                                self.clear_position()
                                return False
                    except Exception as check_e:
                        logger.warning(f"Could not check TP/SL status: {check_e}, proceeding with close")
                    
                    # Store old position details before closing
                    old_direction = self.last_direction
                    old_quantity = self.last_quantity
                    balance_before = self.balance_before
                    
                    # Determine new direction for re-entry
                    new_direction = "buy" if current_signal > 0 else "sell"
                    opposite_side_for_close = "sell" if old_direction == "buy" else "buy"
                    
                    logger.info(f"Closing {old_direction.upper()} position with {opposite_side_for_close.upper()} order")
                    logger.info(f"Will re-enter with {new_direction.upper()} position after closing")
                    
                    # STEP 1: Close existing position with retry logic
                    max_retries = 3
                    retry_delay = 0.5
                    close_order_success = False
                    
                    for attempt in range(max_retries):
                        try:
                            current_price = delta_client.get_market_price()
                            logger.info(f"Close attempt {attempt + 1}: Placing {opposite_side_for_close} order at ${current_price}, qty: {old_quantity}")
                            
                            close_res = delta_client.place_order_market(
                                side=str(opposite_side_for_close), 
                                size=int(old_quantity)
                            )
                            
                            if close_res and (close_res.get('state') in ['closed', 'filled'] or close_res.get('id')):
                                logger.info(f" Close order successful on attempt {attempt + 1}: {close_res.get('id')}")
                                close_order_success = True
                                break
                            else:
                                logger.warning(f"Close attempt {attempt + 1} returned unexpected response")
                                if attempt < max_retries - 1:
                                    time.sleep(retry_delay)
                                    
                        except Exception as close_e:
                            logger.error(f"Close attempt {attempt + 1} failed: {close_e}")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                    
                    if not close_order_success:
                        logger.error(" Failed to close position after all retries, aborting re-entry")
                        self.clear_position()
                        return False
                    
                    # Update position status
                    self.h_pos = 0
                    reset_trade_tracking()
                    set_candle_exit_time(time=df.iloc[-1]['time'])
                    
                    # Calculate loss/gain from closed position
                    balance_after_close = float(delta_client.get_usd_balance())
                    loss_amount = float(balance_before) - float(balance_after_close)
                    logger.info(f"Closed position P&L: ${loss_amount:.2f} (negative = profit)")
                    
                    # Add to global fake_loss_amount if it's a loss
                    global fake_loss_amount
                    if loss_amount > 0:
                        fake_loss_amount += loss_amount
                        print(f"Loss from opposite signal: ${loss_amount:.2f}")
                        print(f"Total fake loss: ${fake_loss_amount:.2f}")
                        logger.info(f"Total fake loss :${fake_loss_amount:.2f}")
                        
                        if fake_loss_amount >= fake_loss_amount_maxlimit:
                            logger.info(f"Fake loss limit reached: ${fake_loss_amount:.2f} >= ${fake_loss_amount_maxlimit}")
                            martingale_manager.update_trade_result('loss', is_fake_trigger=True)
                            fake_loss_amount = 0
                            print(f"New leverage: {martingale_manager.get_leverage()}x")
                    
                    logger.info(f"P&L: ${loss_amount:.2f}, Total fake loss: ${fake_loss_amount:.2f}/{fake_loss_amount_maxlimit}, Level: {self.current_level}")
                    
                    # Brief pause to let exchange update
                    time.sleep(1)

                    # Double trigger increment is now handled directly in update_trade_result
                    
                    # STEP 2: Re-enter with new position in opposite direction
                    try:
                        logger.info(f"RE-ENTERING with {new_direction.upper()} position (signal: {current_signal})")
                        
                        # Get fresh market data for re-entry
                        df_reentry = delta_client.fetch_data_binance()
                        df_reentry = calculate_signals(df_reentry)
                        
                        i = len(df_reentry) - 1
                        row = df_reentry.iloc[i]
                        prev_row = df_reentry.iloc[i-1]
                        second_last_row = df_reentry.iloc[i-2] if i > 1 else prev_row
                        
                        # Calculate entry parameters
                        entry_price = int(delta_client.get_market_price())
                        sl, tp = risk_manager.calculate_sl_tp(entry_price, new_direction, prev_row, second_last_row)
                        sl = float(sl)
                        tp = float(tp)
                        
                        # Calculate trade size with current leverage
                        current_leverage = martingale_manager.get_leverage()
                        trade_amount = delta_client.calculate_trade_size(entry_price, current_leverage, base_capital)
                        
                        # Set leverage
                        delta_client.set_leverage(current_leverage)
                        
                        logger.info(f"Re-entry: {new_direction.upper()} at ${entry_price}, SL: ${sl}, TP: ${tp}, Qty: {trade_amount}, Leverage: {current_leverage}x")
                        
                        # Update current_candle_time for fake trade detection
                        delta_client.current_candle_time = int(df_reentry.iloc[-1]['time'])
                        
                        # Place market order for re-entry
                        market_order = delta_client.place_order_market(new_direction, trade_amount)
                        set_candle_entry_time(time=df_reentry.iloc[-1]['time'])
                        logger.info(f"Re-entry market order response: {market_order}")
                        
                        if market_order:
                            self.balance_before = delta_client.get_usd_balance()
                            self.h_pos = int(current_signal / 2)
                            
                            logger.info(f"Re-entry market order placed: {market_order.get('id')}")
                            set_trade_tracking(current_signal, new_direction, entry_price, int(df_reentry.iloc[-1]['time']))
                            set_flag_fake_trade(1)
                            
                            # Place bracket order for SL/TP
                            try:
                                logger.info(f"Placing bracket order - SL: ${sl}, TP: ${tp}")
                                bracket_order_res = delta_client.place_order_bracket(
                                    side=new_direction,
                                    size=trade_amount,
                                    entry_price=entry_price,
                                    stop_price=sl,
                                    take_profit_price=tp
                                )
                                
                                if not bracket_order_res or not bracket_order_res.get('success', False):
                                    raise Exception("Bracket order placement failed")
                                    
                            except Exception as bracket_e:
                                logger.error(f"Initial bracket order failed: {bracket_e}")
                                time.sleep(1)
                                
                                # Adjust SL/TP and retry
                                if new_direction.lower() == 'buy':
                                    sl = round(sl - 7, 2)
                                    tp = round(tp + 5, 2)
                                else:
                                    sl = round(sl + 7, 2)
                                    tp = round(tp - 5, 2)
                                
                                try:
                                    logger.info(f"Retry bracket order - SL: ${sl}, TP: ${tp}")
                                    bracket_order_res = delta_client.place_order_bracket(
                                        side=new_direction,
                                        size=trade_amount,
                                        entry_price=entry_price,
                                        stop_price=sl,
                                        take_profit_price=tp
                                    )
                                except Exception as bracket_e2:
                                    logger.error(f"Fallback bracket order failed: {bracket_e2}")
                                    # Close position if bracket order fails
                                    close_side = "sell" if new_direction == "buy" else "buy"
                                    delta_client.place_order_market(side=close_side, size=trade_amount)
                                    self.clear_position()
                                    reset_candle_entry_exit_time()
                                    return True
                            
                            # Extract bracket order IDs and update globals
                            try:
                                bracket_tp_order_id = bracket_order_res['result']['take_profit_order']['id']
                                bracket_sl_order_id = bracket_order_res['result']['stop_loss_order']['id']
                            except:
                                try:
                                    bracket_tp_order_id = bracket_order_res['take_profit_order']['id']
                                    bracket_sl_order_id = bracket_order_res['stop_loss_order']['id']
                                except Exception as id_e:
                                    logger.error(f"Could not extract bracket order IDs: {id_e}")
                            
                            logger.info(f"Bracket orders placed - TP ID: {bracket_tp_order_id}, SL ID: {bracket_sl_order_id}")
                            
                            # Double trigger increment is now handled directly in update_trade_result
                            
                            # Set position status
                            signal_for_position = 2 if new_direction == "buy" else -2
                            self.set_position(new_direction, entry_price, sl, tp, trade_amount, signal_for_position)
                            
                            logger.info(f"RE-ENTRY COMPLETE: {new_direction.upper()} position established")
                            print(f"Opposite signal processed: Closed old position and re-entered {new_direction.upper()}")
                            
                        else:
                            logger.error("Re-entry market order failed")
                            reset_trade_tracking()
                            
                    except Exception as reentry_e:
                        logger.error(f"Re-entry failed: {reentry_e}")
                        self.clear_position()
                        reset_candle_entry_exit_time()
                    
                    return True
                
                return False
            
        except Exception as e:
            logger.error(f"Error in check_opposite_signal: {e}")
            print(f"Error checking opposite signal: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def monitor_and_close_position(self):
        # global double_trigger_flag,pending_double_trigger
        try:
            if self.h_pos == 0:
                return False

            print(f"  Checking position status...")
            print(f"  Direction: {self.last_direction}")
            print(f"  Entry: ${self.last_entry_price}")
            print(f"  SL: ${self.last_sl_price}")
            print(f"  TP: ${self.last_tp_price}")
            print(f"  Quantity: {self.last_quantity}")

            try:
                # Fetch updated order status
                tp_res = delta_client.get_order_status(order_id=bracket_tp_order_id)
                current_bracket_state_tp = tp_res['result']['state']

                sl_res = delta_client.get_order_status(order_id=bracket_sl_order_id)
                current_bracket_state_sl = sl_res['result']['state']

                # Check if either TP or SL is closed
                if current_bracket_state_tp == "closed" or current_bracket_state_sl == "closed":
                    print(f"Order closed. TP state: {current_bracket_state_tp}, SL state: {current_bracket_state_sl}")

                    if current_bracket_state_tp == "closed":
                        logger.info(f"we have won the trade")
                        # NEW: Use is_fake_trigger=False for regular TP/SL wins
                        self.update_trade_result('win', is_fake_trigger=False)
                        logger.info(f"current martingale level is {martingale_manager.current_level} and the current fake loss is {fake_loss_amount}")
                    elif current_bracket_state_sl == "closed":
                        logger.info(f"we have lost the trade")
                        logger.info(f"current martingale level is {martingale_manager.current_level} and the current fake loss is {fake_loss_amount}")
                        # NEW: Use is_fake_trigger=False for regular SL losses (this sets double_trigger_flag=True)
                        self.update_trade_result('loss', is_fake_trigger=False)

                    self.clear_position()
                    set_candle_exit_time(self.df.iloc[-1]['time'])

                    # print(" Sleeping for one candle seconds to avoid re-entry in same candle...")
                    if check_entry_exit_same_candle_condition():
                        logger.info(f"here we are going to sleep for {RENTRY_TIME_BINANCE} since the entry and exit time is the same")
                        time.sleep(RENTRY_TIME_BINANCE)
                    else:
                        logger.info(f"here we are not going to sleep since the entry and exit time is not same")
                        time.sleep(0.5)
                    reset_candle_entry_exit_time()
                    print(" Ready for next trade opportunity")
                    return True

                # Still open
                print(f" Order still open... TP state: {current_bracket_state_tp}, SL state: {current_bracket_state_sl}")
                return False

            except Exception as e:
                print(f"Error checking order status: {e}")
                return False

        except Exception as e:
            print(f" Error in monitor_and_close_position: {e}")
            return False
        
try:
    rf = RangeFilter()
    bsrsi = RSIBuySellIndicator()
    Grsi = RSIGainzy()
    delta_client = DeltaBroker()
    delta_client.connect()
    
    # risk_manager = RiskManager(SL_BUFFER_POINTS, TP_PERCENT, INITIAL_CAPITAL)
    risk_manager = RiskManager(DELTA_SL_BUFFER_POINTS,DELTA_TP_PERCENT,initial_capital=DELTA_INITIAL_CAPITAL)
    # base_capital = INITIAL_CAPITAL
    base_capital = DELTA_INITIAL_CAPITAL
    base_leverage = DELTA_BASE_LEVERAGE
    martingale_manager = MartingaleManager(base_capital, base_leverage)
    
except Exception as e:
    print(f"Error initializing components: {e}")
    exit(1)


def format_trade_data(direction, entry_price, sl, tp, trade_amount, strategy_type, martingale_level, leverage):
    """Format trade data for logging"""
    try:
        return {
            'timestamp': datetime.now().isoformat(),
            'symbol': 'ETHUSD',
            'direction': direction,
            'entry_price': entry_price,
            'sl': sl,
            'tp': tp,
            'amount': trade_amount,
            'strategy': strategy_type,
            'martingale_level': martingale_level,
            'leverage': leverage
        }
    except Exception as e:
        print(f"Error formatting trade data: {e}")
        return {}
    
def set_candle_entry_time(time):
    global candle_entry
    candle_entry = time

def set_candle_exit_time(time):
    global candle_exit
    candle_exit = time

def reset_candle_entry_exit_time():
    global candle_entry,candle_exit
    candle_entry = None
    candle_exit  = None

def check_entry_exit_same_candle_condition():
    # if this value is true then we need to put the function in sleep
    global candle_entry,candle_exit
    if candle_entry == candle_exit:
        reset_candle_entry_exit_time()
        return True
    else:
        reset_candle_entry_exit_time()
        return False

def set_flag_fake_trade(flag):
    # here the value of 0/1 will be passed
    global fake_trade_flag
    fake_trade_flag = int(flag)

def fake_trade_loss_checker(df, current_time):
    global fake_loss_amount, trade_taken_time, trade_taken_signal, trade_taken_price, trade_taken_direction
    # global double_trigger_flag,pending_double_trigger

    try:
        start_balance = float(delta_client.get_usd_balance())

        if martingale_manager.h_pos != 0:
            print("Monitoring for potential fake signal...")

            while True:
                # df = delta_client.fetch_data_binance()  # get real-time data from Binance
                # df = delta_client.fetch_data()
                df = delta_client.fetch_data_binance()
                df = calculate_signals(df)
                df.to_csv('Delta_Final.csv')

                last_row = df.iloc[-1]
                last_time = int(last_row['time'])

                print(f"Last DF time: {last_time}, Current candle time: {current_time}")

                if last_time >= current_time + 30:
                    print("New candle detected, now evaluating signal reversal...")

                    second_last_candle = df.iloc[-2]
                    second_last_signal = second_last_candle['Signal_Final']
                    second_last_signal_time = second_last_candle['Timestamp']
                    last_candle = df.iloc[-1]
                    last_signal = last_candle['Signal_Final']
                    print(f"Second last signal: {second_last_signal}")

                    if second_last_signal == 0:
                        print("FAKE SIGNAL DETECTED!")
                        print(f"  Trade taken at: {trade_taken_time}")
                        print(f"  Original signal: {trade_taken_signal}")
                        logger.info(f"fake signal is detected trade taken at {trade_taken_time} with original signal {trade_taken_signal} and the second last signal time is {second_last_signal_time}")
                        logger.info(f"last signal is {last_signal} , second last signal is {second_last_signal}")

                        # Close the position
                        close_position_on_fake_signal()

                        # Calculate and log the fake loss
                        current_balance = float(delta_client.get_usd_balance())
                        fake_loss = start_balance - current_balance
                        fake_loss_amount += fake_loss

                        print(f"Calculated fake loss: ${fake_loss:.2f}")
                        print(f"Total fake loss amount: ${fake_loss_amount:.2f}")
                        logger.info(f"Fake Loss amount is ${fake_loss_amount}") # code added
                        print(f"Max limit: ${fake_loss_amount_maxlimit}")

                        # NEW: Use double-trigger prevention system
                        if fake_loss_amount >= fake_loss_amount_maxlimit:
                            print("FAKE LOSS LIMIT REACHED!")
                            martingale_manager.update_trade_result('loss', is_fake_trigger=True)
                            fake_loss_amount = 0  # Reset fake loss tracking
                            print(f"  New leverage: {martingale_manager.get_leverage()}x")

                        # Reset trade tracking
                        reset_trade_tracking()
                        logger.info(f"the current martingale level is {martingale_manager.current_level}")
                        import time
                        # print(f"sleeping for one candle seconds to prevent re-entry")
                        if check_entry_exit_same_candle_condition():
                            logger.info(f"here we are going to sleep for {RENTRY_TIME_BINANCE} since the entry and exit time is the same")
                            time.sleep(RENTRY_TIME_BINANCE)
                        else:
                            logger.info(f"here we are not going to sleep since the entry and exit time is not same")
                            time.sleep(0.5)
                        reset_candle_entry_exit_time()
                        return True
                    else:
                        print("Signal is still valid. No fake trade.")
                        return False
                else:
                    print(" Waiting for new candle... Sleeping 2 seconds.")
                    import time
                    time.sleep(2) # important 
                

    except Exception as e:
        print(f"Error in fake_trade_loss_checker: {e}")
        return False

def close_position_on_fake_signal():
    # global double_trigger_flag,pending_double_trigger
    """Close position by placing opposite order of same size"""
    try:
        if martingale_manager.h_pos != 0:
            # Determine opposite direction
            if martingale_manager.last_direction == "buy":
                opposite_direction = "sell"
            else:
                opposite_direction = "buy"
            
            print(f"  Closing position due to fake signal...")
            print(f"  Original direction: {martingale_manager.last_direction}")
            print(f"  Closing with: {opposite_direction}")
            print(f"  Size: {martingale_manager.last_quantity}")
            
            # Place opposite market order to close position
            current_price = delta_client.get_market_price()
            logger.info(f"this is a fake order so the market order will be placed to close it , the current price is {current_price}")
            # here i will add the logic for not closing if the tp/sl got hit
            tp_res = delta_client.get_order_status(order_id=bracket_tp_order_id)
            current_bracket_state_tp = tp_res['result']['state']

            sl_res = delta_client.get_order_status(order_id=bracket_sl_order_id)
            current_bracket_state_sl = sl_res['result']['state']
            # logger.info(f"the current sl status is {current_bracket_state_sl} and the current tp status is {current_bracket_state_tp}")
            if current_bracket_state_sl == "FILLED" or current_bracket_state_tp == "FILLED" or current_bracket_state_sl == "closed" or current_bracket_state_tp == "closed": # this logic is correct
                logger.info(f"the sl / tp was hitted before the execution so no closing market order , sl status : {current_bracket_state_sl} , tp status : {current_bracket_state_tp}")
            else:
                logger.info(f"the sl / tp was not hit so we are closing market order , sl status : {current_bracket_state_sl} , tp status : {current_bracket_state_tp}")
                df = delta_client.fetch_data_binance()
                df = calculate_signals(df)
                df.to_csv('Delta_Final.csv')
                close_order = delta_client.place_order_market(
                    side=opposite_direction, 
                    size=martingale_manager.last_quantity
                )
                set_candle_exit_time(time=df.iloc[-1]['time'])
                reset_candle_entry_exit_time()
            
            if close_order:
                print(f"Position closed successfully: {close_order.get('id')}")
                martingale_manager.clear_position()
            else:
                print("Failed to close position")
                
    except Exception as e:
        print(f"Error closing position on fake signal: {e}")

def set_trade_tracking(signal, direction, entry_price, trade_time):
    """Set tracking variables when a trade is taken"""
    global trade_taken_time, trade_taken_signal, trade_taken_price, trade_taken_direction
    
    trade_taken_time = trade_time
    trade_taken_signal = signal
    trade_taken_price = entry_price
    trade_taken_direction = direction
    
    print(f"  Trade tracking set:")
    print(f"  Time: {trade_taken_time}")
    print(f"  Signal: {trade_taken_signal}")
    print(f"  Price: ${trade_taken_price}")
    print(f"  Direction: {trade_taken_direction}")

def reset_trade_tracking():
    """Reset all trade tracking variables"""
    global trade_taken_time, trade_taken_signal, trade_taken_price, trade_taken_direction
    
    trade_taken_time = None
    trade_taken_signal = 0
    trade_taken_price = 0
    trade_taken_direction = None
    print(" Trade tracking reset")

def is_time_in_range_ist():
    from datetime import datetime, time
    import pytz
    ist = pytz.timezone("Asia/Kolkata")
    current_time = datetime.now(ist).time()
    start_time = time(START_HOUR, START_MINUTE)
    end_time = time(END_HOUR, END_MINUTE)
    return start_time <= current_time <= end_time

def calculate_heiken_ashi_testnet(df):
    try:
        # print("heiken-ashi is being calculated.")
        # Ensure required columns exist
        required_cols = {'Open', 'High', 'Low', 'Close'}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"DataFrame must contain the following columns: {required_cols}")

        # Create new columns for Heiken-Ashi
        df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        df['HA_Open'] = 0.0
        df['HA_High'] = 0.0
        df['HA_Low'] = 0.0

        # Initialize first HA_Open
        df.at[df.index[0], 'HA_Open'] = (df.at[df.index[0], 'Open'] + df.at[df.index[0], 'Close']) / 2

        # Calculate remaining Heiken-Ashi values
        for i in range(1, len(df)):
            prev_ha_open = df.at[df.index[i - 1], 'HA_Open']
            prev_ha_close = df.at[df.index[i - 1], 'HA_Close']

            df.at[df.index[i], 'HA_Open'] = (prev_ha_open + prev_ha_close) / 2
            df.at[df.index[i], 'HA_High'] = max(
                df.at[df.index[i], 'High'],
                df.at[df.index[i], 'HA_Open'],
                df.at[df.index[i], 'HA_Close']
            )
            df.at[df.index[i], 'HA_Low'] = min(
                df.at[df.index[i], 'Low'],
                df.at[df.index[i], 'HA_Open'],
                df.at[df.index[i], 'HA_Close']
            )

        # Replace original OHLC columns with Heiken-Ashi values
        df.drop(columns=['Open', 'High', 'Low', 'Close'], inplace=True)
        df.rename(columns={
            'HA_Open': 'Open',
            'HA_High': 'High',
            'HA_Low': 'Low',
            'HA_Close': 'Close'
        }, inplace=True)
        return df
        # print("DONE")
    except Exception as e:
        print(f"Error in heiken-ashi calculation : {e}")

def calculate_takeprofit( entry_price, side):
    """Calculate take profit based on risk-reward ratio"""
    try:
        if side == "buy":
            tp = entry_price * (1+DELTA_TP_PERCENT)  # 2% profit
        else:  # sell
            tp = entry_price * (1-DELTA_TP_PERCENT)  # 2% profit
        
        print(f"Calculated take profit for {side}: {tp}")
        return tp
        
    except Exception as e:
        print(f"Error in calculate_takeprofit: {e}")
        return None

def calculate_signals(df):
    try:
        from module.rf import RangeFilter
        from module.ib_indicator import calculate_inside_ib_box
        from module.rsi_buy_sell import RSIBuySellIndicator
        rf = RangeFilter()
        bsrsi = RSIBuySellIndicator()
        
        df.rename(columns={'close':'Close','open':'Open','high':'High','low':'Low','volume':'Volume'},inplace=True)
        if int(MASTER_HEIKEN_CHOICE)==1:
            calculate_heiken_ashi(df)
        # df = rf.run_filter(df)
        df = rf.run_filter(df)
        df.rename(columns={'Close':'close','Open':'open','High':'high','Low':'low','Volume':'volume'},inplace=True)
        df['rsi'],df['rsi_buy'],df['rsi_sell'] = bsrsi.generate_signals(df['close'])
        df = calculate_inside_ib_box(df)
        columns_to_drop = [
            'RF_UpperBand', 'RF_LowerBand','RF_Trend',
            'IsIB', 'BoxHigh', 'BoxLow', 'BarColor','rsi'
        ]
        df = df.drop(columns=columns_to_drop)

        df = df.tail(200)
        df['Signal_Final'] = 0

        # Configuration variable for RF signal lookback period
        N_CANDLE_LOOKBACK = 5

        # Initialize signal tracking variables
        last_rf_buy_signal = False
        last_rf_sell_signal = False
        rf_signal_candle = -1
        rf_used = False

        # Initialize IB Arrow signal tracking variables
        last_green_arrow = False
        last_red_arrow = False
        arrow_signal_candle = -1
        arrow_used = False

        # Initialize RSI signal tracking variables
        last_rsi_buy_signal = False
        last_rsi_sell_signal = False
        rsi_signal_candle = -1
        rsi_used = False

        for i in range(len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i - 1] if i > 0 else None

            # Detect new RF signals (transition from 0 to 1)
            current_rf_buy = row['RF_BuySignal'] == 1
            current_rf_sell = row['RF_SellSignal'] == 1

            new_rf_buy = current_rf_buy and (prev_row is None or prev_row['RF_BuySignal'] != 1)
            new_rf_sell = current_rf_sell and (prev_row is None or prev_row['RF_SellSignal'] != 1)

            # Detect new IB Arrow signals
            new_green_arrow = row['GreenArrow'] == 1 and (prev_row is None or prev_row['GreenArrow'] != 1)
            new_red_arrow = row['RedArrow'] == 1 and (prev_row is None or prev_row['RedArrow'] != 1)

            # Detect new RSI signals
            new_rsi_buy = row['rsi_buy'] == 1 and (prev_row is None or prev_row['rsi_buy'] != 1)
            new_rsi_sell = row['rsi_sell'] == 1 and (prev_row is None or prev_row['rsi_sell'] != 1)

            # Update RF signal tracking
            if new_rf_buy:
                last_rf_buy_signal = True
                last_rf_sell_signal = False
                rf_signal_candle = i
                rf_used = False
            elif new_rf_sell:
                last_rf_sell_signal = True
                last_rf_buy_signal = False
                rf_signal_candle = i
                rf_used = False

            # Update IB Arrow signal tracking
            if new_green_arrow:
                last_green_arrow = True
                last_red_arrow = False
                arrow_signal_candle = i
                arrow_used = False
            elif new_red_arrow:
                last_red_arrow = True
                last_green_arrow = False
                arrow_signal_candle = i
                arrow_used = False

            # Update RSI signal tracking
            if new_rsi_buy:
                last_rsi_buy_signal = True
                last_rsi_sell_signal = False
                rsi_signal_candle = i
                rsi_used = False
            elif new_rsi_sell:
                last_rsi_sell_signal = True
                last_rsi_buy_signal = False
                rsi_signal_candle = i
                rsi_used = False

            # Reset signals if they're older than specified timeframes and not used
            # RF signals valid for N_CANDLE_LOOKBACK candles until IB trigger
            if (i - rf_signal_candle) > N_CANDLE_LOOKBACK and (last_rf_buy_signal or last_rf_sell_signal) and not rf_used:
                last_rf_buy_signal = False
                last_rf_sell_signal = False
                rf_used = False

            # IB Arrow signals valid for 1 candle for RF confirmation
            if (i - arrow_signal_candle) > 1 and (last_green_arrow or last_red_arrow) and not arrow_used:
                last_green_arrow = False
                last_red_arrow = False
                arrow_used = False

            # RSI signals valid for 1 candle for IB confirmation
            if (i - rsi_signal_candle) > 1 and (last_rsi_buy_signal or last_rsi_sell_signal) and not rsi_used:
                last_rsi_buy_signal = False
                last_rsi_sell_signal = False
                rsi_used = False

            signal = 0

            # CONDITION 4: IB and RF in same candle (Highest Priority)
            if new_rf_buy and new_green_arrow and not rf_used and not arrow_used:
                signal = 2  # RF + IB_Box buy signal (same candle)
                rf_used = True
                arrow_used = True
                last_rf_buy_signal = False
                last_green_arrow = False
                # print(f"RF + IB_Box BUY signal triggered at candle {i} (same candle)")
            elif new_rf_sell and new_red_arrow and not rf_used and not arrow_used:
                signal = -2  # RF + IB_Box sell signal (same candle)
                rf_used = True
                arrow_used = True
                last_rf_sell_signal = False
                last_red_arrow = False
                # print(f"RF + IB_Box SELL signal triggered at candle {i} (same candle)")
            
            # CONDITION 1: RF signal first, then IB box after few candles
            elif last_rf_buy_signal and not rf_used and new_green_arrow:
                signal = 2  # RF + IB_Box buy signal
                rf_used = True
                arrow_used = True
                last_rf_buy_signal = False
                last_green_arrow = False
                # print(f"RF + IB_Box BUY signal triggered at candle {i} (RF at {rf_signal_candle}, IB at {i})")
            elif last_rf_sell_signal and not rf_used and new_red_arrow:
                signal = -2  # RF + IB_Box sell signal
                rf_used = True
                arrow_used = True
                last_rf_sell_signal = False
                last_red_arrow = False
                # print(f"RF + IB_Box SELL signal triggered at candle {i} (RF at {rf_signal_candle}, IB at {i})")

            # CONDITION 2: IB box first, then RF signal on immediate next candle
            elif last_green_arrow and not arrow_used and new_rf_buy and (i - arrow_signal_candle) == 1:
                signal = 2  # RF + IB_Box buy signal
                arrow_used = True
                rf_used = True
                last_green_arrow = False
                last_rf_buy_signal = False
                # print(f"RF + IB_Box BUY signal triggered at candle {i} (IB at {arrow_signal_candle}, RF at {i})")
            elif last_red_arrow and not arrow_used and new_rf_sell and (i - arrow_signal_candle) == 1:
                signal = -2  # RF + IB_Box sell signal
                arrow_used = True
                rf_used = True
                last_red_arrow = False
                last_rf_sell_signal = False
                # print(f"RF + IB_Box SELL signal triggered at candle {i} (IB at {arrow_signal_candle}, RF at {i})")

            # CONDITION 5: RSI and IB in same candle
            elif signal == 0 and new_rsi_buy and new_green_arrow and not rsi_used:
                signal = 4  # RSI + IB_Box buy signal (same candle)
                rsi_used = True
                last_rsi_buy_signal = False
                # print(f"RSI + IB_Box BUY signal triggered at candle {i} (same candle)")
            elif signal == 0 and new_rsi_sell and new_red_arrow and not rsi_used:
                signal = -4  # RSI + IB_Box sell signal (same candle)
                rsi_used = True
                last_rsi_sell_signal = False
                # print(f"RSI + IB_Box SELL signal triggered at candle {i} (same candle)")

            # CONDITION 3: RSI signal first, then IB on immediate next candle
            elif signal == 0 and last_rsi_buy_signal and not rsi_used and new_green_arrow and (i - rsi_signal_candle) == 1:
                signal = 4  # RSI + IB_Box buy signal
                rsi_used = True
                last_rsi_buy_signal = False
                # print(f"RSI + IB_Box BUY signal triggered at candle {i} (RSI at {rsi_signal_candle}, IB at {i})")
            elif signal == 0 and last_rsi_sell_signal and not rsi_used and new_red_arrow and (i - rsi_signal_candle) == 1:
                signal = -4  # RSI + IB_Box sell signal
                rsi_used = True
                last_rsi_sell_signal = False
                # print(f"RSI + IB_Box SELL signal triggered at candle {i} (RSI at {rsi_signal_candle}, IB at {i})")

            # Assign the final signal
            df.iat[i, df.columns.get_loc('Signal_Final')] = signal

        df.to_csv('Delta_Final.csv')
        # df.to_csv("data/Delta_Final_main.csv")
        return df
    except Exception as e:
        print(f"Error occured in calculating the signal : {e}")

if __name__ == "__main__":
    # res = delta_client.get_usd_balance()
    # print(res)
    # exit(0)
    try:
        print("Starting Delta Exchange Trading Bot with Bracket Orders")
        print(f"Initial Capital: Rs{base_capital}")
        print(f"Base Leverage: {base_leverage}x")
        print(f"Symbol: {DELTA_SYMBOL}")
        print(f"Interval: {DELTA_INTERVAL}")
        print(f"TP PERCENT: {DELTA_TP_PERCENT}")
        print(f"SL BUFFER POINTS: {DELTA_SL_BUFFER_POINTS}")
        logger.info(f"The trading bot has started with initial capital {base_capital} and initial leverage {base_leverage} and symbol {DELTA_SYMBOL} and interval {DELTA_INTERVAL} with tp percent {DELTA_TP_PERCENT} and sl points {DELTA_SL_BUFFER_POINTS} current fake loss amount is {fake_loss_amount} and current martingale level is {martingale_manager.current_level} with fake loss threshold {DELTA_FAKE_LOSS_MAX_AMOUNT} on timeframe {BYBIT_INTERVAL} with heikan-ashi status as {MASTER_HEIKEN_CHOICE}")
        print("=" * 50)
        
        # Set initial leverage
        delta_client.set_leverage(base_leverage)
        
    except Exception as e:
        print(f"Error in initial setup: {e}")
        exit(1)
    
    while True:
        try:
            print("\n --- New Trading Cycle ---")
            df_check = delta_client.fetch_data_binance()

            # Validate fetched data
            if df_check is None or df_check.empty:
                print("ERROR: No data fetched from Binance")
                continue

            # Convert string columns to numeric BEFORE passing to calculate_signals
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df_check[col] = pd.to_numeric(df_check[col], errors='coerce')

            # Remove any rows with NaN values
            df_check = df_check.dropna()

            df_check.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'},inplace=True)
            df_check = calculate_signals(df=df_check)
            df_check.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume'},inplace=True)
            df_check.to_csv("Delta_Final.csv")
            df = df_check
            df_position_check = df_check

            if is_time_in_range_ist():
                print(f"Trading time active: {is_time_in_range_ist()}")

                if martingale_manager.h_pos != 0:
                    if fake_trade_flag != 0:
                        fake_signal_with_position = fake_trade_loss_checker(df_position_check, delta_client.current_candle_time)
                        set_flag_fake_trade(0)
                        logger.info(f"fake trade flag is reverted to {fake_trade_flag} , fake signal with position status is {fake_signal_with_position}")
                        if fake_signal_with_position:
                            print(" Fake signal detected with active position!")
                    
                    opposite_signal_exit = martingale_manager.check_opposite_signal()
                    df = delta_client.fetch_data_binance()
                    df = calculate_signals(df)
                    
                    # FIX: Get current signal for display, not undefined entry_signal
                    current_signal_for_display = df.iloc[-1]['Signal_Final']
                    entry_signal_for_display = martingale_manager.entry_signal if martingale_manager.entry_signal else "None"
                    print(f"current entry signal is {entry_signal_for_display} and current signal is {current_signal_for_display}")
    
                    if opposite_signal_exit:
                        print(" Position closed due to opposite signal!")
                        continue

                    try:
                        print("Existing position detected - monitoring...")
                        position_closed = martingale_manager.monitor_and_close_position()
                        if position_closed:
                            print("Position monitoring completed")
                            continue
                    except Exception as monitor_e:
                        print(f"Error monitoring position: {monitor_e}")
                        continue
                
                # Check if we can take a trade (no active positions)
                can_trade = delta_client.get_active_positions()
                print(f"can trade status is {can_trade}")
                
                if can_trade and martingale_manager.can_take_trade():
                    try:
                        last_candle = df.iloc[-1]
                        current_entry_signal = last_candle['Signal_Final']  # FIX: Use different variable name
                        current_price = delta_client.get_market_price()
                        
                        print(f"Current Price: ${current_price}")
                        print(f"Signal: {current_entry_signal}")
                        print(f"RM1 Level: {martingale_manager.current_level}")

                        # Check for entry signal
                        if current_entry_signal in DESIRED_TYPES and current_entry_signal != 0:
                            try:
                                delta_client.current_candle_time = int(df.iloc[-1]['time'])
                                direction = "buy" if int(current_entry_signal) > 0 else "sell"
                                print(f"Taking {direction.upper()} trade!")

                                # Calculate trade parameters
                                i = len(df) - 1
                                row = df.iloc[i]
                                prev_row = df.iloc[i-1]
                                second_last_row = df.iloc[i-2] if i > 1 else prev_row

                                entry_price = int(current_price)
                                sl, tp = risk_manager.calculate_sl_tp(entry_price, direction, prev_row, second_last_row)
                                sl = float(sl)
                                tp = float(tp)
                                
                                # Double trigger increment is now handled directly in update_trade_result

                                # Get current leverage and calculate trade size
                                current_leverage = martingale_manager.get_leverage()
                                trade_amount = delta_client.calculate_trade_size(entry_price, current_leverage, base_capital)
                                
                                # Set leverage before placing trade
                                delta_client.set_leverage(current_leverage)
                                
                                print(f"  Trade Details:")
                                print(f"  Direction: {direction.upper()}")
                                print(f"  Entry Price: ${entry_price}")
                                print(f"  Stop Loss: ${sl}")
                                print(f"  Take Profit: ${tp}")
                                print(f"  Quantity: {trade_amount}")
                                print(f"  Leverage: {current_leverage}x")
                                print(f"  Notional: ${trade_amount * entry_price}")
                                
                                # Check balance
                                balance = delta_client.get_usd_balance()
                                print(f"Account Balance: ${balance}")
                                
                                # Step 1: Place market order first
                                print(" Placing market order...")
                                current_price = delta_client.get_market_price()
                                logger.info(f"current_price is {current_price} before placing the market order")
                                market_order = delta_client.place_order_market(direction, trade_amount)
                                set_candle_entry_time(time=df.iloc[-1]['time'])
                                logger.info(f"the current entry signal is {current_entry_signal}")
                                logger.info(f"the market order has been placed and response is {market_order}")
                                martingale_manager.balance_before = delta_client.get_usd_balance()
                                martingale_manager.h_pos = int(current_entry_signal / 2)  # FIX: Use correct variable
                                
                                if market_order:
                                    print(f" Market order placed: {market_order.get('id')}")
                                    set_trade_tracking(current_entry_signal, direction, entry_price, delta_client.current_candle_time)  # FIX: Use correct variable
                                    set_flag_fake_trade(1)
                                    logger.info(f"since a new trade is being opened the fake trade flag is {fake_trade_flag}")
                                    
                                    # Step 2: Place bracket order for SL/TP management
                                    print(" Placing bracket order for SL/TP...")

                                    try:
                                        logger.info(f"placing order at sl: {sl} , tp: {tp}")
                                        bracket_order_res = delta_client.place_order_bracket(
                                            side=direction,
                                            size=trade_amount,
                                            entry_price=entry_price,
                                            stop_price=sl,
                                            take_profit_price=tp
                                        )
                                        print(f"bracket order res is {bracket_order_res}")
                                        logger.info(f"bracket order response is {bracket_order_res}")
                                        if not bracket_order_res or not bracket_order_res.get('success',False):
                                            raise Exception("Bracket order placement failed")
                                    except Exception as e:
                                        print(f"Initial bracket order failed {e}")
                                        time.sleep(1)
                                        if direction.lower() == 'buy':
                                            sl = round(sl-7,2)
                                            tp = round(tp+5,2)
                                        elif direction.lower() == 'sell':
                                            sl = round(sl+7,2)
                                            tp = round(tp-5,2)
                                        else:
                                            print(f"Invalid direction {direction}")
                                        
                                        try:
                                            logger.info(f"placing order since last bracket order failed at sl: {sl} , tp: {tp}")
                                            bracket_order_res = delta_client.place_order_bracket(
                                                side=direction,
                                                size=trade_amount,
                                                entry_price=entry_price,
                                                stop_price=sl,
                                                take_profit_price=tp
                                            )
                                            print(f"fallback bracket order response {bracket_order_res}")
                                        except Exception as e2:
                                            print(f"fallback bracket order also has failed {e2}")
                                            bracket_order_res = None
                                            current_price = delta_client.get_market_price()
                                            if direction == 'buy':
                                                logger.info(f"since the fallback market order also failed we are closing the order at {current_price}")
                                                delta_client.place_order_market(side='sell',size=martingale_manager.last_quantity)
                                                martingale_manager.clear_position()
                                                reset_candle_entry_exit_time()
                                            else:
                                                logger.info(f"since the fallback market order also failed we are closing the order at {current_price}")
                                                delta_client.place_order_market(side='buy',size=martingale_manager.last_quantity)
                                                martingale_manager.clear_position()
                                                reset_candle_entry_exit_time()
                                    try:
                                        bracket_tp_order_id = bracket_order_res['result']['take_profit_order']['id']
                                        bracket_sl_order_id = bracket_order_res['result']['stop_loss_order']['id']
                                    except Exception as e:
                                        try:
                                            bracket_tp_order_id = bracket_order_res['take_profit_order']['id']
                                            bracket_sl_order_id = bracket_order_res['stop_loss_order']['id']
                                        except Exception as e:
                                            print(f"exception {e} occured.")

                                    current_bracket_state_tp = delta_client.get_order_status(order_id=bracket_tp_order_id)
                                    current_bracket_state_sl = delta_client.get_order_status(order_id=bracket_sl_order_id)
                                    print(f"current bracket order tp id is {bracket_tp_order_id} and state is {current_bracket_state_tp}")
                                    print(f"current bracket order sl id is {bracket_sl_order_id} and state is {current_bracket_state_sl}")
                                        
                                    # Set position status
                                    if direction == "buy":
                                        signal_for_position = 2
                                    else:
                                        signal_for_position = -2
                                    martingale_manager.set_position(direction, entry_price, sl, tp, trade_amount, signal_for_position)
                                    # Clear elevated start flag after using it for this trade
                                    
                                        
                                    print(" Waiting for bracket order to complete...")
                                else:
                                    print(" Failed to place market order")
                                    reset_trade_tracking()
                                    
                            except Exception as signal_e:
                                print(f" Error processing signal: {signal_e}")
                                reset_trade_tracking()
                        else:
                            print("No trading signal detected")
                            
                    except Exception as fetch_e:
                        print(f"Error fetching data or processing signals: {fetch_e}")
                        continue
                
                # Status summary
                try:
                    print(f"\n System Status:")
                    print(f"  RM1 Level: {martingale_manager.current_level}")
                    print(f"  Next Leverage: {martingale_manager.get_leverage()}x")
                    print(f"  Capital: ${martingale_manager.base_capital}")
                    print(f"  Position: h_pos = {martingale_manager.h_pos}")
                    print(f"  Fake Loss Amount: ${fake_loss_amount:.2f}")
                    # print(f"  Double Trigger Flag: {double_trigger_flag}")
                    # print(f"  Pending Double Trigger: {pending_double_trigger}")
                    print(f"  Trade Tracking Active: {trade_taken_time is not None}")
                    if martingale_manager.last_loss_timestamp:
                        print(f"  Last Loss: {martingale_manager.last_loss_type} at {datetime.fromtimestamp(martingale_manager.last_loss_timestamp).strftime('%H:%M:%S')}")
                except Exception as status_e:
                    print(f"Error displaying status: {status_e}")
                
                # Sleep between cycles
                print(f" Sleeping for {1} seconds...")
                time.sleep(1)
            else:
                print("Outside trading hours, sleeping...")
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n" + "="*50)
            print("BOT STOPPED BY USER (Ctrl+C)")
            print("="*50)
            logger.info("Trading bot stopped by user (KeyboardInterrupt)")
            logger.info(f"Final status - Level: {martingale_manager.current_level}, Position: {martingale_manager.h_pos}, Fake Loss: ${fake_loss_amount:.2f}")
            break
        except Exception as e:
            print(f" Error in main loop: {e}") 
            time.sleep(1)
            continue