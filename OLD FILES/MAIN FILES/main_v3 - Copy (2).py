import pandas as pd
import time
from datetime import datetime
from config import *
from module.rf import RangeFilter
from module.ib_indicator import calculate_inside_ib_box
from module.rsi_gaizy import RSIGainzy
from module.rsi_buy_sell import RSIBuySellIndicator
from binance_client_ import BinanceClient
from important import *
import warnings

# Suppress specific FutureWarnings from pandas
warnings.simplefilter(action='ignore', category=FutureWarning)


class RiskManager:
    def __init__(self, sl_buffer_points, tp_percent, initial_capital):
        self.sl_buffer_points = sl_buffer_points
        self.tp_percent = tp_percent
        self.equity = initial_capital
        self.max_drawdown = 0
        self.peak_equity = initial_capital

    def calculate_sl_tp(self, entry_price, direction, prev_row, second_last_row):
        if direction == 'buy':
            sl = max(
                second_last_row['low'],
                entry_price - self.sl_buffer_points
            )
            tp = entry_price * (1 + self.tp_percent/100)
        else:
            sl = min(
                second_last_row['high'],
                entry_price + self.sl_buffer_points
            )
            tp = entry_price * (1 - self.tp_percent/100)
        return round(sl,2), round(tp,2)

    def update_equity(self, pnl):
        self.equity += pnl
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        current_drawdown = (self.peak_equity - self.equity) / self.peak_equity * 100
        self.max_drawdown = max(self.max_drawdown, current_drawdown)


class MartingaleManager:
    def __init__(self, base_capital, base_leverage=1):
        self.base_capital = base_capital  # X money - fixed amount per trade
        self.base_leverage = base_leverage
        self.current_level = 0  # 0-4 for 5 levels
        self.leverage_multipliers = [1, 2, 4, 16, 32]  # RM1 leverage progression
        self.max_levels = 5
        self.last_trade_result = None  # 'win', 'loss', or None
        self.active_orders = {}  # Track active orders
        self.position_history = []  # Track position changes
        
    def get_leverage(self):
        """Get current leverage based on RM1 system"""
        return self.base_leverage * self.leverage_multipliers[self.current_level]
    
    def get_trade_amount(self):
        """Calculate trade amount - always use base capital"""
        return self.base_capital
    
    def update_trade_result(self, result):
        """Update trade result and adjust system based on RM1"""
        self.last_trade_result = result
        
        if result == 'win':
            # RM1: Reset to level 0 after any win
            self.current_level = 0
            print(f"Trade won! Resetting to level 0, leverage: {self.get_leverage()}x")
                
        elif result == 'loss':
            # RM1: Move to next level, reset to 0 if at max level
            if self.current_level >= self.max_levels - 1:
                print(f"5th trade failed! Resetting to beginning (level 0)")
                self.current_level = 0
            else:
                self.current_level += 1
                print(f"Trade lost! Moving to level {self.current_level}, leverage: {self.get_leverage()}x")
    
    def track_order(self, order_id, order_type, price, quantity, side):
        """Track active orders"""
        self.active_orders[order_id] = {
            'type': order_type,
            'price': price,
            'quantity': quantity,
            'side': side,
            'timestamp': datetime.now()
        }
    
    def check_order_execution(self, binance_client, symbol, current_price, tp_price, sl_price, entry_price):
        """Check if orders were executed and determine win/loss with martingale logic"""
        try:
            # Get current position
            current_position = self.get_current_position(binance_client, symbol)
            
            # Check if position changed from positive to zero
            if len(self.position_history) > 0:
                last_position = self.position_history[-1]
                if last_position != 0 and current_position == 0:
                    # Position closed, determine if it was TP or SL using the specified logic
                    tp_distance = abs(current_price - tp_price)
                    sl_distance = abs(current_price - sl_price)
                    
                    # Implement the martingale logic: if abs(current_price - tp_price) > abs(current_price - sl_price) then sl hit
                    if tp_distance > sl_distance:
                        # SL was hit - apply martingale multiplier
                        print(f"Position closed at SL level. Current price: {current_price}, SL: {sl_price}")
                        self.update_trade_result('loss')
                        # Set new leverage after loss
                        new_leverage = self.get_leverage()
                        binance_client.set_leverage(symbol, new_leverage)
                        print(f"Leverage updated to: {new_leverage}x")
                    else:
                        # TP was hit - keep martingale same (reset to level 0)
                        print(f"Position closed at TP level. Current price: {current_price}, TP: {tp_price}")
                        self.update_trade_result('win')
                        # Set leverage back to base after win
                        new_leverage = self.get_leverage()
                        binance_client.set_leverage(symbol, new_leverage)
                        print(f"Leverage reset to: {new_leverage}x")
            
            # Update position history
            self.position_history.append(current_position)
            
            # Keep only last 10 position records
            if len(self.position_history) > 10:
                self.position_history.pop(0)
                
        except Exception as e:
            print(f"Error checking order execution: {e}")
    
    def get_current_position(self, binance_client, symbol):
        """Get current position quantity for symbol"""
        try:
            endpoint = "/fapi/v2/positionRisk"
            timestamp = int(time.time() * 1000)
            params = {
                "symbol": symbol,
                "timestamp": timestamp,
            }
            query_string = '&'.join([f"{key}={params[key]}" for key in params])
            signature = binance_client.generate_signature(query_string)
            headers = {
                "X-MBX-APIKEY": binance_client.api_key
            }
            params["signature"] = signature
            
            import requests
            response = requests.get(f"{binance_client.base_url}{endpoint}", headers=headers, params=params)
            
            if response.status_code == 200:
                positions = response.json()
                for position in positions:
                    if position['symbol'] == symbol:
                        position_amt = float(position['positionAmt'])
                        return position_amt
                return 0  # No position found for this symbol
            else:
                print(f"Error getting position: {response.json()}")
                return 0
                
        except Exception as e:
            print(f"Error getting position: {e}")
            return 0


# Initialize components
rf = RangeFilter()
bsrsi = RSIBuySellIndicator()
Grsi = RSIGainzy()
binance_client = BinanceClient(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=1)
binance_client.login()
risk_manager = RiskManager(SL_BUFFER_POINTS, TP_PERCENT, INITIAL_CAPITAL)

# Initialize Martingale Manager with RM1 system
base_capital = INITIAL_CAPITAL  # X money - fixed amount per trade
base_leverage = 1  # Base leverage multiplier
martingale_manager = MartingaleManager(base_capital, base_leverage)


def interval_to_seconds(interval):
    if interval.endswith('m'):
        return int(interval[:-1]) * 60
    elif interval.endswith('h'):
        return int(interval[:-1]) * 60 * 60
    elif interval.endswith('d'):
        return int(interval[:-1]) * 24 * 60 * 60
    else:
        raise ValueError(f"Unsupported interval: {interval}")

def format_trade_data(direction, entry_price, sl, tp, trade_amount, strategy_type, martingale_level, leverage):
    """Format trade data for logging"""
    return {
        'timestamp': datetime.now().isoformat(),
        'symbol': BINANCE_SYMBOL,
        'direction': direction,
        'entry_price': entry_price,
        'sl': sl,
        'tp': tp,
        'amount': trade_amount,
        'strategy': strategy_type,
        'martingale_level': martingale_level,
        'leverage': leverage
    }

while True:
    print("\n--- New Trading Cycle ---")
    
    # Step 1: Fetch and prepare data
    limit = 1000
    interval_seconds = interval_to_seconds(BINANCE_INTERVAL)
    end_time = int(time.time() * 1000)  # Convert to milliseconds
    start_time = end_time - (interval_seconds * 1000 * limit)  # Convert to milliseconds
    
    df = binance_client.client.get_historical_klines(
        symbol=BINANCE_SYMBOL,
        interval=BINANCE_INTERVAL,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    # print(df)
    df = execute_signals(
        calculate_signals(
            convert_to_complete_format(
                df
            )
        )
    )
    # df = pd.read_csv(r"C:\Users\Ahmed Mohamed\Programming\Python\READY\trading - binance _ MIXED\data.csv")

    last_candle = df.iloc[-1]
    # last_candle = df.iloc[584]
    entry_signal = last_candle['Signal_Final']
    current_price = last_candle['close']
    
    # Step 4: Process latest signal
    i = len(df) - 1
    row = df.iloc[i]
    prev_row = df.iloc[i-1]
    second_last_row = df.iloc[i-2] if i > 1 else prev_row

    # Check for completed trades and update martingale
    if len(martingale_manager.active_orders) > 0:
        # Get the last trade's TP and SL for comparison
        last_tp = getattr(martingale_manager, 'last_tp', None)
        last_sl = getattr(martingale_manager, 'last_sl', None)
        last_entry = getattr(martingale_manager, 'last_entry', None)
        
        if last_tp and last_sl and last_entry:
            martingale_manager.check_order_execution(
                binance_client, BINANCE_SYMBOL, current_price, last_tp, last_sl, last_entry
            )
    
    if entry_signal:
        direction = entry_signal
        
        entry_price = row['close']
        sl, tp = risk_manager.calculate_sl_tp(entry_price, direction, prev_row, second_last_row)
        
        # Store TP/SL/Entry for martingale tracking
        martingale_manager.last_tp = tp
        martingale_manager.last_sl = sl
        martingale_manager.last_entry = entry_price
        
        side = ("BUY" if direction == 'buy' else "SELL")
        
        # RM1: Use base capital and set leverage
        current_capital = martingale_manager.get_trade_amount()  # Base capital (no RM2)
        current_leverage = martingale_manager.get_leverage()  # Current leverage (RM1)
        
        # Set leverage before placing trade
        binance_client.set_leverage(BINANCE_SYMBOL, current_leverage)
        
        # Get symbol info for proper precision
        symbol_info = binance_client.get_symbol_info(BINANCE_SYMBOL)
        if symbol_info:
            quantity_precision = symbol_info['quantity_precision']
            step_size = symbol_info['step_size']
            min_qty = symbol_info['min_qty']
            
            # Calculate trade amount: capital / entry_price (leverage is applied by exchange)
            raw_trade_amount = current_capital / entry_price
            
            # Adjust for step size and precision
            trade_amount = round(raw_trade_amount, quantity_precision)
            
            # Ensure trade amount meets minimum quantity requirement
            if trade_amount < min_qty:
                trade_amount = min_qty
                print(f"Trade amount adjusted to minimum: {trade_amount}")
            
            print(f"Symbol info - Min qty: {min_qty}, Step size: {step_size}, Precision: {quantity_precision}")
            print(f"Raw amount: {raw_trade_amount}, Adjusted amount: {trade_amount}")
        else:
            print("Could not get symbol info, using default precision")
            trade_amount = round(current_capital / entry_price, 3)  # Default to 3 decimal places
        
        print(f"RM1 System - Level: {martingale_manager.current_level}, Leverage: {current_leverage}x")
        print(f"Capital: {current_capital}")
        print(f"Open {side} trade at {entry_price} | SL: {sl} | TP: {tp} | Amount: {trade_amount}")
        
        binance_client.get_account_balance()
        order = binance_client.place_order(BINANCE_SYMBOL, side, "MARKET", trade_amount)
        if order:
            # Track the main order
            if 'orderId' in order:
                martingale_manager.track_order(
                    order['orderId'], 'MARKET', entry_price, trade_amount, side
                )
            
            # Place stop loss order
            oco_order = binance_client.place_oco_order(symbol=BINANCE_SYMBOL,side=side,type="LIMIT",quantity=trade_amount,current_price=entry_price)

            print(f"Order placed successfully: {order}")
            print(f"Stop loss order: {oco_order}")
            
            # Track OCO orders if they exist
            if oco_order and 'orders' in oco_order:
                for oco_sub_order in oco_order['orders']:
                    if 'orderId' in oco_sub_order:
                        martingale_manager.track_order(
                            oco_sub_order['orderId'], 
                            oco_sub_order.get('type', 'OCO'), 
                            oco_sub_order.get('price', 0), 
                            trade_amount, 
                            side
                        )

            # Log trade data with martingale level and leverage
            strategy_type = "Signal_Final"
            trade_data = format_trade_data(
                direction, entry_price, sl, tp, trade_amount, 
                strategy_type, martingale_manager.current_level, current_leverage
            )
            print(f"Trade data: {trade_data}")
            
        else:
            print("Failed to place order")

    # Step 9: Save data and wait for next cycle
    print(f"RM1 System - Current Level: {martingale_manager.current_level}, Next Leverage: {martingale_manager.get_leverage()}x")
    print(f"Current Capital: {martingale_manager.base_capital}")
    print("Cycle complete. Sleeping for next interval...")
    df.to_csv("./data.csv")
    time.sleep(interval_seconds)