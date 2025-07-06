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

# Initialize components

rf = RangeFilter()
bsrsi = RSIBuySellIndicator()
Grsi = RSIGainzy()
binance_client = BinanceClient(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=1)
binance_client.login()
risk_manager = RiskManager(SL_BUFFER_POINTS, TP_PERCENT, INITIAL_CAPITAL)


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

while True:
    print("\n--- New Trading Cycle ---")
    
    # Step 1: Fetch and prepare data
    limit = 1000
    interval_seconds = interval_to_seconds(BINANCE_INTERVAL)
    end_time = int(time.time() * 1000)  # Convert to milliseconds
    start_time = end_time - (interval_seconds * 1000 * limit)  # Convert to milliseconds
    
    # df = binance_client.client.get_historical_klines(
    #     symbol=BINANCE_SYMBOL,
    #     interval=BINANCE_INTERVAL,
    #     start_time=start_time,
    #     end_time=end_time,
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
    

    
    # Step 4: Process latest signal
    i = len(df) - 1
    row = df.iloc[i]
    prev_row = df.iloc[i-1]
    second_last_row = df.iloc[i-2] if i > 1 else prev_row

    
    if entry_signal:
        direction = entry_signal
        
        entry_price = row['close']
        sl, tp = risk_manager.calculate_sl_tp(entry_price, direction, prev_row, second_last_row)
        
        
        side = ("BUY" if direction == 'buy' else "SELL")
        trade_amount = round(float(binance_client.get_account_balance())/entry_price,5)
        print(f"Open {side} trade at {entry_price} | SL: {sl} | TP: {tp} | Amount: {trade_amount}")
        
        binance_client.get_account_balance()
        order = binance_client.check_and_place_order(BINANCE_SYMBOL, side, "MARKET", trade_amount)
        if order:
            # Place stop loss order
            oco_order = binance_client.place_oco_order(symbol=BINANCE_SYMBOL,side=side,type="LIMIT",quantity=trade_amount,current_price=entry_price)

            print(f"Order placed successfully: {order}")
            print(f"Stop loss order: {oco_order}")

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