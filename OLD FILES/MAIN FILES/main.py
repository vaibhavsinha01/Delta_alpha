import pandas as pd
import time
from datetime import datetime
from config import *
# from indicators.rsi import calculate_rsi
# from indicators.rsi_gaizy import apply_rsi_gaizy_color
# from indicators.range_filter import calculate_range_filter
# from indicators.ib_box import detect_ib_box
# from strategy.entry_logic import generate_trade_signals
# from strategy.martingale import MartingaleManager
# from trade_manager.risk import RiskManager
# from trade_manager.trade_state import TradeStateManager
# from utils.binance_client import BinanceClient

from module.rf import RangeFilter
from module.ib_indicator import calculate_inside_ib_box
from module.rsi_gaizy import RSIGainzy
from module.rsi_buy_sell import RSIBuySellIndicator
from binance_client_ import BinanceClient
from important import *
import warnings

# Suppress specific FutureWarnings from pandas
warnings.simplefilter(action='ignore', category=FutureWarning)

class MartingaleManager:
    def __init__(self, base_amount, max_steps, multiplier, mode='RM1'):
        self.base_amount = base_amount
        self.max_steps = max_steps
        self.multiplier = multiplier
        self.mode = mode
        self.current_step = 0
        self.last_win_amount = 0
        self.current_capital = base_amount

    def get_trade_amount(self):
        if self.mode == 'RM1':
            # Classic martingale with leverage
            leverage = 2 ** self.current_step # 1->2->8 but what want is 1->2->4
            # leverage = 2*self.current_step
            return self.base_amount * leverage
        else:  # RM2
            return self.current_capital

    def update_result(self, result, pnl):
        if result == 'win':
            if self.mode == 'RM2':
                # Add Y/31 to capital after win
                self.current_capital += (pnl / 31)
            self.current_step = 0
            self.last_win_amount = pnl
        else:
            if self.current_step < self.max_steps:
                self.current_step += 1
            else:
                self.current_step = 0

    def place_order_with_leverage(self, binance_client, symbol, side, quantity, lav_object):
        # Update leverage manager based on last trade success
        if not lav_object.last_trade_suc:
            # Don't multiply the object, just update the step for failed trades
            pass  # The leverage is already handled in calc_lev() method

        # Set leverage using the corrected method
        leverage_response = binance_client.set_leverage(symbol, lav_object.calc_lev())
        if not leverage_response:
            return None

        # Then place order
        order = binance_client.place_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=round(quantity, 5)
        )
        return order

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

    # def is_drawdown_exceeded(self):
    #     return self.max_drawdown > 20  # 20% max drawdown limit

class TradeStateManager:
    def __init__(self):
        self.active_trade = False
        self.current_conditions = {}
        self.x_loss_count = 0
        self.entry_price = 0

    def check_conditions_changed(self, new_conditions):
        if not self.current_conditions:
            self.current_conditions = new_conditions
            return False
        return self.current_conditions != new_conditions

    def calculate_x_loss(self, current_price):
        return abs(current_price - self.entry_price)

    def should_trigger_martingale(self):
        return self.x_loss_count >= 3

    def close_trade(self, result, points=None):
        self.active_trade = False
        if result == 'x_loss':
            self.x_loss_count += 1
        else:
            self.x_loss_count = 0

class LeverageManager:
    def __init__(self, max_leverage=20):
        self.max_leverage = max_leverage
        self.current_leverage = 1
        self.last_trade_suc = True
        self.num = 1
        self.lev = {1:1, 2:2, 3:4, 4:8, 5:16}

    def calculate_leverage(self, martingale_step):
        # Calculate leverage based on martingale step
        # Fixed to start from 1 instead of 2
        if martingale_step == 1:
            return 1
        leverage = min(2 ** (martingale_step - 1), self.max_leverage)
        return leverage

    def validate_leverage(self, leverage):
        return 1 <= leverage <= self.max_leverage
    
    def __imul__(self, other): # my instance *= 1,2
        self.current_leverage *= other
        return self
    
    def calc_lev(self):
        return self.lev.get(self.num, 1)  # Default to 1 if num is out of range

    def set_last_trade(self, suc):
        if not suc: 
            if self.num >= 3:  # Changed from == 3 to >= 3 for safety
                self.last_trade_suc = True
                self.num = 1
                return
            else:
                self.last_trade_suc = False
                self.num += 1
                return
            
        self.last_trade_suc = True
        self.num = 1

# Initialize components
# ORDERS = []
rf = RangeFilter()
bsrsi = RSIBuySellIndicator()
Grsi = RSIGainzy()
binance_client = BinanceClient(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=1)
binance_client.login()
# martingale = MartingaleManager(
#     base_amount=INITIAL_CAPITAL,
#     max_steps=MARTINGALE_MAX_STEPS,
#     multiplier=MARTINGALE_MULTIPLIER,
#     mode=MARTINGALE_MODE
# )
risk_manager = RiskManager(SL_BUFFER_POINTS, TP_PERCENT, INITIAL_CAPITAL)
# trade_state_manager = TradeStateManager()
# leverage_manager = LeverageManager()

def interval_to_seconds(interval):
    if interval.endswith('m'):
        return int(interval[:-1]) * 60
    elif interval.endswith('h'):
        return int(interval[:-1]) * 60 * 60
    elif interval.endswith('d'):
        return int(interval[:-1]) * 24 * 60 * 60
    else:
        raise ValueError(f"Unsupported interval: {interval}")

def format_trade_data(direction, entry_price, sl, tp, trade_amount, strategy_type):
    """Format trade data for logging"""
    return {
        'timestamp': datetime.now().isoformat(),
        'symbol': BINANCE_SYMBOL,
        'direction': direction,
        'entry_price': entry_price,
        'sl': sl,
        'tp': tp,
        'amount': trade_amount,
        'strategy': strategy_type
    }

# def check_entry_conditions(row, prev_row, second_last_row):
#     if trade_state_manager.active_trade:
#         return None

#     # Strategy selection based on K parameter
#     if K == 1:  # RSI1 + IB box strategy
#         if row['rsi_buy'] and row['GreenArrow']:
#             return 'buy'
#         elif row['rsi_sell'] and row['RedArrow']:
#             return 'sell'
    
#     elif K == 2:  # RF + IB box strategy
#         if (row['RF_BuySignal'] and row['GreenArrow']) or \
#             (prev_row['RF_BuySignal'] and row['GreenArrow']):
#             return 'buy'
#         elif (row['RF_SellSignal'] and row['RedArrow']) or \
#             (prev_row['RF_SellSignal'] and row['RedArrow']):
#             return 'sell'
    
#     elif K == 3:  # RF + RSI2 strategy
#         if (row['rsi_buy'] and row['RF_BuySignal']) or \
#             (prev_row['rsi_buy'] and row['RF_BuySignal']):
#             return 'buy'
#         elif (row['rsi_sell'] and row['RF_SellSignal']) or \
#             (prev_row['rsi_sell'] and row['RF_SellSignal']):
#             return 'sell'
    
#     else:  # K = 0: All strategies
#         # Check RSI_Gaizy color rules
#         if row['gaizy_color'] == 'black':
#             if row['GreenArrow']:
#                 return 'buy'
#             elif row['RedArrow']:
#                 return 'sell'
#         elif row['gaizy_color'] in ['bright_green', 'dark_green'] and not row.get('used_green', False):
#             if row['GreenArrow']:
#                 row['used_green'] = True
#                 return 'buy'
#         elif row['gaizy_color'] == 'red' and not row.get('used_red', False):
#             if row['RedArrow']:
#                 row['used_red'] = True
#                 return 'sell'
#         elif row['gaizy_color'] == 'pink' and not row.get('used_pink', False):
#             if row['RedArrow']:
#                 row['used_pink'] = True
#                 return 'sell'
#         # else:
#         #     # Check other strategies
#         #     if check_entry_conditions(row, prev_row, second_last_row):
#         #         return check_entry_conditions(row, prev_row, second_last_row)

#     return None

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

    # df.columns = ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
    
    # df = binance_client.get_klines(
    #     symbol=BINANCE_SYMBOL,
    #     interval=BINANCE_INTERVAL,
    #     # start_time=start_time,
    #     # end_time=end_time,
    #     limit=limit
    # )

    # df = execute_signals(
    #     calculate_signals(
    #         convert_to_complete_format(
    #             df
    #         )
    #     )
    # )
    df = pd.read_csv(r"C:\Users\Ahmed Mohamed\Programming\Python\READY\trading - binance _ MIXED\data.csv")

    last_candle = df.iloc[-1]
    # last_candle = df.iloc[584]
    entry_signal = last_candle['Signal_Final']
    
    # important.calculate_heiken_ashi(df)
    # important.calculate_inside_bar_boxes(df)
    # important.calculate_breakout_signal(df)
    # important.calculate_rsi_gaizy_color(df)
    # important.calculate_rsi(df, RSI_PERIOD)
    # important.calculate_range_filter(df, RANGE_FILTER_LENGTH)
    # important.calculate_ib_box(df, IB_BOX_LOOKBACK)
    # df.to_csv("SAMPLEE2.csv")
    # input("Press Enter to continue...")
    # if df is None or len(df) < 20:
    #     print("Not enough data, skipping this cycle.")
    #     time.sleep(60)
    #     continue

    # # Step 2: Calculate indicators
    # calculate_rsi(df, RSI_PERIOD)
    # apply_rsi_gaizy_color(df)
    # calculate_range_filter(df, RANGE_FILTER_LENGTH)
    # detect_ib_box(df, IB_BOX_LOOKBACK)
    
    # # Generate RSI signals for RSI + RF strategy
    # df['RSI_Signal'] = None
    # for i in range(1, len(df)):
    #     if df['RSI'].iloc[i] < 30:
    #         df.at[i, 'RSI_Signal'] = 'buy'
    #     elif df['RSI'].iloc[i] > 70:
    #         df.at[i, 'RSI_Signal'] = 'sell'

    # # Step 3: Generate trade signals
    # signals_df = generate_trade_signals(df, trade_state_manager)
    
    # Step 4: Process latest signal
    i = len(df) - 1
    row = df.iloc[i]
    prev_row = df.iloc[i-1]
    second_last_row = df.iloc[i-2] if i > 1 else prev_row
    
    # Check risk management
    # if risk_manager.is_drawdown_exceeded():
    #     print(f"Max drawdown exceeded. Trading halted.")
    #     break

    # Check entry conditions
    # entry_signal = check_entry_conditions(row, prev_row, second_last_row)
    
    if entry_signal:
        direction = entry_signal
        # print(direction,type(direction))
        entry_price = row['close']
        sl, tp = risk_manager.calculate_sl_tp(entry_price, direction, prev_row, second_last_row)
        
        # Store current conditions for x_loss checking
        # current_conditions = {
        #     'rsi_signal': row.get('rsi_buy') or row.get('rsi_sell'),
        #     'ib_signal': row.get('GreenArrow') or row.get('RedArrow'),
        #     'rf_signal': row.get('RF_BuySignal') or row.get('RF_SellSignal'),
        #     'rsi_gaizy': row.get('gaizy_color')
        # }
        
        # trade_amount = martingale.get_trade_amount()
        
        side = ("BUY" if direction == 'buy' else "SELL")
        trade_amount = binance_client.get_account_balance()/entry_price
        print(f"Open {side} trade at {entry_price} | SL: {sl} | TP: {tp} | Amount: {trade_amount}")
        # print(f"Current leverage step: {leverage_manager.num} | Leverage: {leverage_manager.calc_lev()}")
        
        # Set last trade result before placing order
        last_trade_successful = True
        # if ORDERS:
        #     # Check if last trade was successful (simplified logic)
        #     last_order_tp = ORDERS[-1]['take_profit']
        #     if direction == 'buy':
        #         last_trade_successful = entry_price > last_order_tp
        #     else:
        #         last_trade_successful = entry_price < last_order_tp
        
        # leverage_manager.set_last_trade(last_trade_successful)
        
        # Place order on Binance
        # order = martingale.place_order_with_leverage(
        #     binance_client, 
        #     BINANCE_SYMBOL, 
        #     side, 
        #     leverage_manager.calc_lev(), 
        #     leverage_manager
        # )
        
        binance_client.get_account_balance()
        order = binance_client.check_and_place_order(BINANCE_SYMBOL, side, "MARKET", trade_amount)
        if order:
            # Place stop loss order
            oco_order = binance_client.place_oco_order(symbol=BINANCE_SYMBOL,side=side,type="LIMIT",quantity=trade_amount,current_price=entry_price)
            # oco_order = binance_client.place_oco_order(
            #     symbol=BINANCE_SYMBOL,
            #     side=side,
            #     quantity=round(trade_amount/entry_price, 5),
            #     type="STOP_LOSS_LIMIT",
            #     current_price=entry_price
            # )
            
            # ORDERS.append({
            #     "symbol": BINANCE_SYMBOL,
            #     'take_profit': tp,
            #     'entry_price': entry_price,
            #     'direction': direction,
            #     'timestamp': datetime.now().isoformat()
            # })
            
            print(f"Order placed successfully: {order}")
            print(f"Stop loss order: {oco_order}")
            
            # trade_state_manager.active_trade = True
            # trade_state_manager.entry_price = entry_price
            
            # Log trade data
            strategy_type = "Signal_Final"
            trade_data = format_trade_data(direction, entry_price, sl, tp, trade_amount, strategy_type)
            print(f"Trade data: {trade_data}")
            
        else:
            print("Failed to place order")

    # Step 9: Save data and wait for next cycle
    print("Cycle complete. Sleeping for next interval...")
    # df.to_csv("./data.csv")
    time.sleep(interval_seconds)