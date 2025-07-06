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
import threading

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
            sl = min(
                second_last_row['low'],
                entry_price - self.sl_buffer_points
            )
            tp = entry_price * (1 + self.tp_percent/100)
        else:  # sell
            sl = max(
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
        
        # New attributes for order tracking
        self.position_order_id = None
        self.sl_order_id = None
        self.tp_order_id = None
        self.last_tp_price = None
        self.last_sl_price = None
        self.last_entry_price = None
        self.last_direction = None  # Track direction for monitoring
        self.monitoring_active = False
        
        # Position tracking
        self.h_pos = 0  # 0: no position, 1: position active
        self.post_trade_sleep = False  # Flag for post-trade sleep
        
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
    
    def track_orders(self, position_order_id, sl_order_id, tp_order_id, tp_price, sl_price, entry_price, direction):
        """Track the three orders: position, stop loss, and take profit"""
        self.position_order_id = position_order_id
        self.sl_order_id = sl_order_id
        self.tp_order_id = tp_order_id
        self.last_tp_price = tp_price
        self.last_sl_price = sl_price
        self.last_entry_price = entry_price
        self.last_direction = direction
        self.monitoring_active = True
        self.h_pos = 1  # Set position active
        print(f"Orders tracked - Position: {position_order_id}, SL: {sl_order_id}, TP: {tp_order_id}")
        print(f"Position set: h_pos = {self.h_pos} for 1 trade")
    
    def clear_orders(self):
        """Clear all order tracking"""
        self.position_order_id = None
        self.sl_order_id = None
        self.tp_order_id = None
        self.last_tp_price = None
        self.last_sl_price = None
        self.last_entry_price = None
        self.last_direction = None
        self.monitoring_active = False
        self.h_pos = 0  # Clear position
        self.post_trade_sleep = True  # Activate post-trade sleep
        print("Order tracking cleared")
        print(f"Position cleared: h_pos = {self.h_pos}")
    
    def monitor_orders(self, symbol):
        """Monitor orders continuously and return signal when TP/SL is hit"""
        while self.monitoring_active and (self.sl_order_id is not None or self.tp_order_id is not None):
            try:
                # Get current price
                current_price = self.get_current_price(symbol)
                if current_price is None:
                    time.sleep(2)
                    continue
                
                signal = 0  # 0: no signal, 1: profit, -1: loss
                
                # Check based on direction
                if self.last_direction == 'buy':
                    # For BUY: TP > current_price > SL
                    if self.last_tp_price and current_price >= self.last_tp_price:
                        print(f"Take Profit hit! Current price: {current_price}, TP: {self.last_tp_price}")
                        signal = 1
                        # Cancel SL order
                        if self.sl_order_id:
                            binance_client.cancel_trade(symbol, self.sl_order_id)
                            self.sl_order_id = None
                        self.update_trade_result('win')
                        self.clear_orders()
                        break
                    
                    elif self.last_sl_price and current_price <= self.last_sl_price:
                        print(f"Stop Loss hit! Current price: {current_price}, SL: {self.last_sl_price}")
                        signal = -1
                        # Cancel TP order
                        if self.tp_order_id:
                            binance_client.cancel_trade(symbol, self.tp_order_id)
                            self.tp_order_id = None
                        self.update_trade_result('loss')
                        self.clear_orders()
                        break
                
                elif self.last_direction == 'sell':
                    # For SELL: SL > current_price > TP
                    if self.last_tp_price and current_price <= self.last_tp_price:
                        print(f"Take Profit hit! Current price: {current_price}, TP: {self.last_tp_price}")
                        signal = 1
                        # Cancel SL order
                        if self.sl_order_id:
                            binance_client.cancel_trade(symbol, self.sl_order_id)
                            self.sl_order_id = None
                        self.update_trade_result('win')
                        self.clear_orders()
                        break
                    
                    elif self.last_sl_price and current_price >= self.last_sl_price:
                        print(f"Stop Loss hit! Current price: {current_price}, SL: {self.last_sl_price}")
                        signal = -1
                        # Cancel TP order
                        if self.tp_order_id:
                            binance_client.cancel_trade(symbol, self.tp_order_id)
                            self.tp_order_id = None
                        self.update_trade_result('loss')
                        self.clear_orders()
                        break
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                print(f"Error in order monitoring: {e}")
                time.sleep(2)
                continue
        
        return signal
    
    def get_current_price(self, symbol):
        """Get current price of the symbol"""
        try:
            klines = binance_client.get_klines(symbol, interval='1m', limit=1)
            if klines and len(klines) > 0:
                return float(klines[0][4])  # Close price
        except Exception as e:
            print(f"Error getting current price: {e}")
        return None
    
    def get_current_position(self, symbol):
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
base_leverage = 10 # Base leverage multiplier
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

def start_order_monitoring(martingale_manager, binance_client, symbol):
    """Start order monitoring in a separate thread"""
    def monitor():
        martingale_manager.monitor_orders(symbol)
    
    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    return monitor_thread

binance_client.set_leverage(BINANCE_SYMBOL,10)

while True:
    print("\n--- New Trading Cycle ---")
    
    # Check if we're in post-trade sleep period
    if martingale_manager.post_trade_sleep:
        print("Post-trade sleep active. Sleeping for 120 seconds...")
        time.sleep(120)  # 2 minutes sleep after TP/SL hit
        martingale_manager.post_trade_sleep = False
        print("Post-trade sleep completed.")
        continue
    
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

    # Check conditions before placing new order
    condition1 = entry_signal and entry_signal != 0  # There is a signal
    condition2 = martingale_manager.h_pos == 0  # No active position
    condition3 = not martingale_manager.monitoring_active  # Not currently monitoring orders
    
    print(f"Signal: {entry_signal}, h_pos: {martingale_manager.h_pos}, monitoring: {martingale_manager.monitoring_active}")
    print(f"Condition 1 (signal exists): {condition1}")
    print(f"Condition 2 (no position): {condition2}")
    print(f"Condition 3 (not monitoring): {condition3}")
    
    # Only process new signals if all conditions are met
    if condition1 and condition2 and condition3:
        direction = entry_signal
        
        entry_price = row['close']
        sl, tp = risk_manager.calculate_sl_tp(entry_price, direction, prev_row, second_last_row)
        
        # Get symbol info for proper price precision
        symbol_info = binance_client.get_symbol_info(BINANCE_SYMBOL)
        if symbol_info:
            # price_precision = symbol_info['price_precision']
            price_precision = 1
            # Round prices to correct precision
            entry_price = round(entry_price, price_precision)
            sl = round(sl, price_precision)
            tp = round(tp, price_precision)
            print(f"Prices rounded to {price_precision} decimals - Entry: {entry_price}, SL: {sl}, TP: {tp}")
        
        side = ("BUY" if direction == 'buy' else "SELL")
        opposite_side = ("SELL" if direction == 'buy' else "BUY")
        
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
            
            # FIXED CALCULATION: Use leverage properly
            # Total buying power = capital * leverage
            total_buying_power = current_capital * current_leverage
            # Trade amount in base asset = buying_power / entry_price
            raw_trade_amount = total_buying_power / entry_price
            
            # Adjust for step size and precision
            trade_amount = round(raw_trade_amount, quantity_precision)
            
            # Ensure trade amount meets minimum quantity requirement
            if trade_amount < min_qty:
                trade_amount = min_qty
                print(f"Trade amount adjusted to minimum: {trade_amount}")
            
            print(f"Symbol info - Min qty: {min_qty}, Step size: {step_size}, Precision: {quantity_precision}")
            print(f"Capital: {current_capital}, Leverage: {current_leverage}x, Buying power: {total_buying_power}")
            print(f"Raw amount: {raw_trade_amount}, Adjusted amount: {trade_amount}")
        else:
            print("Could not get symbol info, using default precision")
            # Default calculation with leverage
            total_buying_power = current_capital * current_leverage
            trade_amount = round(total_buying_power / entry_price, 3)  # Default to 3 decimal places
        
        print(f"RM1 System - Level: {martingale_manager.current_level}, Leverage: {current_leverage}x")
        print(f"Capital: {current_capital}")
        print(f"Open {side} trade at {entry_price} | SL: {sl} | TP: {tp} | Amount: {trade_amount}")
        
        binance_client.get_account_balance()
        
        # Place 3 separate orders
        try:
            # 1. Place position order (market order)
            position_order = binance_client.place_order(BINANCE_SYMBOL, side, "MARKET", trade_amount)
            position_order_id = position_order.get('orderId') if position_order else None
            
            if position_order and position_order_id:
                print(f"Position order placed successfully: {position_order_id}")
                
                # 2. Place stop loss order
                sl_order = binance_client.place_stoploss_order(
                    symbol=BINANCE_SYMBOL,
                    side=opposite_side,  # Opposite side to close position
                    quantity=trade_amount,
                    stop_price=round(sl,1)
                )
                sl_order_id = sl_order.get('orderId') if sl_order else None
                
                # 3. Place take profit order (limit order)
                tp_order = binance_client.place_order(
                    symbol=BINANCE_SYMBOL,
                    side=opposite_side,  # Opposite side to close position
                    type="LIMIT",
                    quantity=trade_amount,
                    price=round(tp,1)
                )
                tp_order_id = tp_order.get('orderId') if tp_order else None
                print(f"STOP LOSS ORDER RESPONSE : {sl_order}")
                print(f"TAKE PROFIT ORDER RESPONSE : {tp_order}")
                
                if sl_order_id and tp_order_id:
                    print(f"All orders placed successfully - Position: {position_order_id}, SL: {sl_order_id}, TP: {tp_order_id}")
                    
                    # Track orders and start monitoring
                    martingale_manager.track_orders(position_order_id, sl_order_id, tp_order_id, tp, sl, entry_price, direction)
                    
                    # Start monitoring in a separate thread
                    start_order_monitoring(martingale_manager, binance_client, BINANCE_SYMBOL)
                    
                else:
                    print("Failed to place SL or TP orders")
                    # Cancel position order if SL/TP failed
                    if position_order_id:
                        binance_client.cancel_trade(BINANCE_SYMBOL, position_order_id)
            else:
                print("Failed to place position order")
                
        except Exception as e:
            print(f"Error placing orders: {e}")
    
    else:
        print("Conditions not met for new trade - either no signal, position active, or monitoring in progress")

    # Step 9: Save data and wait for next cycle
    print(f"RM1 System - Current Level: {martingale_manager.current_level}, Next Leverage: {martingale_manager.get_leverage()}x")
    print(f"Current Capital: {martingale_manager.base_capital}")
    print(f"Monitoring Active: {martingale_manager.monitoring_active}")
    print(f"Position Status: h_pos = {martingale_manager.h_pos}")
    print("Cycle complete. Sleeping for next interval...")
    print("\n"+("_"*120)+"\n")
    df.to_csv("./data.csv")
    time.sleep(interval_seconds)