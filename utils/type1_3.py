# replace this function with the function to calculate signals 
from config import *
from important import calculate_heiken_ashi

def calculate_signals(df):
    try:
        from module.rf import RangeFilter
        from module.ib_indicator import calculate_inside_ib_box
        from module.rsi_gaizy import RSIGainzy
        from module.rsi_buy_sell import RSIBuySellIndicator
        rf = RangeFilter()
        bsrsi = RSIBuySellIndicator()
        Grsi = RSIGainzy()
        df.rename(columns={'close':'Close','open':'Open','high':'High','low':'Low','volume':'Volume'},inplace=True)
        if MASTER_HEIKEN_CHOICE==1:
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

            signal = 0  

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

            elif last_green_arrow and not arrow_used and new_rf_buy and (i - arrow_signal_candle) == 1:
                signal = 2  # RF + IB_Box buy signal
                arrow_used = True
                last_green_arrow = False
                # print(f"RF + IB_Box BUY signal triggered at candle {i} (Arrow at {arrow_signal_candle}, RF at {i})")
            elif last_red_arrow and not arrow_used and new_rf_sell and (i - arrow_signal_candle) == 1:
                signal = -2  # RF + IB_Box sell signal
                arrow_used = True
                last_red_arrow = False

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
                        signal = 1
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

        df.to_csv('Delta_Final.csv')
        # df.to_csv("data/Delta_Final_main.csv")
        return df
    except Exception as e:
        print(f"Error occured in calculating the signal : {e}")