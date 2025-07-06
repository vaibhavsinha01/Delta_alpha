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
        
        # Position tracking attributes
        self.position_order_id = None
        self.last_tp_price = None
        self.last_sl_price = None
        self.last_entry_price = None
        self.last_direction = None
        self.last_quantity = None
        
        # Position management
        self.h_pos = 0  # 0: no position, 1: buy position, -1: sell position
        self.min_lot = 0.001  # Minimum lot size for Bitcoin
        
    def calculate_trade_size(self, current_price, leverage):
        """
        Simplified and correct position sizing calculation
        Formula: (capital * leverage) / current_price = quantity in BTC
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
        """Check if we can take a new trade (no existing position)"""
        can_trade = self.h_pos == 0
        print(f"Can take trade check: h_pos={self.h_pos}, result={can_trade}")
        return can_trade
    
    def set_position(self, direction, entry_price, sl_price, tp_price, quantity):
        """Set position status when opening a trade"""
        if direction == 'buy':
            self.h_pos = 1
        elif direction == 'sell':
            self.h_pos = -1
        
        self.last_entry_price = entry_price
        self.last_sl_price = sl_price
        self.last_tp_price = tp_price
        self.last_direction = direction
        self.last_quantity = quantity
        
        print(f"Position set: h_pos = {self.h_pos} for {direction} trade")
        print(f"  Entry: ${entry_price}, SL: ${sl_price}, TP: ${tp_price}")
    
    def clear_position(self):
        """Clear position status when trade is closed"""
        self.h_pos = 0
        self.position_order_id = None
        self.last_tp_price = None
        self.last_sl_price = None
        self.last_entry_price = None
        self.last_direction = None
        self.last_quantity = None
        print("Position cleared: h_pos = 0")
    
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
    
    def monitor_and_close_position(self, symbol):
        """
        Monitor position and manually close when TP/SL is hit
        This replaces the threading approach with a blocking monitor
        Returns True when position is closed, False if no position to monitor
        """
        if self.h_pos == 0:
            return False
            
        print("🔍 Starting position monitoring (blocking mode)...")
        print(f"  Direction: {self.last_direction}")
        print(f"  Entry: ${self.last_entry_price}")
        print(f"  SL: ${self.last_sl_price}")
        print(f"  TP: ${self.last_tp_price}")
        print(f"  Quantity: {self.last_quantity}")
        
        while self.h_pos != 0:
            try:
                # Get current price
                current_price = self.get_current_price(symbol)
                if current_price is None:
                    time.sleep(2)
                    continue
                
                trade_closed = False
                result = None
                
                # Check based on direction
                if self.last_direction == 'buy':
                    # For BUY: TP > current_price > SL
                    if self.last_tp_price and current_price >= self.last_tp_price:
                        print(f"✅ Take Profit hit! Current price: {current_price}, TP: {self.last_tp_price}")
                        # Close position by selling the same quantity
                        close_order = binance_client.place_order(
                            symbol, "SELL", "MARKET", self.last_quantity
                        )
                        if close_order:
                            print(f"✅ Position closed via market sell order: {close_order.get('orderId')}")
                            result = 'win'
                            trade_closed = True
                        else:
                            print("❌ Failed to close position at TP")
                    
                    elif self.last_sl_price and current_price <= self.last_sl_price:
                        print(f"❌ Stop Loss hit! Current price: {current_price}, SL: {self.last_sl_price}")
                        # Close position by selling the same quantity
                        close_order = binance_client.place_order(
                            symbol, "SELL", "MARKET", self.last_quantity
                        )
                        if close_order:
                            print(f"✅ Position closed via market sell order: {close_order.get('orderId')}")
                            result = 'loss'
                            trade_closed = True
                        else:
                            print("❌ Failed to close position at SL")
                
                elif self.last_direction == 'sell':
                    # For SELL: SL > current_price > TP
                    if self.last_tp_price and current_price <= self.last_tp_price:
                        print(f"✅ Take Profit hit! Current price: {current_price}, TP: {self.last_tp_price}")
                        # Close position by buying the same quantity
                        close_order = binance_client.place_order(
                            symbol, "BUY", "MARKET", self.last_quantity
                        )
                        if close_order:
                            print(f"✅ Position closed via market buy order: {close_order.get('orderId')}")
                            result = 'win'
                            trade_closed = True
                        else:
                            print("❌ Failed to close position at TP")
                    
                    elif self.last_sl_price and current_price >= self.last_sl_price:
                        print(f"❌ Stop Loss hit! Current price: {current_price}, SL: {self.last_sl_price}")
                        # Close position by buying the same quantity
                        close_order = binance_client.place_order(
                            symbol, "BUY", "MARKET", self.last_quantity
                        )
                        if close_order:
                            print(f"✅ Position closed via market buy order: {close_order.get('orderId')}")
                            result = 'loss'
                            trade_closed = True
                        else:
                            print("❌ Failed to close position at SL")
                
                # If trade closed, clean up and update result
                if trade_closed and result:
                    self.update_trade_result(result)
                    self.clear_position()
                    
                    # Sleep for 120 seconds (2 candles) to prevent immediate re-entry
                    print("🛌 Trade closed. Sleeping for 120 seconds to prevent same-candle re-entry...")
                    time.sleep(120)
                    print("🔄 Ready for next trade opportunity")
                    return True
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                print(f"Error in position monitoring: {e}")
                time.sleep(2)
                continue
        
        return True
    
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


if __name__ == "__main__":
    print("🚀 Starting Trading Bot with Manual TP/SL Management")
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
            
            # Step 1: If we have an open position, monitor it first
            if martingale_manager.h_pos != 0:
                print("📊 Existing position detected - monitoring...")
                position_closed = martingale_manager.monitor_and_close_position(BINANCE_SYMBOL)
                if position_closed:
                    print("✅ Position monitoring completed")
                    # Continue to next cycle to look for new signals
                    continue
            
            # Step 2: Look for new trading opportunities (only if no position)
            if martingale_manager.can_take_trade():
                # Fetch and prepare data
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
                print(f"the entry signal is {entry_signal} with current_price {current_price}")
                
                # Process latest signal
                i = len(df) - 1
                row = df.iloc[i]
                prev_row = df.iloc[i-1]
                second_last_row = df.iloc[i-2] if i > 1 else prev_row

                print(f"📊 Current Price: ${current_price}")
                print(f"📈 Signal: {entry_signal}")
                print(f"🎯 Position Status: h_pos = {martingale_manager.h_pos}")
                print(f"📊 RM1 Level: {martingale_manager.current_level}")

                # Check for entry signal
                if entry_signal:
                    direction = "buy" if int(entry_signal) > 0 else "sell"
                    print(f"🎯 Taking {direction.upper()} trade!")

                    entry_price = row['close']
                    sl, tp = risk_manager.calculate_sl_tp(entry_price, direction, prev_row, second_last_row)
                    
                    # Get current leverage and calculate trade size
                    current_leverage = martingale_manager.get_leverage()
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
                    
                    # Place only the position order (no SL/TP orders)
                    try:
                        print("📝 Placing position order...")
                        position_order = binance_client.place_order(BINANCE_SYMBOL, side, "MARKET", trade_amount)
                        position_order_id = position_order.get('orderId') if position_order else None
                        
                        if position_order and position_order_id:
                            print(f"✅ Position order placed: {position_order_id}")
                            
                            # Set position status and start monitoring
                            martingale_manager.set_position(direction, entry_price, sl, tp, trade_amount)
                            
                            # The position will be monitored in the next cycle iteration
                            print("🔄 Position opened - will monitor in next cycle")
                            
                        else:
                            print("❌ Failed to place position order")
                            
                    except Exception as e:
                        print(f"❌ Error placing order: {e}")
                
                else:
                    print("⏸️ No trading signal detected")
                    
                # Save data
                df.to_csv("./data.csv")
            
            # Status summary
            print(f"\n📊 System Status:")
            print(f"  RM1 Level: {martingale_manager.current_level}")
            print(f"  Next Leverage: {martingale_manager.get_leverage()}x")
            print(f"  Capital: ${martingale_manager.base_capital}")
            print(f"  Position: h_pos = {martingale_manager.h_pos}")
            
            # Only sleep if no position (if position exists, monitoring handles timing)
            if martingale_manager.h_pos == 0:
                interval_seconds = interval_to_seconds(BINANCE_INTERVAL)
                print(f"💤 Sleeping for {interval_seconds} seconds...")
                time.sleep(interval_seconds)
            
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            time.sleep(60)  # Wait 1 minute before retrying
            continue