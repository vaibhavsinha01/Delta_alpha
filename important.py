import pandas as pd
from module.rf import RangeFilter
from module.ib_indicator import calculate_inside_ib_box
from module.rsi_gaizy import RSIGainzy
from module.rsi_buy_sell import RSIBuySellIndicator
import pandas as pd
import numpy as np
from datetime import datetime
from config import *


rf = RangeFilter()
bsrsi = RSIBuySellIndicator()
Grsi = RSIGainzy()

def calculate_heiken_ashi(df):
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
        # print("DONE")
    except Exception as e:
        print(f"Error in heiken-ashi calculation : {e}")

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

def calculate_stoploss( entry_price, side, candle_data=None):
    """Calculate stoploss based on 1%, 50 points, or low of 2nd last candle"""
    try:
        stoplosses = []
        
        # 1% stoploss
        if side == "buy":
            sl_1_percent = entry_price * 0.99
            sl_50_points = entry_price - 10
        else:  # sell
            sl_1_percent = entry_price * 1.01
            sl_50_points = entry_price + 10
        
        stoplosses.append(sl_1_percent)
        stoplosses.append(sl_50_points)
        
        # Low of 2nd last candle (if available)
        if candle_data is not None and len(candle_data) >= 2:
            second_last_low = candle_data.iloc[-2]['low']
            if side == "buy":
                stoplosses.append(second_last_low)
            else:  # sell - use high for sell orders
                second_last_high = candle_data.iloc[-2]['high']
                stoplosses.append(second_last_high)
        
        # Choose the most conservative stoploss
        if side == "buy":
            final_sl = max(stoplosses)  # Highest stoploss for buy
            # final_sl = min(stoplosses)
        else:
            final_sl = min(stoplosses)  # Lowest stoploss for sell
            # final_sl = max(stoplosses)
        
        print(f"Calculated stoploss for {side}: {final_sl}")
        return final_sl
        
    except Exception as e:
        print(f"Error in calculate_stoploss: {e}")
        return None

def calculate_takeprofit( entry_price, side):
    """Calculate take profit based on risk-reward ratio"""
    try:
        if side == "buy":
            tp = entry_price * 1.01  # 2% profit
        else:  # sell
            tp = entry_price * 0.99  # 2% profit
        
        print(f"Calculated take profit for {side}: {tp}")
        return tp
        
    except Exception as e:
        print(f"Error in calculate_takeprofit: {e}")
        return None

def calculate_signals(df):
    try:
        df.rename(columns={'close':'Close','open':'Open','high':'High','low':'Low','volume':'Volume'},inplace=True)
        if MASTER_HEIKEN_CHOICE == 1:
            calculate_heiken_ashi(df)
        df = rf.run_filter(df)
        # df['gaizy_color'] = self.Grsi.calculate_signals(df=df)
        df.rename(columns={'Close':'close','Open':'open','High':'high','Low':'low','Volume':'volume'},inplace=True)
        df['rsi'],df['rsi_buy'],df['rsi_sell'] = bsrsi.generate_signals(df['close'])
        df['gaizy_color'] = Grsi.calculate_gainzy_colors(df=df)
        # df,_ = calculate_inside_bar_boxes(df)
        df = calculate_inside_ib_box(df)
        columns_to_drop = [
            'RF_UpperBand', 'RF_LowerBand', 'RF_Filter', 'RF_Trend',
            'IsIB', 'BoxHigh', 'BoxLow', 'BarColor','rsi'
        ]
        df = df.drop(columns=columns_to_drop)

        df = df.tail(200)
        df['Signal_Final'] = 0

        # Initialize signal tracking variables
        last_rf_buy_signal = False
        last_rf_sell_signal = False
        rf_signal_candle = -1
        rf_used = False

        # Initialize Arrow signal tracking variables (added from second code)
        last_green_arrow = False
        last_red_arrow = False
        arrow_signal_candle = -1
        arrow_used = False

        pending_rsi_buy = False
        pending_rsi_sell = False
        rsi_signal_candle = -1

        # Track used RSI_Gaizy lines to ensure only one trade per color line
        used_gaizy_green = False
        used_gaizy_red = False
        used_gaizy_pink = False
        used_gaizy_black = False  # Added this line
        used_gaizy_dark_green = False
        used_gaizy_blue = False

        for i in range(len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i - 1] if i > 0 else None

            # Detect new RF signals (transition from 0 to 1)
            current_rf_buy = row['RF_BuySignal'] == 1
            current_rf_sell = row['RF_SellSignal'] == 1

            new_rf_buy = current_rf_buy and (prev_row is None or prev_row['RF_BuySignal'] != 1)
            new_rf_sell = current_rf_sell and (prev_row is None or prev_row['RF_SellSignal'] != 1)

            # Detect new Arrow signals (added from second code)
            new_green_arrow = row['GreenArrow'] == 1 and (prev_row is None or prev_row['GreenArrow'] != 1)
            new_red_arrow = row['RedArrow'] == 1 and (prev_row is None or prev_row['RedArrow'] != 1)

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

            # Update Arrow signal tracking (added from second code)
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

            # Reset RF signals if they're older than 1 candle and not used
            if (i - rf_signal_candle) > 1 and (last_rf_buy_signal or last_rf_sell_signal):
                last_rf_buy_signal = False
                last_rf_sell_signal = False
                rf_used = False

            # Reset Arrow signals if they're older than 1 candle and not used
            if (i - arrow_signal_candle) > 1 and (last_green_arrow or last_red_arrow):
                last_green_arrow = False
                last_red_arrow = False
                arrow_used = False

            # Detect RSI_Gaizy color changes
            current_gaizy = row['gaizy_color']
            gaizy_changed = prev_row is not None and prev_row['gaizy_color'] != current_gaizy

            # Reset color usage flags when new color appears
            if gaizy_changed:
                if current_gaizy in ['light_green']:
                    used_gaizy_green = False
                elif current_gaizy in ['green']:
                    used_gaizy_dark_green = False
                elif current_gaizy in ['red']:
                    used_gaizy_red = False
                elif current_gaizy in ['pink']:
                    used_gaizy_pink = False
                elif current_gaizy == 'black':  # Added this condition
                    used_gaizy_black = False
                elif current_gaizy == "blue":
                    used_gaizy_blue = False

            signal = 0  # Default

            # === PRIORITY 1: Range Filter (RF) + IB_Box Confirmation ===
            # This gets highest priority to ensure it's fulfilled
            
            # Scenario A: RF signal first, then Arrow signal
            # Condition A1: RF and Arrow signals in same candle
            if new_rf_buy and row['GreenArrow'] == 1 and not rf_used:
                signal = 2  # RF + IB_Box buy signal
                rf_used = True
                last_rf_buy_signal = False
                # print(f"RF + IB_Box BUY signal triggered at candle {i} (same candle)")
            elif new_rf_sell and row['RedArrow'] == 1 and not rf_used:
                signal = -2  # RF + IB_Box sell signal
                rf_used = True
                last_rf_sell_signal = False
                # print(f"RF + IB_Box SELL signal triggered at candle {i} (same candle)")
            
            # Condition A2: RF signal, then Arrow signal in immediate next candle
            elif last_rf_buy_signal and not rf_used and row['GreenArrow'] == 1 and (i - rf_signal_candle) == 1:
                signal = 2  # RF + IB_Box buy signal
                rf_used = True
                last_rf_buy_signal = False
                # print(f"RF + IB_Box BUY signal triggered at candle {i} (RF at {rf_signal_candle}, Arrow at {i})")
            elif last_rf_sell_signal and not rf_used and row['RedArrow'] == 1 and (i - rf_signal_candle) == 1:
                signal = -2  # RF + IB_Box sell signal
                rf_used = True
                last_rf_sell_signal = False
                # print(f"RF + IB_Box SELL signal triggered at candle {i} (RF at {rf_signal_candle}, Arrow at {i})")

            # Scenario B: Arrow signal first, then RF signal
            # Condition B1: Arrow signal, then RF signal in immediate next candle
            elif last_green_arrow and not arrow_used and new_rf_buy and (i - arrow_signal_candle) == 1:
                signal = 2  # RF + IB_Box buy signal
                arrow_used = True
                last_green_arrow = False
                # print(f"RF + IB_Box BUY signal triggered at candle {i} (Arrow at {arrow_signal_candle}, RF at {i})")
            elif last_red_arrow and not arrow_used and new_rf_sell and (i - arrow_signal_candle) == 1:
                signal = -2  # RF + IB_Box sell signal
                arrow_used = True
                last_red_arrow = False
                # print(f"RF + IB_Box SELL signal triggered at candle {i} (Arrow at {arrow_signal_candle}, RF at {i})")

            # === PRIORITY 2: RSI_Gaizy Integration + IB_box ===
            # Only execute if no RF + IB_Box signal was triggered
            elif signal == 0:
                # Each RSI_Gaizy color line can trigger only one trade
                if current_gaizy in ['light_green'] and not used_gaizy_green:
                    # Green line → Triggers Green Box trade only
                    if row['GreenArrow'] == 1:
                        signal = 1
                        used_gaizy_green = True
                        # print(f"RSI_Gaizy GREEN + IB_Box signal triggered at candle {i}")
                elif current_gaizy in ['green'] and not used_gaizy_dark_green:
                    if row['GreenArrow'] == 1:
                        signal = 1 
                        used_gaizy_dark_green = True
                        # print(f"RSI_Gaizy GREEN + IB_box triggered at candle {i}")
                elif current_gaizy == 'red' and not used_gaizy_red:
                    # Red line → Triggers Red Box trade only
                    if row['RedArrow'] == 1:
                        signal = -1
                        used_gaizy_red = True
                        # print(f"RSI_Gaizy RED + IB_Box signal triggered at candle {i}")
                elif current_gaizy == 'pink' and not used_gaizy_pink:
                    # Pink strong sell → Triggers Red Box trade only
                    if row['RedArrow'] == 1:
                        signal = -1
                        used_gaizy_pink = True
                        # print(f"RSI_Gaizy PINK + IB_Box signal triggered at candle {i}")
                elif current_gaizy == 'black' and not used_gaizy_black:  # Added usage check
                    # Black signal → Take trade based on IB box
                    if row['GreenArrow'] == 1:
                        signal = 1
                        used_gaizy_black = True  # Mark as used
                        # print(f"RSI_Gaizy BLACK + Green IB_Box signal triggered at candle {i}")
                    elif row['RedArrow'] == 1:
                        signal = -1
                        used_gaizy_black = True  # Mark as used
                        # print(f"RSI_Gaizy BLACK + Red IB_Box signal triggered at candle {i}")
                elif current_gaizy == 'blue' and not used_gaizy_blue:
                    if row['GreenArrow'] == 1:
                        signal = 1
                        used_gaizy_blue = True
                    elif row['RedArrow'] == 1:
                        signal = -1
                        used_gaizy_blue = True

            # Mark RSI_Gaizy colors as used when ANY signal is triggered (including RF + IB_Box)
            if signal != 0:
                if current_gaizy in ['light_green']:
                    used_gaizy_green = True
                elif current_gaizy == 'red':
                    used_gaizy_red = True
                elif current_gaizy == 'pink':
                    used_gaizy_pink = True
                elif current_gaizy == 'black':
                    used_gaizy_black = True
                elif current_gaizy in ['green']:
                    used_gaizy_dark_green = True
                elif current_gaizy == 'blue':
                    used_gaizy_blue = True

            # === PRIORITY 3: RSI Buy/sell + RF Logic ===
            # Only execute if no higher priority signal was triggered
            if signal == 0:
                # Track RSI signals
                if row['rsi_buy'] == 1:
                    pending_rsi_buy = True
                    rsi_signal_candle = i
                elif row['rsi_sell'] == 1:
                    pending_rsi_sell = True
                    rsi_signal_candle = i

                # Check for RF confirmation after RSI signal
                if pending_rsi_buy and current_rf_buy and (i - rsi_signal_candle) <= 1 and not rf_used:
                    signal = 3
                    pending_rsi_buy = False
                    rf_used = True
                    last_rf_buy_signal = False
                    # print(f"RSI + RF BUY signal triggered at candle {i}")
                elif pending_rsi_sell and current_rf_sell and (i - rsi_signal_candle) <= 1 and not rf_used:
                    signal = -3
                    pending_rsi_sell = False
                    rf_used = True
                    last_rf_sell_signal = False
                    # print(f"RSI + RF SELL signal triggered at candle {i}")

                # Reset pending RSI signals if too much time has passed (more than 2 candles)
                if pending_rsi_buy and (i - rsi_signal_candle) > 2:
                    pending_rsi_buy = False
                if pending_rsi_sell and (i - rsi_signal_candle) > 2:
                    pending_rsi_sell = False

            # Assign the final signal
            df.iat[i, df.columns.get_loc('Signal_Final')] = signal

        # df.to_csv('ETHUSD_Final.csv')
        df.to_csv("data/ETHUSD_Final_main.csv")
        return df
    except Exception as e:
        print(f"Error occured in calculating the signal : {e}")

def execute_signals(df):
    try:

        # === Execute Latest Signal ===
        last_candle = df.iloc[-1]
        last_signal = last_candle['Signal_Final']
        # print(f"the current order id is {self.current_order_id}")
        print(f"the last signal is {last_signal}")

        if last_signal != 0:
            print(f"a new order would be placed since last signal is {last_signal}")
            current_price = float(last_candle['close'])
            # self.last_price = current_price
            # self.trade_entry_price = current_price  # Store entry price for win/loss calculation
            side = "buy" if last_signal > 0 else "sell"

            sl_price = calculate_stoploss(current_price, side, df)
            tp_price = calculate_takeprofit(current_price, side)
            # self.last_sl_price = sl_price
            # self.last_tp_price = tp_price
            da = datetime.now()
            print(f"ORDER AT {da} TYPE : {side}")
            # if sl_price is not None and tp_price is not None:
            #     stop_limit = sl_price + 10 if side == "buy" else sl_price + 10
            #     tp_limit = tp_price - 10 if side == "buy" else tp_price + 10
            #     self.set_leverage_delta(value=self.base_leverage,product_id="1699")
            #     # self.leverage_check()
            #     self.get_base_margin_size() # updates the self.base size
            #     self.place_order_market(side=side, size=int(self.base))
            #     # import time
            #     # time.sleep(1) # sleep for 1 seconds

            #     self.place_order_bracket_limit(
            #         limit_price=str(current_price),
            #         stop_price=str(sl_price),
            #         take_profit_price=str(tp_price),
            #         stop_limit_price=str(stop_limit),
            #         take_profit_limit_price=str(tp_limit),
            #         side=side,
            #         size=int(self.base)
            #     )
        return df 

    except Exception as e:
        print(f"Error occurred in execution: {e}")
        import traceback
        traceback.print_exc()

def convert_to_complete_format(df):
    # df = pd.read_csv('Sample.csv')

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Calculate price changes and patterns
    df['price_change'] = df['close'].diff()
    df['price_change_pct'] = df['close'].pct_change()

    # Calculate RSI (Relative Strength Index)
    def calculate_rsi(data, periods=14):
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    df['RSI'] = calculate_rsi(df['close'])

    # Calculate signals based on price movements and RSI
    df['RF_BuySignal'] = ((df['price_change'] > 0) & (df['RSI'] < 30)).astype(int)
    df['RF_SellSignal'] = ((df['price_change'] < 0) & (df['RSI'] > 70)).astype(int)

    # RSI buy/sell signals
    df['rsi_buy'] = df['RSI'] < 30
    df['rsi_sell'] = df['RSI'] > 70

    # Calculate gaizy color based on price movement
    df['gaizy_color'] = np.where(df['close'] > df['open'], 'green', 'black')

    # Calculate Green and Red arrows based on significant price movements
    df['GreenArrow'] = (df['price_change_pct'] > 0.001) & (df['close'] > df['open'])
    df['RedArrow'] = (df['price_change_pct'] < -0.001) & (df['close'] < df['open'])

    # Rename columns to match Sample2.csv
    df = df.rename(columns={
        'timestamp': 'Timestamp',
        'Volume': 'volume',
        'close': 'close',
        'open': 'open',
        'high': 'high',
        'low': 'low'
    })

    # Add time column (Unix timestamp)
    df['time'] = df['Timestamp'].astype(np.int64) // 10**9

    # Reorder columns to match Sample2.csv
    columns_order = [
        'time', 'volume', 'Timestamp', 'close', 'open', 'high', 'low',
        'RF_BuySignal', 'RF_SellSignal', 'rsi_buy', 'rsi_sell',
        'gaizy_color', 'GreenArrow', 'RedArrow'
    ]
    df = df[columns_order]

    # Save the transformed data
    # df.to_csv('Sample2.csv', index=False)
    # print("Transformation completed successfully!") 
    return df

# execute_signals(
#     calculate_signals(
#         convert_to_complete_format()
#     )
# )

# execute_signals(
#     calculate_signals(
#         pd.read_csv('Sample2.csv')
#     )
# )