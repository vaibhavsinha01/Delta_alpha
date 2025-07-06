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
        try:
            if direction == 'buy':
                sl = max(
                    second_last_row['low'],
                    entry_price - self.sl_buffer_points
                )
                tp = entry_price * (1 + self.tp_percent/100)
            else:  # sell
                sl = min(
                    second_last_row['high'],
                    entry_price + self.sl_buffer_points
                )
                tp = entry_price * (1 - self.tp_percent/100)
            return round(sl,2), round(tp,2)
        except Exception as e:
            print(f"Error calculating SL/TP: {e}")
            # Fallback values
            if direction == 'buy':
                sl = entry_price - self.sl_buffer_points
                tp = entry_price * (1 + self.tp_percent/100)
            else:
                sl = entry_price + self.sl_buffer_points
                tp = entry_price * (1 - self.tp_percent/100)
            return round(sl,2), round(tp,2)


class MartingaleManager:
    def __init__(self, base_capital, base_leverage=1):
        self.base_capital = base_capital  # X money - fixed amount per trade
        self.base_leverage = base_leverage
        self.current_level = 0  # 0-4 for 5 levels
        self.leverage_multipliers = [1, 2, 4, 8, 16]  # LEVERAGE INCREASES FROM 10->20->40->80->160
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
        self.fake_amount = 0
        self.max_fake_amount = 100
        self.max_fake_count = 3
        
    def calculate_trade_size(self, current_price, leverage):
        """
        Simplified and correct position sizing calculation
        Formula: (capital * leverage) / current_price = quantity in BTC
        """
        try:
            # Use only the base capital amount for each trade
            capital_to_use = self.base_capital
            
            quantity = self.min_lot # initialize the quantity so that the divide by zero error doesn't come across
            # Calculate quantity: (capital * leverage) / price
            if current_price != 0 or not None:
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
        try:
            return self.base_leverage * self.leverage_multipliers[self.current_level]
        except Exception as e:
            print(f"Error getting leverage: {e}")
            return self.base_leverage
    
    def get_trade_amount(self):
        """Calculate trade amount - always use base capital"""
        return self.base_capital
    
    def can_take_trade(self):
        """Check if we can take a new trade (no existing position)"""
        try:
            can_trade = self.h_pos == 0
            print(f"Can take trade check: h_pos={self.h_pos}, result={can_trade}")
            return can_trade
        except Exception as e:
            print(f"Error checking if can take trade: {e}")
            return False
    
    def set_position(self, direction, entry_price, sl_price, tp_price, quantity):
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
            
            print(f"Position set: h_pos = {self.h_pos} for {direction} trade")
            print(f"  Entry: ${entry_price}, SL: ${sl_price}, TP: ${tp_price}")
        except Exception as e:
            print(f"Error setting position: {e}")
    
    def clear_position(self):
        """Clear position status when trade is closed"""
        try:
            self.h_pos = 0
            self.position_order_id = None
            self.last_tp_price = None
            self.last_sl_price = None
            self.last_entry_price = None
            self.last_direction = None
            self.last_quantity = None
            print("Position cleared: h_pos = 0")
        except Exception as e:
            print(f"Error clearing position: {e}")
    
    def update_trade_result(self, result):
        """Update trade result and adjust system based on RM1"""
        try:
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
        except Exception as e:
            print(f"Error updating trade result: {e}")
    
    def increment_fake_loss(self,amount):
        try:
            self.fake_amount += amount
            if self.fake_amount < self.max_fake_amount:
                print(f"current fake_loss amount changed to {self.fake_amount}")
            elif self.fake_amount >= self.max_fake_amount:
                print(f"price of fake amount is beyond the max_fake_amount")
                if self.current_level<self.max_levels:
                    self.current_level = self.current_level + 1
                    print(f"current leverage is {self.base_leverage*self.leverage_multipliers[self.current_level]}")
                    binance_client.set_leverage(symbol=BINANCE_SYMBOL,leverage=self.base_leverage*self.leverage_multipliers[self.current_level])
                else:
                    self.current_level = 0
                    print(f"since the current level was already the max the counter is reset to {self.base_leverage} for trading")
                    binance_client.set_leverage(symbol=BINANCE_SYMBOL,leverage=self.base_leverage)
        except Exception as e:
            print(f"Error incrementing fake loss: {e}")

    def check_for_fake_trade(self, side, time_candle):
        try:
            start_balance = float(binance_client.get_account_balance())  # ensure float
            print(f"balance is {start_balance}")

            while True:
                interval_seconds = interval_to_seconds(BINANCE_INTERVAL)
                limit = 1000
                poll_interval = 10  # seconds between re-checks
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
                df.to_csv(f"Binance_Final.csv")

                last_row = df.iloc[-1]
                last_signal = last_row['Signal_Final']
                last_time = last_row['time']
                print(f"last df time is {last_time} and last trade candle time is {time_candle} , last signal is {last_signal}")
                # Only act when the target time has passed
                if int(last_time) >= int(time_candle)+30: # here we add 30 to see even in case of a one minute the difference will be more since 1m is 30 seconds
                    # if last_signal == 0:
                    print(f"now a new candle has been formed")
                    if df.iloc[-2]['Signal_Final'] == 0:
                        closing_side = "SELL" if side.lower() == "buy" else "BUY"
                        print(f"symbol is {BINANCE_SYMBOL} side is {closing_side} type is {"MARKET"} and quantity is {self.last_quantity}")
                        res = binance_client.place_order(
                            symbol=BINANCE_SYMBOL,
                            side=closing_side,
                            type="MARKET",
                            quantity=self.last_quantity
                        )
                        # print(f"res is {res}")
                        new_balance = float(binance_client.get_account_balance())
                        self.clear_position()
                        balance_loss = start_balance - new_balance
                        print(f"balance lost is {balance_loss}")
                        self.increment_fake_loss(balance_loss)
                    break

                # Wait and check again
                print(f"waiting for {poll_interval} seconds before checking again")
                time.sleep(poll_interval)

        except Exception as e:
            print(f"Error in check_for_fake_trade: {e}")

    def monitor_and_close_position(self, symbol):
        """
        Monitor position and manually close when TP/SL is hit
        This replaces the threading approach with a blocking monitor
        Returns True when position is closed, False if no position to monitor
        """
        try:
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
                    print(f"current direction is {self.last_direction} with current price with {current_price}")
                    print(f"the stoploss is {self.last_sl_price} and with takeprofit {self.last_tp_price}")
                    if self.last_direction == 'buy' or self.last_direction == "BUY":
                        # For BUY: TP > current_price > SL
                        if self.last_tp_price and current_price >= self.last_tp_price:
                            print(f"✅ Take Profit hit! Current price: {current_price}, TP: {self.last_tp_price}")
                            # Close position by selling the same quantity
                            try:
                                close_order = binance_client.place_order(
                                    symbol, "SELL", "MARKET", self.last_quantity
                                )
                                if close_order:
                                    print(f"✅ Position closed via market sell order: {close_order.get('orderId')}")
                                    result = 'win'
                                    trade_closed = True
                                else:
                                    print("❌ Failed to close position at TP")
                                
                                print(f"since tp was hit so current leverage is changed to {self.base_leverage}")
                                # self.current_level = 0
                                # binance_client.set_leverage(symbol=BINANCE_SYMBOL,leverage=self.base_leverage)
                            except Exception as close_e:
                                print(f"❌ Error closing position at TP: {close_e}")
                        
                        elif self.last_sl_price and current_price <= self.last_sl_price:
                            print(f"❌ Stop Loss hit! Current price: {current_price}, SL: {self.last_sl_price}")
                            # Close position by selling the same quantity
                            try:
                                close_order = binance_client.place_order(
                                    symbol, "SELL", "MARKET", self.last_quantity
                                )
                                if close_order:
                                    print(f"✅ Position closed via market sell order: {close_order.get('orderId')}")
                                    result = 'loss'
                                    trade_closed = True
                                else:
                                    print("❌ Failed to close position at SL")
                            except Exception as close_e:
                                print(f"❌ Error closing position at SL: {close_e}")
                    
                    elif self.last_direction == 'sell' or self.last_direction == "SELL":
                        # For SELL: SL > current_price > TP
                        if self.last_tp_price and current_price <= self.last_tp_price:
                            print(f"✅ Take Profit hit! Current price: {current_price}, TP: {self.last_tp_price}")
                            # Close position by buying the same quantity
                            try:
                                close_order = binance_client.place_order(
                                    symbol, "BUY", "MARKET", self.last_quantity
                                )
                                if close_order:
                                    print(f"✅ Position closed via market buy order: {close_order.get('orderId')}")
                                    result = 'win'
                                    trade_closed = True
                                else:
                                    print("❌ Failed to close position at TP")
                                
                                print(f"since tp was hit so current leverage is changed to {self.base_leverage}")
                                # self.current_level = 0
                                # binance_client.set_leverage(symbol=BINANCE_SYMBOL,leverage=self.base_leverage)
                            except Exception as close_e:
                                print(f"❌ Error closing position at TP: {close_e}")
                        
                        elif self.last_sl_price and current_price >= self.last_sl_price:
                            print(f"❌ Stop Loss hit! Current price: {current_price}, SL: {self.last_sl_price}")
                            # Close position by buying the same quantity
                            try:
                                close_order = binance_client.place_order(
                                    symbol, "BUY", "MARKET", self.last_quantity
                                )
                                if close_order:
                                    print(f"✅ Position closed via market buy order: {close_order.get('orderId')}")
                                    result = 'loss'
                                    trade_closed = True
                                else:
                                    print("❌ Failed to close position at SL")
                            except Exception as close_e:
                                print(f"❌ Error closing position at SL: {close_e}")
                    
                    # If trade closed, clean up and update result
                    if trade_closed and result:
                        self.update_trade_result(result)
                        self.clear_position()
                        
                        # Sleep for 120 seconds (2 candles) to prevent immediate re-entry
                        print("🛌 Trade closed. Sleeping for 120 seconds to prevent same-candle re-entry...")
                        time.sleep(RENTRY_TIME_BINANCE)
                        print("🔄 Ready for next trade opportunity")
                        return True
                    
                    time.sleep(2)  # Check every 2 seconds
                    
                except Exception as e:
                    print(f"Error in position monitoring loop: {e}")
                    time.sleep(2)
                    continue
            
            return True
        except Exception as e:
            print(f"Error in monitor_and_close_position: {e}")
            return False
    
    def get_current_price(self, symbol):
        """Get current price of the symbol"""
        try:
            klines = binance_client.get_klines(BINANCE_SYMBOL,interval=BINANCE_INTERVAL,limit=1)
            if klines and len(klines) > 0:
                return float(klines[0][4])  # Close price
            return None
        except Exception as e:
            print(f"Error getting current price: {e}")
            return None


# Initialize components
try:
    rf = RangeFilter()
    bsrsi = RSIBuySellIndicator()
    Grsi = RSIGainzy()
    binance_client = BinanceClient(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=1)
    binance_client.login()
    risk_manager = RiskManager(SL_BUFFER_POINTS, TP_PERCENT, INITIAL_CAPITAL)

    # Initialize Martingale Manager with RM1 system
    base_capital = INITIAL_CAPITAL  # X money - fixed amount per trade
    base_leverage = BINANCE_BASE_LEVERAGE  # Base leverage multiplier
    martingale_manager = MartingaleManager(base_capital, base_leverage)
except Exception as e:
    print(f"Error initializing components: {e}")
    exit(1)


def interval_to_seconds(interval):
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

def format_trade_data(direction, entry_price, sl, tp, trade_amount, strategy_type, martingale_level, leverage):
    """Format trade data for logging"""
    try:
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
    except Exception as e:
        print(f"Error formatting trade data: {e}")
        return {}
    
def is_time_in_range_ist():
    from datetime import datetime, time
    import pytz
    # Define IST timezone
    ist = pytz.timezone("Asia/Kolkata")
    
    # Get current time in IST
    current_time = datetime.now(ist).time()
    # Define time range (05:30 to 14:00 IST)
    start_time = time(START_HOUR,START_MINUTE)
    end_time = time(END_HOUR,END_MINUTE)
    # start_time = time(5, 30)   # 05:30 AM
    # end_time = time(14, 0)     # 02:00 PM

    # Check if current time is within the range
    return start_time <= current_time <= end_time

if __name__ == "__main__":
    try:
        print("🚀 Starting Trading Bot with Manual TP/SL Management")
        print(f"💰 Initial Capital: ${base_capital}")
        print(f"⚡ Base Leverage: {base_leverage}x")
        print(f"📊 Symbol: {BINANCE_SYMBOL}")
        print(f"⏰ Interval: {BINANCE_INTERVAL}")
        print(f"✅ TP PERCENT: {TP_PERCENT}")
        print(f"❌ SL BUFFER POINTS: {SL_BUFFER_POINTS}")
        print("=" * 50)
        
        # Set initial leverage
        binance_client.set_leverage(BINANCE_SYMBOL, base_leverage)
    except Exception as e:
        print(f"Error in initial setup: {e}")
        exit(1)
    
    while True:
        try:
            print("\n🔄 --- New Trading Cycle ---")

            if is_time_in_range_ist():
                print(f"Currently the trade would be taking place since the time status is {is_time_in_range_ist()}")
                # Step 1: If we have an open position, monitor it first
                if martingale_manager.h_pos != 0:
                    print("📊 Existing position detected - monitoring...")
                    try:
                        position_closed = martingale_manager.monitor_and_close_position(BINANCE_SYMBOL)
                        if position_closed:
                            print("✅ Position monitoring completed")
                            # Continue to next cycle to look for new signals
                            continue
                    except Exception as monitor_e:
                        print(f"Error monitoring position: {monitor_e}")
                        continue
                
                # Step 2: Look for new trading opportunities (only if no position)
                if martingale_manager.can_take_trade():
                # if 1==1:
                    try:
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
                        df.to_csv(f"Binance_Final.csv")

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
                        if entry_signal in DESIRED_TYPES:
                        # if 1==1:
                            try:
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
                                    time.sleep(2) # delay so it immediately doesn't check
                                    martingale_manager.position_order_id = position_order_id

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
                                    df.to_csv(f"Binance_Final.csv")

                                    last_candle = df.iloc[-1]
                                    
                                    if position_order and position_order_id:
                                        print(f"✅ Position order placed: {position_order_id}")
                                        
                                        # Set position status and start monitoring
                                        martingale_manager.set_position(direction, entry_price, sl, tp, trade_amount)
                                        
                                        # The position will be monitored in the next cycle iteration
                                        print("🔄 Position opened - will monitor in next cycle")
                                    else:
                                        print("❌ Failed to place position order")

                                    if last_candle['Signal_Final'] != 0:
                                    # if 1==1:
                                        print(f"function is in check for fake trade function")
                                        martingale_manager.check_for_fake_trade(side=side,time_candle=last_candle['time']) # now we pass the side and time so that the opposite side order is being placed , we can note a time so that once the time has changed then we can exit the condition loop 
                                        
                                    else:
                                        print("❌ Failed to go into fake_trade")
                                        
                                except Exception as order_e:
                                    print(f"❌ Error placing order: {order_e}")
                            except Exception as signal_e:
                                print(f"❌ Error processing signal: {signal_e}")
                        
                        else:
                            print("⏸️ No trading signal detected")
                            
                        # Save data
                        try:
                            df.to_csv("./data.csv")
                        except Exception as save_e:
                            print(f"Error saving data: {save_e}")
                            
                    except Exception as fetch_e:
                        print(f"Error fetching data or processing signals: {fetch_e}")
                        continue
                
                # Status summary
                try:
                    print(f"\n📊 System Status:")
                    print(f"  RM1 Level: {martingale_manager.current_level}")
                    print(f"  Next Leverage: {martingale_manager.get_leverage()}x")
                    print(f"  Capital: ${martingale_manager.base_capital}")
                    print(f"  Position: h_pos = {martingale_manager.h_pos}")
                except Exception as status_e:
                    print(f"Error displaying status: {status_e}")
                
                # Only sleep if no position (if position exists, monitoring handles timing)
                if martingale_manager.h_pos == 0:
                    try:
                        # interval_seconds = interval_to_seconds(BINANCE_INTERVAL)
                        print(f"💤 Sleeping for {3} seconds...")
                        import time
                        time.sleep(3)
                    except Exception as sleep_e:
                        print(f"Error during sleep: {sleep_e}")
                        import time
                        time.sleep(60)  # Fallback sleep
            else:
                time.sleep(60)
                
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            import time
            time.sleep(60)  # Wait 1 minute before retrying
            continue