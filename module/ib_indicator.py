# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# # from module.ib_box import calculate_inside_bar_boxes, plot_inside_bar_boxes
# from module.ib_box import *

# def calculate_heikin_ashi(df):
#     """
#     Calculate Heikin-Ashi candles from regular OHLC data.
    
#     Parameters:
#     -----------
#     df : pandas.DataFrame
#         DataFrame with 'open', 'high', 'low', 'close' columns
        
#     Returns:
#     --------
#     pandas.DataFrame
#         DataFrame with Heikin-Ashi candles
#     """
#     ha_df = df.copy()
    
#     # Ensure column names are lowercase
#     if not all(col in ha_df.columns for col in ['open', 'high', 'low', 'close']):
#         # Try to convert from capitalized column names
#         ha_df.rename(columns={
#             'Open': 'open', 
#             'High': 'high', 
#             'Low': 'low', 
#             'Close': 'close'
#         }, inplace=True, errors='ignore')
    
#     # Calculate Heikin-Ashi candles
#     ha_df['ha_close'] = (ha_df['open'] + ha_df['high'] + ha_df['low'] + ha_df['close']) / 4
    
#     # Initialize first Heikin-Ashi candle
#     ha_df.loc[ha_df.index[0], 'ha_open'] = (ha_df.loc[ha_df.index[0], 'open'] + 
#                                            ha_df.loc[ha_df.index[0], 'close']) / 2
    
#     # Calculate remaining Heikin-Ashi candles
#     for i in range(1, len(ha_df)):
#         ha_df.loc[ha_df.index[i], 'ha_open'] = (ha_df.loc[ha_df.index[i-1], 'ha_open'] + 
#                                                ha_df.loc[ha_df.index[i-1], 'ha_close']) / 2
    
#     ha_df['ha_high'] = ha_df[['high', 'ha_open', 'ha_close']].max(axis=1)
#     ha_df['ha_low'] = ha_df[['low', 'ha_open', 'ha_close']].min(axis=1)
    
#     # Replace original OHLC with Heikin-Ashi values
#     ha_df['open'] = ha_df['ha_open']
#     ha_df['high'] = ha_df['ha_high']
#     ha_df['low'] = ha_df['ha_low']
#     ha_df['close'] = ha_df['ha_close']
    
#     # Drop temporary columns
#     ha_df.drop(['ha_open', 'ha_high', 'ha_low', 'ha_close'], axis=1, inplace=True)
    
#     return ha_df

# def apply_inside_bar_boxes(df, high_low_buffer=0, bar_highlight=True, 
#                           show_only_last_box=False, show_break=True, 
#                           bg_color='blue', bg_transparency=90, inside_bars_color='orange', 
#                           mintick=0.05, plot=False, use_heikin_ashi=False): # i have set heiken-ashi to false since I have already calculated the heiken-ashi in the code
#     """
#     Apply Inside Bar Boxes indicator to OHLC data.
    
#     Parameters:
#     -----------
#     df : pandas.DataFrame
#         DataFrame with 'open', 'high', 'low', 'close' columns
#     high_low_buffer : float
#         Buffer zone around high-low (in mintick units)
#     bar_highlight : bool
#         Whether to highlight inside bars
#     show_only_last_box : bool
#         Show only the last box
#     show_break : bool
#         Show box breakouts
#     bg_color : str
#         Background color for boxes
#     bg_transparency : int
#         Box transparency (0-100)
#     inside_bars_color : str
#         Color for inside bars
#     mintick : float
#         Minimum tick size
#     plot : bool
#         Whether to plot the result
#     use_heikin_ashi : bool
#         Whether to use Heikin-Ashi candles
        
#     Returns:
#     --------
#     tuple
#         (box_high Series, box_low Series)
#     """
#     # Ensure column names are lowercase
#     df = df.copy()
#     if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
#         # Try to convert from capitalized column names
#         df.rename(columns={
#             'Open': 'open', 
#             'High': 'high', 
#             'Low': 'low', 
#             'Close': 'close'
#         }, inplace=True, errors='ignore')
    
#     # Convert to Heikin-Ashi if requested
#     if use_heikin_ashi:
#         df = calculate_heikin_ashi(df)
    
#     # Calculate inside bar boxes
#     result_df, boxes = calculate_inside_bar_boxes(
#         df, 
#         high_low_buffer=high_low_buffer,
#         mintick=mintick,
#         bar_highlight=bar_highlight,
#         show_only_last_box=show_only_last_box,
#         show_break=show_break,
#         bg_color=bg_color,
#         bg_transparency=bg_transparency,
#         inside_bars_color=inside_bars_color
#     )
    
#     # Plot if requested
#     if plot:
#         plot_inside_bar_boxes(result_df)
    
#     # Extract box_high and box_low as separate Series
#     box_high = result_df['BoxHigh']
#     box_low = result_df['BoxLow']
    
#     # Return only box_high and box_low
#     return box_high, box_low

# def generate_synthetic_ohlc_data(n_periods=120, base_price=150.0, seed=42):
#     """
#     Generate synthetic OHLC data using numpy random with seed for reproducibility.
    
#     Parameters:
#     -----------
#     n_periods : int
#         Number of periods to generate
#     base_price : float
#         Starting price level
#     seed : int
#         Random seed for reproducibility
        
#     Returns:
#     --------
#     pandas.DataFrame
#         DataFrame with OHLC data
#     """
#     np.random.seed(seed)
    
#     # Generate random walk for closing prices
#     returns = np.random.normal(0, 0.02, n_periods)  # 2% daily volatility
#     prices = [base_price]
    
#     for ret in returns:
#         prices.append(prices[-1] * (1 + ret))
    
#     prices = np.array(prices[1:])  # Remove the initial base_price
    
#     # Generate OHLC data
#     ohlc_data = []
    
#     for i in range(n_periods):
#         if i == 0:
#             open_price = base_price
#         else:
#             open_price = ohlc_data[i-1]['close']
        
#         close_price = prices[i]
        
#         # Generate high and low with some randomness
#         daily_range = abs(close_price - open_price) + np.random.uniform(0.5, 2.5)
#         high_price = max(open_price, close_price) + np.random.uniform(0, daily_range * 0.3)
#         low_price = min(open_price, close_price) - np.random.uniform(0, daily_range * 0.3)
        
#         ohlc_data.append({
#             'open': round(open_price, 2),
#             'high': round(high_price, 2),
#             'low': round(low_price, 2),
#             'close': round(close_price, 2)
#         })
    
#     # Create DataFrame with date index
#     dates = pd.date_range(start='2024-01-01', periods=n_periods, freq='D')
#     df = pd.DataFrame(ohlc_data, index=dates)
    
#     return df

# # Example usage
# if __name__ == "__main__":
#     # Generate synthetic OHLC data
#     np.random.seed(42)  # Set seed for reproducible results
#     data = generate_synthetic_ohlc_data(n_periods=120, base_price=150.0, seed=42)
    
#     print("Generated synthetic OHLC data:")
#     print(data.head(10))
#     print(f"\nData shape: {data.shape}")
#     print(f"Date range: {data.index[0]} to {data.index[-1]}")
    
#     # Apply indicator
#     box_high, box_low = apply_inside_bar_boxes(
#         data,
#         high_low_buffer=0,
#         bar_highlight=True,
#         show_only_last_box=False,
#         show_break=True,
#         plot=True,
#         use_heikin_ashi=True
#     )
    
#     # Display the first few rows of box_high and box_low
#     print("\nBox High values:")
#     print(box_high[box_high.notna()].head())
    
#     print("\nBox Low values:")
#     print(box_low[box_low.notna()].head())

# import pandas as pd
# import numpy as np

# def calculate_inside_ib_box(df, high_low_buffer=0.0, mintick=0.05, bar_highlight=True, 
#                            show_only_last_box=False, show_break=True):
#     """
#     Calculate Inside Bar Boxes based on OHLC data.
    
#     Parameters:
#     -----------
#     df : pandas.DataFrame
#         DataFrame with columns: 'open', 'high', 'low', 'close'
#     high_low_buffer : float, default=0.0
#         Buffer zone around high-low (in mintick units)
#     mintick : float, default=0.05
#         Minimum tick size
#     bar_highlight : bool, default=True
#         Whether to highlight inside bars
#     show_only_last_box : bool, default=False
#         Show only the last box (affects box tracking)
#     show_break : bool, default=True
#         Show box breaks (breakout signals)
    
#     Returns:
#     --------
#     pandas.DataFrame
#         DataFrame containing:
#         - Original OHLC data
#         - IsIB: Boolean indicating inside bars
#         - BoxHigh: High of the current box
#         - BoxLow: Low of the current box
#         - GreenArrow: Boolean indicating upward breakout
#         - RedArrow: Boolean indicating downward breakout
#         - BarColor: Color indicator for inside bars
#     """
    
#     # Validate input DataFrame
#     required_cols = ['open', 'high', 'low', 'close']
#     if not all(col in df.columns for col in required_cols):
#         raise ValueError(f"DataFrame must contain columns: {required_cols}")
    
#     # Create a copy to avoid modifying original data
#     df = df.copy()
    
#     # Ensure datetime index if datetime column exists
#     if 'datetime' in df.columns:
#         df['datetime'] = pd.to_datetime(df['datetime'])
#         df.set_index('datetime', inplace=True)
#     elif not isinstance(df.index, pd.DatetimeIndex):
#         df.index = pd.to_datetime(df.index)
    
#     # Initialize columns
#     df['IsIB'] = False
#     df['BoxHigh'] = np.nan
#     df['BoxLow'] = np.nan
#     df['GreenArrow'] = False
#     df['RedArrow'] = False
#     df['BarColor'] = np.nan
    
#     # State tracking variables (equivalent to PineScript vars)
#     box_high = np.nan
#     box_low = np.nan
#     bar_index = 1
#     f_flag = False  # Equivalent to 'f' in PineScript
    
#     # Process each bar - starting from second bar (index 1)
#     for i in range(1, len(df)):
#         prev = df.iloc[i - 1]  # Previous bar
#         curr = df.iloc[i]      # Current bar
#         prev_is_ib = df.iloc[i-1]['IsIB'] if i > 1 else False  # Previous bar IB status
        
#         # Calculate buffered high/low for inside bar logic
#         hp = prev['high'] + high_low_buffer * mintick
#         lp = prev['low'] - high_low_buffer * mintick
        
#         # Inside bar condition - exactly as in PineScript
#         is_ib = (curr['close'] <= hp and curr['close'] >= lp and 
#                  curr['open'] <= hp and curr['open'] >= lp)
        
#         df.iat[i, df.columns.get_loc('IsIB')] = is_ib
        
#         # Bar color logic
#         if is_ib and bar_highlight:
#             df.iat[i, df.columns.get_loc('BarColor')] = 'orange'
        
#         # Box logic - simulating barstate.isconfirmed with each row calculation
        
#         # Condition 1: New inside bar (current is IB, previous was not)
#         if is_ib and not prev_is_ib:
#             box_high = prev['high']
#             box_low = prev['low']
#             f_flag = True
            
#             # Store box high/low values in dataframe
#             df.iat[i, df.columns.get_loc('BoxHigh')] = box_high
#             df.iat[i, df.columns.get_loc('BoxLow')] = box_low
            
#             bar_index = bar_index + 1
            
#         # Condition 2: Continuing inside bar sequence
#         elif is_ib and prev_is_ib:
#             if not np.isnan(box_high):
#                 df.iat[i, df.columns.get_loc('BoxHigh')] = box_high
#                 df.iat[i, df.columns.get_loc('BoxLow')] = box_low
#             bar_index = bar_index + 1
            
#         # Condition 3: End of inside bar sequence (prev was IB, current is not)
#         elif prev_is_ib and not is_ib:
#             # Check for breakouts exactly as in PineScript
#             if show_break and f_flag:
#                 if prev['close'] <= box_high and curr['close'] > box_high:
#                     df.iat[i, df.columns.get_loc('GreenArrow')] = True
#                 elif prev['close'] >= box_low and curr['close'] < box_low:
#                     df.iat[i, df.columns.get_loc('RedArrow')] = True
            
#             bar_index = 1
            
#         # Condition 4: No inside bar sequence
#         elif not prev_is_ib and not is_ib:
#             f_flag = False
    
#     return df

import pandas as pd
import numpy as np

def calculate_inside_ib_box(df, high_low_buffer=0.0, mintick=0.05, bar_highlight=True, 
                           show_only_last_box=False, show_break=True):
    """
    Calculate Inside Bar Boxes - CORRECTED to exactly match PineScript logic.
    
    KEY CORRECTIONS MADE:
    1. Fixed isInsideBar() function parameter interpretation
    2. Corrected barIndex usage and incrementing logic  
    3. Fixed box reference to use high[1]/low[1] (previous bar)
    4. Implemented proper crossover/crossunder detection
    
    The PineScript uses a dynamic barIndex that starts at 1 and increments during
    inside bar sequences. The isInsideBar(barIndex) function checks if current bar
    is inside the bar that's barIndex positions back.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with columns: 'open', 'high', 'low', 'close'
    high_low_buffer : float, default=0.0
        Buffer zone around high-low (in mintick units)
    mintick : float, default=0.05
        Minimum tick size
    bar_highlight : bool, default=True
        Whether to highlight inside bars
    show_only_last_box : bool, default=False
        Show only the last box (affects box tracking)
    show_break : bool, default=True
        Show box breaks (breakout signals)
    
    Returns:
    --------
    pandas.DataFrame
        DataFrame containing:
        - Original OHLC data
        - IsIB: Boolean indicating inside bars
        - BoxHigh: High of the current box
        - BoxLow: Low of the current box
        - GreenArrow: Boolean indicating upward breakout
        - RedArrow: Boolean indicating downward breakout
        - BarColor: Color indicator for inside bars
        - BarIndex: Current barIndex value (for debugging)
    """
    
    # Validate input DataFrame
    required_cols = ['open', 'high', 'low', 'close']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")
    
    # Create a copy to avoid modifying original data
    df = df.copy()
    
    # Ensure datetime index if datetime column exists
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    # Initialize columns
    df['IsIB'] = False
    df['BoxHigh'] = np.nan
    df['BoxLow'] = np.nan
    df['GreenArrow'] = False
    df['RedArrow'] = False
    df['BarColor'] = np.nan
    df['BarIndex'] = np.nan  # For debugging
    
    # State tracking variables (equivalent to PineScript vars)
    box_high = np.nan
    box_low = np.nan
    bar_index = 1  # varip int barIndex = 1
    f_flag = False  # varip bool f = false
    
    def is_inside_bar(current_idx, lookback_bars, buffer, mintick_size):
        """
        CORRECTED: Exact implementation of PineScript isInsideBar(previousBar) function.
        
        PineScript function:
        isInsideBar(previousBar) =>
            hp = high[previousBar]+highLowBuffer*syminfo.mintick
            lp = low[previousBar]+highLowBuffer*syminfo.mintick
            isIB = (close <= hp and close >= lp) and (open <= hp and open >= lp)
            isIB
            
        This checks if CURRENT bar is inside the bar that's 'lookback_bars' positions back.
        """
        # Must have enough history to look back
        if current_idx < lookback_bars:
            return False
            
        # Get the reference bar (lookback_bars positions back from current)
        reference_bar_idx = current_idx - lookback_bars
        reference_bar = df.iloc[reference_bar_idx]
        current_bar = df.iloc[current_idx]
        
        # Calculate buffered high/low of reference bar
        hp = reference_bar['high'] + buffer * mintick_size
        lp = reference_bar['low'] - buffer * mintick_size
        
        # CORRECTED: Check if current bar's open AND close are within reference bar's buffered range
        is_ib = (current_bar['close'] <= hp and current_bar['close'] >= lp and 
                current_bar['open'] <= hp and current_bar['open'] >= lp)
        
        return is_ib
    
    # Process each bar starting from index 1 (need at least 1 previous bar)
    for i in range(1, len(df)):
        
        # Store current barIndex for debugging
        df.loc[df.index[i], 'BarIndex'] = bar_index
        
        # CORRECTED: Call isInsideBar(barIndex) exactly like PineScript
        # This checks if current bar is inside the bar that's barIndex positions back
        is_ib = is_inside_bar(i, bar_index, high_low_buffer, mintick)
        
        # Get previous IsIB status (isIB[1] in PineScript)
        prev_is_ib = df.loc[df.index[i-1], 'IsIB'] if i > 0 else False
        
        # Set current IsIB status
        df.loc[df.index[i], 'IsIB'] = is_ib
        
        # Bar color logic
        if is_ib and bar_highlight:
            df.loc[df.index[i], 'BarColor'] = 'orange'
        
        # CORRECTED: Box logic matching PineScript conditions exactly
        
        # Condition 1: isIB and not isIB[1] and barstate.isconfirmed
        # New inside bar sequence starts
        if is_ib and not prev_is_ib:
            # CORRECTED: Use high[1] and low[1] - the PREVIOUS bar's high/low
            prev_bar = df.iloc[i - 1]
            box_high = prev_bar['high']  # high[1]
            box_low = prev_bar['low']    # low[1]
            f_flag = True
            
            # Store box values
            df.loc[df.index[i], 'BoxHigh'] = box_high
            df.loc[df.index[i], 'BoxLow'] = box_low
            
            # CORRECTED: Increment barIndex AFTER setting up the box
            bar_index = bar_index + 1
            
        # Condition 2: isIB and isIB[1] and barstate.isconfirmed
        # Continuing inside bar sequence
        elif is_ib and prev_is_ib:
            # Continue with existing box
            if not np.isnan(box_high):
                df.loc[df.index[i], 'BoxHigh'] = box_high
                df.loc[df.index[i], 'BoxLow'] = box_low
            
            # CORRECTED: Increment barIndex to extend the lookback
            bar_index = bar_index + 1
            
        # Condition 3: isIB[1] and not isIB and barstate.isconfirmed
        # End of inside bar sequence
        elif prev_is_ib and not is_ib:
            # CORRECTED: Reset barIndex to 1 (restart counting)
            bar_index = 1
            # Keep f_flag true for breakout detection
            
        # Condition 4: not isIB[1] and not isIB
        # No inside bar sequence active
        elif not prev_is_ib and not is_ib:
            f_flag = False
        
        # CORRECTED: Breakout detection using proper crossover/crossunder logic
        # PineScript: plotshape(showBreak and f and crossover(close, boxHigh), ...)
        # PineScript: plotshape(showBreak and f and crossunder(close, boxLow), ...)
        if show_break and f_flag and not np.isnan(box_high) and not np.isnan(box_low):
            if i > 0:
                prev_close = df.iloc[i-1]['close']
                curr_close = df.iloc[i]['close']
                
                # Green arrow: crossover (close crosses above boxHigh)
                # crossover(close, boxHigh) = prev_close <= boxHigh and curr_close > boxHigh
                if prev_close <= box_high and curr_close > box_high:
                    df.loc[df.index[i], 'GreenArrow'] = True
                    
                # Red arrow: crossunder (close crosses below boxLow)  
                # crossunder(close, boxLow) = prev_close >= boxLow and curr_close < boxLow
                elif prev_close >= box_low and curr_close < box_low:
                    df.loc[df.index[i], 'RedArrow'] = True
    
    return df


def test_inside_bar_logic():
    """
    Test function with detailed analysis to verify the corrected logic.
    Creates sample data designed to trigger inside bar patterns.
    """
    # Create sample data with clear inside bar patterns
    data = {
        'datetime': pd.date_range('2023-01-01', periods=20, freq='1H'),
        'open':  [100.0, 102.0, 101.5, 101.8, 101.2, 101.6, 101.4, 103.0, 102.5, 102.7, 
                  104.0, 103.8, 103.5, 103.2, 105.0, 104.2, 104.5, 106.0, 105.5, 107.0],
        'high':  [101.0, 103.0, 102.0, 102.0, 101.5, 101.9, 101.7, 104.0, 103.0, 103.2, 
                  105.0, 104.5, 104.0, 103.8, 106.0, 105.0, 105.2, 107.0, 106.5, 108.0],
        'low':   [99.5,  101.5, 101.0, 101.5, 101.0, 101.3, 101.1, 102.8, 102.0, 102.2, 
                  103.5, 103.0, 103.2, 102.9, 104.5, 103.8, 104.0, 105.5, 105.0, 106.5],
        'close': [100.5, 102.5, 101.8, 101.6, 101.3, 101.7, 101.5, 103.5, 102.8, 102.9, 
                  104.2, 104.0, 103.8, 103.1, 105.5, 104.5, 104.8, 106.5, 106.0, 107.5]
    }
    
    df = pd.DataFrame(data)
    
    print("Original OHLC Data:")
    print("=" * 80)
    print(df[['open', 'high', 'low', 'close']].round(2))
    print()
    
    # Calculate inside bar boxes with corrected logic
    result = calculate_inside_ib_box(df, high_low_buffer=0, mintick=0.05, 
                                   bar_highlight=True, show_break=True)
    
    print("Inside Bar Analysis Results (CORRECTED LOGIC):")
    print("=" * 80)
    
    # Display results with key columns
    display_cols = ['open', 'high', 'low', 'close', 'BarIndex', 'IsIB', 'BoxHigh', 'BoxLow', 
                   'GreenArrow', 'RedArrow', 'BarColor']
    
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_rows', None)
    
    result_display = result[display_cols].round(2)
    print(result_display)
    
    # Detailed analysis
    print(f"\nDetailed Analysis:")
    print(f"=" * 50)
    
    inside_bars = result['IsIB'].sum()
    breakouts_up = result['GreenArrow'].sum()
    breakouts_down = result['RedArrow'].sum()
    
    print(f"Total Inside Bars: {inside_bars}")
    print(f"Upward Breakouts: {breakouts_up}")
    print(f"Downward Breakouts: {breakouts_down}")
    
    # Show which bars are inside bars with their reference bars
    ib_bars = result[result['IsIB'] == True]
    if len(ib_bars) > 0:
        print(f"\nInside Bars Details:")
        for idx in ib_bars.index:
            bar_idx_in_df = result.index.get_loc(idx)
            bar_index_val = ib_bars.loc[idx, 'BarIndex']
            print(f"  Bar {bar_idx_in_df}: Inside bar (barIndex={bar_index_val}) - "
                  f"Current OHLC: {ib_bars.loc[idx, 'open']:.1f}/{ib_bars.loc[idx, 'high']:.1f}/"
                  f"{ib_bars.loc[idx, 'low']:.1f}/{ib_bars.loc[idx, 'close']:.1f}")
    
    # Show breakouts
    breakout_ups = result[result['GreenArrow'] == True]
    breakout_downs = result[result['RedArrow'] == True]
    
    if len(breakout_ups) > 0:
        print(f"\nUpward Breakouts:")
        for idx in breakout_ups.index:
            bar_idx_in_df = result.index.get_loc(idx)
            print(f"  Bar {bar_idx_in_df}: Close {breakout_ups.loc[idx, 'close']:.1f} "
                  f"crossed above BoxHigh {breakout_ups.loc[idx, 'BoxHigh']:.1f}")
    
    if len(breakout_downs) > 0:
        print(f"\nDownward Breakouts:")
        for idx in breakout_downs.index:
            bar_idx_in_df = result.index.get_loc(idx)
            print(f"  Bar {bar_idx_in_df}: Close {breakout_downs.loc[idx, 'close']:.1f} "
                  f"crossed below BoxLow {breakout_downs.loc[idx, 'BoxLow']:.1f}")
    
    return result

# Additional helper function to visualize the logic step by step
def debug_inside_bar_logic(df, start_idx=1, end_idx=10):
    """
    Debug function to show step-by-step logic execution.
    """
    print(f"Debug: Inside Bar Logic Step-by-Step (bars {start_idx} to {end_idx})")
    print("=" * 80)
    
    bar_index = 1
    f_flag = False
    box_high = np.nan
    box_low = np.nan
    
    for i in range(start_idx, min(end_idx + 1, len(df))):
        current_bar = df.iloc[i]
        prev_bar = df.iloc[i-1] if i > 0 else None
        
        # Check if enough history for barIndex lookback
        if i >= bar_index:
            reference_bar = df.iloc[i - bar_index]
            hp = reference_bar['high']
            lp = reference_bar['low']
            
            is_ib = (current_bar['close'] <= hp and current_bar['close'] >= lp and 
                    current_bar['open'] <= hp and current_bar['open'] >= lp)
        else:
            is_ib = False
            reference_bar = None
            hp = lp = np.nan
        
        prev_is_ib = False  # Simplified for debug
        
        print(f"\nBar {i}:")
        print(f"  Current OHLC: {current_bar['open']:.1f}/{current_bar['high']:.1f}/"
              f"{current_bar['low']:.1f}/{current_bar['close']:.1f}")
        if reference_bar is not None:
            print(f"  Reference bar (barIndex={bar_index}): "
                  f"{reference_bar['open']:.1f}/{reference_bar['high']:.1f}/"
                  f"{reference_bar['low']:.1f}/{reference_bar['close']:.1f}")
            print(f"  Reference range: {lp:.1f} - {hp:.1f}")
        print(f"  IsIB: {is_ib}")
        print(f"  barIndex: {bar_index}, f_flag: {f_flag}")
        
        # Update barIndex based on conditions (simplified)
        if is_ib and not prev_is_ib:
            bar_index += 1
            print(f"  -> New IB sequence, barIndex incremented to {bar_index}")
        elif is_ib and prev_is_ib:
            bar_index += 1
            print(f"  -> Continuing IB sequence, barIndex incremented to {bar_index}")
        elif prev_is_ib and not is_ib:
            bar_index = 1
            print(f"  -> End IB sequence, barIndex reset to {bar_index}")

if __name__ == "__main__":
    print("Testing Corrected Inside Bar Logic")
    print("=" * 80)
    test_result = test_inside_bar_logic()
    
    print(f"\n\nStep-by-step debug for first 10 bars:")
    debug_inside_bar_logic(pd.DataFrame({
        'open':  [100.0, 102.0, 101.5, 101.8, 101.2, 101.6, 101.4, 103.0, 102.5, 102.7],
        'high':  [101.0, 103.0, 102.0, 102.0, 101.5, 101.9, 101.7, 104.0, 103.0, 103.2],
        'low':   [99.5,  101.5, 101.0, 101.5, 101.0, 101.3, 101.1, 102.8, 102.0, 102.2],
        'close': [100.5, 102.5, 101.8, 101.6, 101.3, 101.7, 101.5, 103.5, 102.8, 102.9]
    }), 1, 7)