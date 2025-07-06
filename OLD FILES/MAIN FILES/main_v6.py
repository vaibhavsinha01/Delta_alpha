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
        
        # Order tracking attributes
        self.position_order_id = None
        self.sl_order_id = None
        self.tp_order_id = None
        self.last_tp_price = None
        self.last_sl_price = None
        self.last_entry_price = None
        self.last_direction = None
        self.monitoring_active = False
        
        # FIXED: Position management - properly initialized
        self.h_pos = 0  # 0: no position, 1: buy position, -1: sell position
        self.min_lot = 0.001  # Minimum lot size for Bitcoin
        
    def calculate_trade_size(self, current_price, leverage):
        """
        FIXED: Simplified and correct position sizing calculation
        Formula: (capital * leverage) / current_price = quantity in BTC
        Example: (1000 * 10) / 100000 = 0.1 BTC
        """
        try:
            # Use only the base capital amount for each trade
            capital_to_use = self.base_capital
            
            # Calculate quantity: (capital * leverage) / price
            quantity = (capital_to_use * leverage) / current_price
            
            # Ensure minimum quantity
            if quantity < self.min_lot:
                quantity = self.min_lot
                
            print(f"Position sizing calculation:")
            print(f"  Capital: ${capital_to_use}")
            print(f"  Leverage: {leverage}x")
            print(f"  Price: ${current_price}")
            print(f"  Calculated quantity: {quantity} BTC")
            print(f"  Notional value: ${quantity * current_price}")
            
            return round(quantity, 3)  # Round to 3 decimal places for BTC
            
        except Exception as e:
            print(f"Error calculating trade size: {e}")
            return self.min_lot
        
    def get_leverage(self):
        """Get current leverage based on RM1 system"""
        return self.base_leverage * self.leverage_multipliers[self.current_level]
    
    def get_trade_amount(self):
        """Calculate trade amount - always use base capital"""
        return self.base_capital
    
    def can_take_trade(self):
        """FIXED: Check if we can take a new trade (no existing position)"""
        can_trade = self.h_pos == 0 and not self.monitoring_active
        print(f"Can take trade check: h_pos={self.h_pos}, monitoring_active={self.monitoring_active}, result={can_trade}")
        return can_trade
    
    def set_position(self, direction):
        """FIXED: Set position status when opening a trade"""
        if direction == 'buy':
            self.h_pos = 1
        elif direction == 'sell':
            self.h_pos = -1
        print(f"Position set: h_pos = {self.h_pos} for {direction} trade")
    
    def clear_position(self):
        """FIXED: Clear position status when trade is closed"""
        self.h_pos = 0
        self.monitoring_active = False
        print("Position cleared: h_pos = 0, monitoring_active = False")
    
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
        print(f"Orders tracked - Position: {position_order_id}, SL: {sl_order_id}, TP: {tp_order_id}")
    
    def clear_orders(self):
        """Clear all order tracking"""
        self.position_order_id = None
        self.sl_order_id = None
        self.tp_order_id = None
        self.last_tp_price = None
        self.last_sl_price = None
        self.last_entry_price = None
        self.last_direction = None
        print("Order tracking cleared")
    
    def monitor_orders(self, symbol):
        """FIXED: Monitor orders and implement proper sleep after TP/SL execution"""
        print("Starting order monitoring...")
        
        while self.monitoring_active and (self.sl_order_id is not None or self.tp_order_id is not None):
            try:
                # Get current price
                current_price = self.get_current_price(symbol)
                if current_price is None:
                    time.sleep(2)
                    continue
                
                trade_closed = False
                
                # Check based on direction
                if self.last_direction == 'buy':
                    # For BUY: TP > current_price > SL
                    if self.last_tp_price and current_price >= self.last_tp_price:
                        print(f"✅ Take Profit hit! Current price: {current_price}, TP: {self.last_tp_price}")
                        # Cancel SL order
                        if self.sl_order_id:
                            binance_client.cancel_trade(symbol, self.sl_order_id)
                            self.sl_order_id = None
                        self.update_trade_result('win')
                        trade_closed = True
                    
                    elif self.last_sl_price and current_price <= self.last_sl_price:
                        print(f"❌ Stop Loss hit! Current price: {current_price}, SL: {self.last_sl_price}")
                        # Cancel TP order
                        if self.tp_order_id:
                            binance_client.cancel_trade(symbol, self.tp_order_id)
                            self.tp_order_id = None
                        self.update_trade_result('loss')
                        trade_closed = True
                
                elif self.last_direction == 'sell':
                    # For SELL: SL > current_price > TP
                    if self.last_tp_price and current_price <= self.last_tp_price:
                        print(f"✅ Take Profit hit! Current price: {current_price}, TP: {self.last_tp_price}")
                        # Cancel SL order
                        if self.sl_order_id:
                            binance_client.cancel_trade(symbol, self.sl_order_id)
                            self.sl_order_id = None
                        self.update_trade_result('win')
                        trade_closed = True
                    
                    elif self.last_sl_price and current_price >= self.last_sl_price:
                        print(f"❌ Stop Loss hit! Current price: {current_price}, SL: {self.last_sl_price}")
                        # Cancel TP order
                        if self.tp_order_id:
                            binance_client.cancel_trade(symbol, self.tp_order_id)
                            self.tp_order_id = None
                        self.update_trade_result('loss')
                        trade_closed = True
                
                # FIXED: If trade closed, clean up and sleep
                if trade_closed:
                    self.clear_orders()
                    self.clear_position()
                    
                    # FIXED: Sleep for 120 seconds (2 candles) to prevent immediate re-entry
                    print("🛌 Trade closed. Sleeping for 120 seconds to prevent same-candle re-entry...")
                    time.sleep(120)
                    print("🔄 Ready for next trade opportunity")
                    break
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                print(f"Error in order monitoring: {e}")
                time.sleep(2)
                continue
    
    def get_current_price(self, symbol):
        """Get current price of the symbol"""
        try:
            klines = binance_client.get_klines(symbol, interval='1m', limit=1)
            if klines and len(klines) > 0:
                return float(klines[0][4])  # Close price
        except Exception as e:
            print(f"Error getting current price: {e}")
        return None


# Initialize components
rf = RangeFilter()
bsrsi = RSIBuySellIndicator()
Grsi = RSIGainzy()
binance_client = BinanceClient(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=1)
binance_client.login()
risk_manager = RiskManager(SL_BUFFER_POINTS, TP_PERCENT, INITIAL_CAPITAL)

# Initialize Martingale Manager with RM1 system
base_capital = INITIAL_CAPITAL  # X money - fixed amount per trade
base_leverage = 10  # Base leverage multiplier
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

def start_order_monitoring(symbol):
    """FIXED: Start order monitoring in a separate thread"""
    def monitor():
        martingale_manager.monitor_orders(symbol)
    
    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    return monitor_thread


if __name__ == "__main__":
    print("🚀 Starting Trading Bot with Fixed Position Management")
    print(f"💰 Initial Capital: ${base_capital}")
    print(f"⚡ Base Leverage: {base_leverage}x")
    print(f"📊 Symbol: {BINANCE_SYMBOL}")
    print(f"⏰ Interval: {BINANCE_INTERVAL}")
    print("=" * 50)
    
    # Set initial leverage
    binance_client.set_leverage(BINANCE_SYMBOL, base_leverage)
    
    while True:
        try:
            print("\n🔄 --- New Trading Cycle ---")
            
            # Step 1: Fetch and prepare data
            limit = 1000
            interval_seconds = interval_to_seconds(BINANCE_INTERVAL)
            end_time = int(time.time() * 1000)
            start_time = end_time - (interval_seconds * 1000 * limit)
            
            df = binance_client.client.get_historical_klines(
                symbol=BINANCE_SYMBOL,
                interval=BINANCE_INTERVAL,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            
            df = execute_signals(
                calculate_signals(
                    convert_to_complete_format(df)
                )
            )

            last_candle = df.iloc[-1]
            entry_signal = last_candle['Signal_Final']
            current_price = last_candle['close']
            
            # Process latest signal
            i = len(df) - 1
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            second_last_row = df.iloc[i-2] if i > 1 else prev_row

            print(f"📊 Current Price: ${current_price}")
            print(f"📈 Signal: {entry_signal}")
            print(f"🎯 Position Status: h_pos = {martingale_manager.h_pos}")
            print(f"👁️ Monitoring Active: {martingale_manager.monitoring_active}")
            print(f"📊 RM1 Level: {martingale_manager.current_level}")

            # FIXED: Check all conditions properly
            if entry_signal and martingale_manager.can_take_trade():
                direction = "buy" if int(entry_signal) > 0 else "sell"
                print(f"🎯 Taking {direction.upper()} trade!")

                entry_price = row['close']
                sl, tp = risk_manager.calculate_sl_tp(entry_price, direction, prev_row, second_last_row)
                
                # Get current leverage and calculate trade size
                current_leverage = martingale_manager.get_leverage()
                
                # FIXED: Use the corrected trade size calculation
                trade_amount = martingale_manager.calculate_trade_size(entry_price, current_leverage)
                
                # Set leverage before placing trade
                binance_client.set_leverage(BINANCE_SYMBOL, current_leverage)
                
                # Get symbol info for proper precision
                symbol_info = binance_client.get_symbol_info(BINANCE_SYMBOL)
                if symbol_info:
                    price_precision = 1
                    quantity_precision = symbol_info.get('quantity_precision', 1)
                    min_qty = symbol_info.get('min_qty', 0.001)
                    
                    # Round prices and quantities
                    entry_price = round(entry_price, price_precision)
                    sl = round(sl, price_precision)
                    tp = round(tp, price_precision)
                    trade_amount = max(round(trade_amount, quantity_precision), min_qty)
                
                side = "BUY" if direction == 'buy' else "SELL"
                opposite_side = "SELL" if direction == 'buy' else "BUY"
                
                print(f"🎯 Trade Details:")
                print(f"  Direction: {side}")
                print(f"  Entry Price: ${entry_price}")
                print(f"  Stop Loss: ${sl}")
                print(f"  Take Profit: ${tp}")
                print(f"  Quantity: {trade_amount} BTC")
                print(f"  Leverage: {current_leverage}x")
                print(f"  Notional: ${trade_amount * entry_price}")
                
                # Check account balance
                binance_client.get_account_balance()
                
                # Place orders
                try:
                    # FIXED: Set position status BEFORE placing orders
                    martingale_manager.set_position(direction)
                    
                    # 1. Place position order (market order)
                    print("📝 Placing position order...")
                    position_order = binance_client.place_order(BINANCE_SYMBOL, side, "MARKET", trade_amount)
                    position_order_id = position_order.get('orderId') if position_order else None
                    
                    if position_order and position_order_id:
                        print(f"✅ Position order placed: {position_order_id}")
                        
                        # 2. Place stop loss order
                        print("📝 Placing stop loss order...")
                        sl_order = binance_client.place_stoploss_order(
                            symbol=BINANCE_SYMBOL,
                            side=opposite_side,
                            quantity=trade_amount,
                            stop_price=round(sl, 1)
                        )
                        sl_order_id = sl_order.get('orderId') if sl_order else None
                        
                        # 3. Place take profit order
                        print("📝 Placing take profit order...")
                        tp_order = binance_client.place_order(
                            symbol=BINANCE_SYMBOL,
                            side=opposite_side,
                            type="LIMIT",
                            quantity=trade_amount,
                            price=round(tp, 1)
                        )
                        tp_order_id = tp_order.get('orderId') if tp_order else None
                        
                        if sl_order_id and tp_order_id:
                            print(f"✅ All orders placed successfully!")
                            print(f"   Position: {position_order_id}")
                            print(f"   Stop Loss: {sl_order_id}")
                            print(f"   Take Profit: {tp_order_id}")
                            
                            # FIXED: Track orders and start monitoring
                            martingale_manager.track_orders(
                                position_order_id, sl_order_id, tp_order_id, 
                                tp, sl, entry_price, direction
                            )
                            
                            # Start monitoring in separate thread
                            start_order_monitoring(BINANCE_SYMBOL)
                            
                        else:
                            print("❌ Failed to place SL or TP orders")
                            if position_order_id:
                                binance_client.cancel_trade(BINANCE_SYMBOL, position_order_id)
                            martingale_manager.clear_position()
                    else:
                        print("❌ Failed to place position order")
                        martingale_manager.clear_position()
                        
                except Exception as e:
                    print(f"❌ Error placing orders: {e}")
                    martingale_manager.clear_position()
            
            elif entry_signal and not martingale_manager.can_take_trade():
                if martingale_manager.h_pos != 0:
                    print(f"⏸️ Signal detected but position exists (h_pos = {martingale_manager.h_pos})")
                if martingale_manager.monitoring_active:
                    print(f"⏸️ Signal detected but monitoring active")
            
            elif not entry_signal:
                print("⏸️ No trading signal detected")

            # Status summary
            print(f"\n📊 System Status:")
            print(f"  RM1 Level: {martingale_manager.current_level}")
            print(f"  Next Leverage: {martingale_manager.get_leverage()}x")
            print(f"  Capital: ${martingale_manager.base_capital}")
            print(f"  Position: h_pos = {martingale_manager.h_pos}")
            print(f"  Monitoring: {martingale_manager.monitoring_active}")
            
            # Save data and wait
            df.to_csv("./data.csv")
            print(f"💤 Sleeping for {interval_seconds} seconds...")
            time.sleep(interval_seconds)
            
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            time.sleep(60)  # Wait 1 minute before retrying
            continue