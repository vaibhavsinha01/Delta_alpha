# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# from typing import Tuple, Dict, Optional
# import warnings
# warnings.filterwarnings('ignore')

# class RSIGainzy:
#     """
#     RSI Gainzy Strategy - Python Implementation
#     Converted from Pine Script RSI Integration Tool
    
#     This indicator uses RSI with pivot point trend lines to generate trading signals.
    
#     Signal Colors/Trends:
#     - STRONG_BULL (Bright Pink): trend = -3
#     - STRONG_BEAR (Bright Green): trend = 3  
#     - WEAK_BULL (Green): trend = 1
#     - WEAK_BEAR (Red): trend = -1
#     - NEUTRAL (Blue): trend = 2
#     - DEFAULT (Black): trend = 0
#     """
    
#     def __init__(self):
#         self.results = {}
#         # Color definitions matching Pine Script logic
#         self.colors = {
#             'STRONG_BULL': '#F85BE3',   # Bright Pink (trend = -3)
#             'STRONG_BEAR': '#3EFF45',   # Bright Green (trend = 3)
#             'WEAK_BULL': '#00C853',     # Green (trend = 1)
#             'WEAK_BEAR': '#FF3D00',     # Red (trend = -1)
#             'NEUTRAL': '#2196F3',       # Blue (trend = 2)
#             'DEFAULT': '#000000'        # Black (trend = 0)
#         }
    
#     def calculate_rsi(self, close_prices: np.array, period: int = 14) -> np.array:
#         """Calculate RSI (Relative Strength Index)"""
#         deltas = np.diff(close_prices)
#         gains = np.where(deltas > 0, deltas, 0)
#         losses = np.where(deltas < 0, -deltas, 0)
        
#         # Calculate initial averages
#         avg_gain = np.mean(gains[:period])
#         avg_loss = np.mean(losses[:period])
        
#         # Initialize RSI array
#         rsi = np.full_like(close_prices, np.nan, dtype=float)
        
#         # Calculate RSI values
#         for i in range(period, len(close_prices)):
#             if i == period:
#                 current_avg_gain = avg_gain
#                 current_avg_loss = avg_loss
#             else:
#                 current_avg_gain = (avg_gain * (period - 1) + gains[i-1]) / period
#                 current_avg_loss = (avg_loss * (period - 1) + losses[i-1]) / period
#                 avg_gain = current_avg_gain
#                 avg_loss = current_avg_loss
            
#             if current_avg_loss == 0:
#                 rsi[i] = 100
#             else:
#                 rs = current_avg_gain / current_avg_loss
#                 rsi[i] = 100 - (100 / (1 + rs))
        
#         return rsi
    
#     def find_pivot_highs(self, values: np.array, lookback: int, lookforward: int) -> np.array:
#         """Find pivot highs in the array"""
#         pivots = np.full_like(values, np.nan)
        
#         for i in range(lookback, len(values) - lookforward):
#             if np.isnan(values[i]):
#                 continue
            
#             is_pivot = True
#             # Check lookback period
#             for j in range(i - lookback, i):
#                 if not np.isnan(values[j]) and values[j] >= values[i]:
#                     is_pivot = False
#                     break
            
#             # Check lookforward period
#             if is_pivot:
#                 for j in range(i + 1, min(i + lookforward + 1, len(values))):
#                     if not np.isnan(values[j]) and values[j] >= values[i]:
#                         is_pivot = False
#                         break
            
#             if is_pivot:
#                 pivots[i] = values[i]
        
#         return pivots
    
#     def find_pivot_lows(self, values: np.array, lookback: int, lookforward: int) -> np.array:
#         """Find pivot lows in the array"""
#         pivots = np.full_like(values, np.nan)
        
#         for i in range(lookback, len(values) - lookforward):
#             if np.isnan(values[i]):
#                 continue
            
#             is_pivot = True
#             # Check lookback period
#             for j in range(i - lookback, i):
#                 if not np.isnan(values[j]) and values[j] <= values[i]:
#                     is_pivot = False
#                     break
            
#             # Check lookforward period
#             if is_pivot:
#                 for j in range(i + 1, min(i + lookforward + 1, len(values))):
#                     if not np.isnan(values[j]) and values[j] <= values[i]:
#                         is_pivot = False
#                         break
            
#             if is_pivot:
#                 pivots[i] = values[i]
        
#         return pivots
    
#     def calculate_trend_line_value(self, x1: int, y1: float, x2: int, y2: float, x: int) -> float:
#         """Calculate trend line value at position x"""
#         if x2 == x1:
#             return y1
#         return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    
#     def calculate_signals(self,
#                          df: pd.DataFrame,
#                          rsi_length: int = 14,
#                          pivot_length: int = 10,
#                          overbought_level: int = 70,
#                          oversold_level: int = 30) -> pd.DataFrame:
#         """
#         Calculate RSI Gainzy signals based on Pine Script logic
        
#         Parameters:
#         -----------
#         df : pd.DataFrame
#             DataFrame with OHLC data (must contain 'Close' column)
#         rsi_length : int
#             RSI calculation period
#         pivot_length : int
#             Pivot lookback/forward period
#         overbought_level : int
#             Overbought threshold
#         oversold_level : int
#             Oversold threshold
            
#         Returns:
#         --------
#         pd.DataFrame
#             Original DataFrame with added RSI Gainzy columns
#         """
        
#         # Validate input DataFrame
#         if 'Close' not in df.columns:
#             raise ValueError("DataFrame must contain 'Close' column")
        
#         # Create a copy to avoid modifying original
#         result_df = df.copy()
        
#         # Extract close prices
#         close_prices = df['Close'].values
        
#         # Calculate RSI
#         rsi = self.calculate_rsi(close_prices, rsi_length)
        
#         # Find pivot points
#         pivot_highs = self.find_pivot_highs(rsi, pivot_length, pivot_length)
#         pivot_lows = self.find_pivot_lows(rsi, pivot_length, pivot_length)
        
#         # Initialize arrays for pivot tracking
#         n = len(rsi)
#         prev_high_val = np.full(n, np.nan)
#         last_high_val = np.full(n, np.nan)
#         prev_high_bar = np.full(n, np.nan)
#         last_high_bar = np.full(n, np.nan)
        
#         prev_low_val = np.full(n, np.nan)
#         last_low_val = np.full(n, np.nan)
#         prev_low_bar = np.full(n, np.nan)
#         last_low_bar = np.full(n, np.nan)
        
#         # Track pivot points
#         for i in range(n):
#             if i > 0:
#                 prev_high_val[i] = prev_high_val[i-1]
#                 last_high_val[i] = last_high_val[i-1]
#                 prev_high_bar[i] = prev_high_bar[i-1]
#                 last_high_bar[i] = last_high_bar[i-1]
                
#                 prev_low_val[i] = prev_low_val[i-1]
#                 last_low_val[i] = last_low_val[i-1]
#                 prev_low_bar[i] = prev_low_bar[i-1]
#                 last_low_bar[i] = last_low_bar[i-1]
            
#             # Update pivot highs
#             if not np.isnan(pivot_highs[i]):
#                 prev_high_val[i] = last_high_val[i-1] if i > 0 else np.nan
#                 prev_high_bar[i] = last_high_bar[i-1] if i > 0 else np.nan
#                 last_high_val[i] = pivot_highs[i]
#                 last_high_bar[i] = i
            
#             # Update pivot lows
#             if not np.isnan(pivot_lows[i]):
#                 prev_low_val[i] = last_low_val[i-1] if i > 0 else np.nan
#                 prev_low_bar[i] = last_low_bar[i-1] if i > 0 else np.nan
#                 last_low_val[i] = pivot_lows[i]
#                 last_low_bar[i] = i
        
#         # Calculate current trend line points
#         current_high_line_point = np.full(n, np.nan)
#         current_low_line_point = np.full(n, np.nan)
        
#         for i in range(n):
#             if not np.isnan(prev_high_val[i]) and not np.isnan(last_high_val[i]):
#                 current_high_line_point[i] = self.calculate_trend_line_value(
#                     prev_high_bar[i], prev_high_val[i], 
#                     last_high_bar[i], last_high_val[i], i
#                 )
            
#             if not np.isnan(prev_low_val[i]) and not np.isnan(last_low_val[i]):
#                 current_low_line_point[i] = self.calculate_trend_line_value(
#                     prev_low_bar[i], prev_low_val[i], 
#                     last_low_bar[i], last_low_val[i], i
#                 )
        
#         # Calculate trend based on Pine Script logic
#         trend = np.zeros(n, dtype=int)
        
#         for i in range(1, n):
#             trend[i] = trend[i-1]  # Carry forward previous trend
            
#             # Get current values
#             curr_rsi = rsi[i]
#             curr_high_line = current_high_line_point[i]
#             curr_low_line = current_low_line_point[i]
#             prev_high_line = current_high_line_point[i-1] if i > 0 else np.nan
#             prev_low_line = current_low_line_point[i-1] if i > 0 else np.nan
            
#             # Skip if values are NaN
#             if np.isnan(curr_rsi) or np.isnan(curr_high_line) or np.isnan(curr_low_line):
#                 continue
            
#             # Bullish conditions
#             if (curr_rsi > curr_high_line and curr_high_line > curr_low_line and 
#                 np.isnan(pivot_highs[i]) and curr_high_line > prev_high_line and trend[i] <= 0):
#                 trend[i] = 3
#             elif (curr_rsi > curr_low_line and curr_high_line < curr_low_line and 
#                   np.isnan(pivot_highs[i]) and curr_low_line > prev_low_line and trend[i] <= 0):
#                 trend[i] = 3
#             elif (curr_rsi > curr_high_line and curr_high_line > curr_low_line and 
#                   np.isnan(pivot_highs[i]) and trend[i] < 3):
#                 trend[i] = 1
#             elif (curr_rsi > curr_low_line and curr_high_line < curr_low_line and 
#                   np.isnan(pivot_highs[i]) and trend[i] < 3):
#                 trend[i] = 1
#             elif (curr_rsi > curr_high_line and curr_rsi < curr_low_line and 
#                   curr_high_line < curr_low_line):
#                 trend[i] = 2
            
#             # Reset bullish trend
#             if curr_rsi < curr_high_line and trend[i] > 0:
#                 trend[i] = 0
            
#             # Bearish conditions
#             if (curr_rsi < curr_low_line and curr_high_line > curr_low_line and 
#                 np.isnan(pivot_lows[i]) and curr_low_line < prev_low_line and 
#                 trend[i] >= 0 and trend[i] != 2):
#                 trend[i] = -3
#             elif (curr_rsi < curr_high_line and curr_high_line < curr_low_line and 
#                   np.isnan(pivot_lows[i]) and curr_low_line < prev_low_line and 
#                   trend[i] >= 0 and trend[i] != 2):
#                 trend[i] = -3
#             elif (curr_rsi < curr_low_line and curr_high_line > curr_low_line and 
#                   np.isnan(pivot_lows[i]) and trend[i] > -3):
#                 trend[i] = -1
#             elif (curr_rsi < curr_high_line and curr_high_line < curr_low_line and 
#                   np.isnan(pivot_lows[i]) and trend[i] > -3):
#                 trend[i] = -1
#             elif (curr_rsi < curr_low_line and curr_rsi > curr_high_line and 
#                   curr_high_line < curr_low_line):
#                 trend[i] = 2
            
#             # Reset bearish trend
#             if curr_rsi > curr_low_line and trend[i] < 0:
#                 trend[i] = 0
        
#         # Map trend values to signal colors
#         signal_colors = np.full(n, 'DEFAULT', dtype=object)
#         for i in range(n):
#             if trend[i] == -3:
#                 signal_colors[i] = 'pink' # 'STRONG_BULL'
#             elif trend[i] == 3:
#                 signal_colors[i] = 'bright_green' # 'STRONG_BEAR'
#             elif trend[i] == 1:
#                 signal_colors[i] = 'dark_green' # 'WEAK_BULL'
#             elif trend[i] == -1:
#                 signal_colors[i] = 'red' # 'WEAK_BEAR'
#             elif trend[i] == 2:
#                 signal_colors[i] = 'blue' # 'NEUTRAL'
#             else:
#                 signal_colors[i] = 'black' # 'DEFAULT'
        
#         # Generate trading signals
#         long_signals = (trend == -3) | (trend == 1)  # Strong bull or weak bull
#         short_signals = (trend == 3) | (trend == -1)  # Strong bear or weak bear
        
#         # Add results to DataFrame
#         result_df['RSI'] = rsi
#         result_df['RSI_Smoothed'] = rsi  # Keep same for compatibility
#         result_df['RSI_Momentum'] = trend  # Use trend instead of momentum
#         result_df['Signal_Color'] = signal_colors
#         result_df['Long_Signal'] = long_signals.astype(int)
#         result_df['Short_Signal'] = short_signals.astype(int)
        
#         # Additional columns for analysis
#         result_df['Pivot_Highs'] = pivot_highs
#         result_df['Pivot_Lows'] = pivot_lows
#         result_df['High_Line'] = current_high_line_point
#         result_df['Low_Line'] = current_low_line_point
#         result_df['Trend'] = trend
        
#         # Store results for plotting
#         self.results = {
#             'df': result_df,
#             'rsi': rsi,
#             'smoothed_rsi': rsi,
#             'momentum': trend,
#             'signal_colors': signal_colors,
#             'long_signals': long_signals,
#             'short_signals': short_signals,
#             'overbought_level': overbought_level,
#             'oversold_level': oversold_level,
#             'pivot_highs': pivot_highs,
#             'pivot_lows': pivot_lows,
#             'high_line': current_high_line_point,
#             'low_line': current_low_line_point,
#             'trend': trend
#         }
        
#         # return result_df
#         return result_df['Signal_Color']
    
#     def plot_results(self, figsize: Tuple[int, int] = (15, 12)):
#         """Plot the RSI Gainzy results"""
#         if not self.results:
#             raise ValueError("No results to plot. Run calculate_signals() first.")
        
#         df = self.results['df']
        
#         fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, height_ratios=[2, 1])
        
#         # Main price chart with colored background
#         ax1.plot(df.index, df['Close'], label='Close Price', color='black', linewidth=1, alpha=0.7)
        
#         # Color the background based on signal colors
#         for i in range(len(df)-1):
#             color = self.colors[self.results['signal_colors'][i]]
#             ax1.axvspan(df.index[i], df.index[i+1], alpha=0.1, color=color)
        
#         # Plot signals
#         long_mask = self.results['long_signals']
#         short_mask = self.results['short_signals']
        
#         if np.any(long_mask):
#             ax1.scatter(df.index[long_mask], df['Close'][long_mask], 
#                        color='green', marker='^', s=100, 
#                        label='Long Signal', zorder=5, edgecolors='white', linewidth=1)
        
#         if np.any(short_mask):
#             ax1.scatter(df.index[short_mask], df['Close'][short_mask], 
#                        color='red', marker='v', s=100, 
#                        label='Short Signal', zorder=5, edgecolors='white', linewidth=1)
        
#         ax1.set_title('RSI Gainzy Strategy - Price Chart')
#         ax1.set_ylabel('Price')
#         ax1.legend(loc='upper left')
#         ax1.grid(True, alpha=0.3)
        
#         # RSI subplot with trend lines
#         # Plot RSI with color coding based on trend
#         for i in range(len(df)-1):
#             color = self.colors[self.results['signal_colors'][i]]
#             if not np.isnan(self.results['rsi'][i]) and not np.isnan(self.results['rsi'][i+1]):
#                 ax2.plot([df.index[i], df.index[i+1]], 
#                         [self.results['rsi'][i], self.results['rsi'][i+1]], 
#                         color=color, linewidth=3, alpha=0.8)
        
#         # Plot trend lines
#         high_line = self.results['high_line']
#         low_line = self.results['low_line']
        
#         valid_high = ~np.isnan(high_line)
#         valid_low = ~np.isnan(low_line)
        
#         if np.any(valid_high):
#             ax2.plot(df.index[valid_high], high_line[valid_high], 
#                     color='red', linestyle='--', alpha=0.7, label='High Trend Line')
        
#         if np.any(valid_low):
#             ax2.plot(df.index[valid_low], low_line[valid_low], 
#                     color='green', linestyle='--', alpha=0.7, label='Low Trend Line')
        
#         # Plot pivot points
#         pivot_high_mask = ~np.isnan(self.results['pivot_highs'])
#         pivot_low_mask = ~np.isnan(self.results['pivot_lows'])
        
#         if np.any(pivot_high_mask):
#             ax2.scatter(df.index[pivot_high_mask], self.results['pivot_highs'][pivot_high_mask], 
#                        color='red', marker='v', s=50, alpha=0.8, label='Pivot Highs')
        
#         if np.any(pivot_low_mask):
#             ax2.scatter(df.index[pivot_low_mask], self.results['pivot_lows'][pivot_low_mask], 
#                        color='green', marker='^', s=50, alpha=0.8, label='Pivot Lows')
        
#         # Add overbought/oversold levels
#         ax2.axhline(y=self.results['overbought_level'], color='red', linestyle=':', alpha=0.5)
#         ax2.axhline(y=self.results['oversold_level'], color='green', linestyle=':', alpha=0.5)
#         ax2.axhline(y=50, color='gray', linestyle='-', alpha=0.3)
        
#         ax2.set_title('RSI with Pivot Trend Lines')
#         ax2.set_ylabel('RSI Value')
#         ax2.set_xlabel('Time')
#         ax2.legend(loc='upper right', fontsize=8)
#         ax2.grid(True, alpha=0.3)
#         ax2.set_ylim(0, 100)
        
#         plt.tight_layout()
#         plt.show()
    
#     def get_signal_summary(self) -> Dict:
#         """Get a summary of the signals generated"""
#         if not self.results:
#             raise ValueError("No results available. Run calculate_signals() first.")
        
#         df = self.results['df']
        
#         # Count signals
#         total_long_signals = df['Long_Signal'].sum()
#         total_short_signals = df['Short_Signal'].sum()
        
#         # Count color distribution
#         color_counts = {}
#         for color in self.colors.keys():
#             color_counts[color] = np.sum(self.results['signal_colors'] == color)
        
#         # Calculate percentage of each color
#         total_bars = len(df)
#         color_percentages = {color: (count/total_bars)*100 for color, count in color_counts.items()}
        
#         # Count trend distribution
#         trend_counts = {}
#         for trend_val in [-3, -1, 0, 1, 2, 3]:
#             trend_counts[f'Trend_{trend_val}'] = np.sum(self.results['trend'] == trend_val)
        
#         summary = {
#             'total_bars': total_bars,
#             'long_signals': total_long_signals,
#             'short_signals': total_short_signals,
#             'total_signals': total_long_signals + total_short_signals,
#             'color_counts': color_counts,
#             'color_percentages': color_percentages,
#             'trend_counts': trend_counts,
#             'signal_frequency': ((total_long_signals + total_short_signals) / total_bars) * 100
#         }
        
#         return summary


# # Example usage function
# def example_usage():
#     """Example of how to use the updated RSI Gainzy indicator"""
#     # Create sample data
#     np.random.seed(42)
#     n_periods = 500
    
#     # Generate synthetic price data with trend
#     price = 100
#     data = []
#     trend = 0
    
#     for i in range(n_periods):
#         # Add some trending behavior
#         if i % 50 == 0:
#             trend = np.random.choice([-1, 0, 1], p=[0.3, 0.4, 0.3])
        
#         change = np.random.normal(trend * 0.1, 1)
#         price += change
        
#         # Create OHLC from the price
#         high = price + abs(np.random.normal(0, 0.5))
#         low = price - abs(np.random.normal(0, 0.5))
#         open_price = price + np.random.normal(0, 0.2)
#         close = price
        
#         data.append({
#             'Open': open_price,
#             'High': high,
#             'Low': low,
#             'Close': close
#         })
    
#     df = pd.DataFrame(data)
#     df.index = pd.date_range(start='2023-01-01', periods=n_periods, freq='D')
    
#     # Initialize RSI Gainzy
#     rsi_gainzy = RSIGainzy()
    
#     # Calculate signals with custom parameters
#     result = rsi_gainzy.calculate_signals(
#         df,
#         rsi_length=14,
#         pivot_length=10,
#         overbought_level=70,
#         oversold_level=30
#     )
    
#     # Display results
#     print("RSI Gainzy Results:")
#     print(result[['Close', 'RSI', 'Trend', 'Signal_Color', 
#                   'Long_Signal', 'Short_Signal']].tail(10))
    
#     # Get signal summary
#     summary = rsi_gainzy.get_signal_summary()
#     print(f"\n=== SIGNAL SUMMARY ===")
#     print(f"Total Bars: {summary['total_bars']}")
#     print(f"Long Signals: {summary['long_signals']}")
#     print(f"Short Signals: {summary['short_signals']}")
#     print(f"Signal Frequency: {summary['signal_frequency']:.2f}%")
#     print(f"\nColor Distribution:")
#     for color, percentage in summary['color_percentages'].items():
#         print(f"  {color}: {percentage:.1f}%")
#     print(f"\nTrend Distribution:")
#     for trend, count in summary['trend_counts'].items():
#         print(f"  {trend}: {count}")
    
#     # Plot results
#     rsi_gainzy.plot_results(figsize=(15, 12))
    
#     return result

# if __name__ == "__main__":
#     example_usage()

# import pandas as pd
# import numpy as np

# class RSIGainzy:
#     """
#     RSI Gainzy Strategy - DataFrame Implementation
#     Adds 'gainzy_color' column to the input DataFrame
#     """
    
#     def __init__(self):
#         pass
    
#     def calculate_rsi(self, close_prices: np.array, period: int = 14) -> np.array:
#         """Calculate RSI using the same method as Pine Script ta.rsi()"""
#         close_prices = np.array(close_prices, dtype=float)
        
#         # Calculate price changes
#         deltas = np.diff(close_prices)
#         deltas = np.concatenate([[0], deltas])  # Add 0 for first element
        
#         # Separate gains and losses
#         gains = np.where(deltas > 0, deltas, 0.0)
#         losses = np.where(deltas < 0, -deltas, 0.0)
        
#         # Initialize RSI array
#         rsi = np.full(len(close_prices), np.nan)
        
#         if len(close_prices) < period + 1:
#             return rsi
        
#         # Calculate initial SMA for gains and losses
#         avg_gain = np.mean(gains[1:period+1])
#         avg_loss = np.mean(losses[1:period+1])
        
#         # Calculate first RSI value
#         if avg_loss == 0:
#             rsi[period] = 100.0
#         else:
#             rs = avg_gain / avg_loss
#             rsi[period] = 100.0 - (100.0 / (1.0 + rs))
        
#         # Calculate subsequent RSI values using Wilder's smoothing
#         for i in range(period + 1, len(close_prices)):
#             avg_gain = (avg_gain * (period - 1) + gains[i]) / period
#             avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
#             if avg_loss == 0:
#                 rsi[i] = 100.0
#             else:
#                 rs = avg_gain / avg_loss
#                 rsi[i] = 100.0 - (100.0 / (1.0 + rs))
        
#         return rsi
    
#     def find_pivot_highs(self, values: np.array, left: int, right: int) -> np.array:
#         """Find pivot highs - matches Pine Script ta.pivothigh logic"""
#         n = len(values)
#         pivots = np.full(n, np.nan)
        
#         for i in range(left, n - right):
#             if np.isnan(values[i]):
#                 continue
                
#             is_pivot = True
#             pivot_value = values[i]
            
#             # Check left side
#             for j in range(i - left, i):
#                 if not np.isnan(values[j]) and values[j] >= pivot_value:
#                     is_pivot = False
#                     break
            
#             # Check right side if left side passed
#             if is_pivot:
#                 for j in range(i + 1, i + right + 1):
#                     if j < n and not np.isnan(values[j]) and values[j] >= pivot_value:
#                         is_pivot = False
#                         break
            
#             if is_pivot:
#                 pivots[i] = pivot_value
                
#         return pivots
    
#     def find_pivot_lows(self, values: np.array, left: int, right: int) -> np.array:
#         """Find pivot lows - matches Pine Script ta.pivotlow logic"""
#         n = len(values)
#         pivots = np.full(n, np.nan)
        
#         for i in range(left, n - right):
#             if np.isnan(values[i]):
#                 continue
                
#             is_pivot = True
#             pivot_value = values[i]
            
#             # Check left side
#             for j in range(i - left, i):
#                 if not np.isnan(values[j]) and values[j] <= pivot_value:
#                     is_pivot = False
#                     break
            
#             # Check right side if left side passed
#             if is_pivot:
#                 for j in range(i + 1, i + right + 1):
#                     if j < n and not np.isnan(values[j]) and values[j] <= pivot_value:
#                         is_pivot = False
#                         break
            
#             if is_pivot:
#                 pivots[i] = pivot_value
                
#         return pivots
    
#     # def calculate_gainzy_colors(self, df, close_col='close', rsi_length=14, pivot_length=10):
#     #     """
#     #     Calculate RSI Gainzy colors and add to DataFrame
        
#     #     Parameters:
#     #     df: pandas DataFrame with price data
#     #     close_col: name of the close price column (default: 'close')
#     #     rsi_length: RSI calculation period (default: 14)
#     #     pivot_length: pivot point calculation period (default: 10)
        
#     #     Returns:
#     #     df: DataFrame with added 'gainzy_color' column
#     #     """
        
#     #     # Make a copy to avoid modifying original
#     #     df = df.copy()
        
#     #     # Get close prices
#     #     close_prices = df[close_col].values
#     #     n = len(close_prices)
        
#     #     # Initialize gainzy_color column
#     #     df.loc[:, 'gainzy_color'] = 'black'
        
#     #     # Calculate RSI
#     #     rsi = self.calculate_rsi(close_prices, rsi_length)
        
#     #     # Find pivot points
#     #     rsi_pivot_high = self.find_pivot_highs(rsi, pivot_length, pivot_length)
#     #     rsi_pivot_low = self.find_pivot_lows(rsi, pivot_length, pivot_length)
        
#     #     # Initialize tracking variables
#     #     last_rsi_pivot_high = np.full(n, np.nan)
#     #     last_rsi_pivot_low = np.full(n, np.nan)
        
#     #     # Track last pivot values - FIXED: Check condition properly
#     #     for i in range(n):
#     #         if i > 0:
#     #             last_rsi_pivot_high[i] = last_rsi_pivot_high[i-1]
#     #             last_rsi_pivot_low[i] = last_rsi_pivot_low[i-1]
            
#     #         # Reset to NaN each bar (matching Pine Script logic)
#     #         last_rsi_pivot_high[i] = np.nan
#     #         last_rsi_pivot_low[i] = np.nan
            
#     #         # Update when new pivot found - FIXED: Check at correct index
#     #         if (not np.isnan(rsi_pivot_high[i]) and 
#     #             i >= pivot_length and 
#     #             i < n - 1 and 
#     #             not np.isnan(rsi[i - pivot_length]) and 
#     #             not np.isnan(rsi[i - pivot_length + 1]) and 
#     #             rsi[i - pivot_length] != rsi[i - pivot_length + 1]):
#     #             last_rsi_pivot_high[i] = rsi_pivot_high[i]
            
#     #         if (not np.isnan(rsi_pivot_low[i]) and 
#     #             i >= pivot_length and 
#     #             i < n - 1 and 
#     #             not np.isnan(rsi[i - pivot_length]) and 
#     #             not np.isnan(rsi[i - pivot_length + 1]) and 
#     #             rsi[i - pivot_length] != rsi[i - pivot_length + 1]):
#     #             last_rsi_pivot_low[i] = rsi_pivot_low[i]
        
#     #     # Store pivot high values and bars
#     #     prev_high_val = np.full(n, np.nan)
#     #     last_high_val = np.full(n, np.nan)
#     #     prev_high_bar = np.full(n, np.nan)
#     #     last_high_bar = np.full(n, np.nan)
        
#     #     # Store pivot low values and bars
#     #     prev_low_val = np.full(n, np.nan)
#     #     last_low_val = np.full(n, np.nan)
#     #     prev_low_bar = np.full(n, np.nan)
#     #     last_low_bar = np.full(n, np.nan)
        
#     #     # Track pivot values and bar indices
#     #     for i in range(n):
#     #         if i > 0:
#     #             prev_high_val[i] = prev_high_val[i-1]
#     #             last_high_val[i] = last_high_val[i-1]
#     #             prev_high_bar[i] = prev_high_bar[i-1]
#     #             last_high_bar[i] = last_high_bar[i-1]
                
#     #             prev_low_val[i] = prev_low_val[i-1]
#     #             last_low_val[i] = last_low_val[i-1]
#     #             prev_low_bar[i] = prev_low_bar[i-1]
#     #             last_low_bar[i] = last_low_bar[i-1]
            
#     #         # Update when new pivot high found - FIXED: Use correct bar index
#     #         if not np.isnan(last_rsi_pivot_high[i]):
#     #             prev_high_val[i] = last_high_val[i-1] if i > 0 else np.nan
#     #             prev_high_bar[i] = last_high_bar[i-1] if i > 0 else np.nan
#     #             last_high_val[i] = last_rsi_pivot_high[i]
#     #             last_high_bar[i] = i  # FIXED: Should be i, not i - pivot_length
            
#     #         # Update when new pivot low found - FIXED: Use correct bar index
#     #         if not np.isnan(last_rsi_pivot_low[i]):
#     #             prev_low_val[i] = last_low_val[i-1] if i > 0 else np.nan
#     #             prev_low_bar[i] = last_low_bar[i-1] if i > 0 else np.nan
#     #             last_low_val[i] = last_rsi_pivot_low[i]
#     #             last_low_bar[i] = i  # FIXED: Should be i, not i - pivot_length
        
#     #     # Calculate current high and low line points - FIXED: Logic completely rewritten
#     #     current_high_line_point = np.full(n, np.nan)
#     #     current_low_line_point = np.full(n, np.nan)
        
#     #     for i in range(n):
#     #         # Initialize with previous values
#     #         if i > 0:
#     #             current_high_line_point[i] = current_high_line_point[i-1]
#     #             current_low_line_point[i] = current_low_line_point[i-1]
#     #         else:
#     #             current_high_line_point[i] = prev_high_val[i] if not np.isnan(prev_high_val[i]) else np.nan
#     #             current_low_line_point[i] = prev_low_val[i] if not np.isnan(prev_low_val[i]) else np.nan
            
#     #         # Calculate high line point - FIXED: Proper line extension logic
#     #         if (not np.isnan(prev_high_val[i]) and not np.isnan(last_high_val[i]) and 
#     #             not np.isnan(prev_high_bar[i]) and not np.isnan(last_high_bar[i]) and
#     #             last_high_bar[i] != prev_high_bar[i]):
                
#     #             # Extend line from last_high_bar to current bar
#     #             j = int(last_high_bar[i])
#     #             while j < i:
#     #                 line_val = (prev_high_val[i] + 
#     #                            (last_high_val[i] - prev_high_val[i]) * 
#     #                            (j + 1 - prev_high_bar[i]) / 
#     #                            (last_high_bar[i] - prev_high_bar[i]))
#     #                 if line_val >= 100 or line_val <= 0:
#     #                     break
#     #                 j += 1
                
#     #             # Calculate current line point
#     #             current_high_line_point[i] = (prev_high_val[i] + 
#     #                                         (last_high_val[i] - prev_high_val[i]) * 
#     #                                         (j - prev_high_bar[i]) / 
#     #                                         (last_high_bar[i] - prev_high_bar[i]))
            
#     #         # Calculate low line point - FIXED: Proper line extension logic
#     #         if (not np.isnan(prev_low_val[i]) and not np.isnan(last_low_val[i]) and 
#     #             not np.isnan(prev_low_bar[i]) and not np.isnan(last_low_bar[i]) and
#     #             last_low_bar[i] != prev_low_bar[i]):
                
#     #             # Extend line from last_low_bar to current bar
#     #             j = int(last_low_bar[i])
#     #             while j < i:
#     #                 line_val = (prev_low_val[i] + 
#     #                            (last_low_val[i] - prev_low_val[i]) * 
#     #                            (j - prev_low_bar[i]) / 
#     #                            (last_low_bar[i] - prev_low_bar[i]))
#     #                 if line_val >= 100 or line_val <= 0:
#     #                     break
#     #                 j += 1
                
#     #             # Calculate current line point
#     #             current_low_line_point[i] = (prev_low_val[i] + 
#     #                                        (last_low_val[i] - prev_low_val[i]) * 
#     #                                        (j - prev_low_bar[i]) / 
#     #                                        (last_low_bar[i] - prev_low_bar[i]))
        
#     #     # Calculate trend based on Pine Script logic - FIXED: Proper trend logic
#     #     trend = np.zeros(n, dtype=int)
        
#     #     for i in range(1, n):
#     #         # Carry forward previous trend
#     #         trend[i] = trend[i-1]
            
#     #         if np.isnan(rsi[i]):
#     #             continue
            
#     #         curr_rsi = rsi[i]
#     #         curr_high_line = current_high_line_point[i] if not np.isnan(current_high_line_point[i]) else 0
#     #         curr_low_line = current_low_line_point[i] if not np.isnan(current_low_line_point[i]) else 0
#     #         prev_high_line = current_high_line_point[i-1] if not np.isnan(current_high_line_point[i-1]) else 0
#     #         prev_low_line = current_low_line_point[i-1] if not np.isnan(current_low_line_point[i-1]) else 0
            
#     #         # Bullish trend conditions
#     #         if (curr_rsi > curr_high_line and curr_high_line > curr_low_line and 
#     #             np.isnan(last_rsi_pivot_high[i]) and curr_high_line > prev_high_line and trend[i] <= 0):
#     #             trend[i] = 3
#     #         elif (curr_rsi > curr_low_line and curr_high_line < curr_low_line and 
#     #               np.isnan(last_rsi_pivot_high[i]) and curr_low_line > prev_low_line and trend[i] <= 0):
#     #             trend[i] = 3
#     #         elif (curr_rsi > curr_high_line and curr_high_line > curr_low_line and 
#     #               np.isnan(last_rsi_pivot_high[i]) and trend[i] < 3):
#     #             trend[i] = 1
#     #         elif (curr_rsi > curr_low_line and curr_high_line < curr_low_line and 
#     #               np.isnan(last_rsi_pivot_high[i]) and trend[i] < 3):
#     #             trend[i] = 1
#     #         elif (curr_rsi > curr_high_line and curr_rsi < curr_low_line and 
#     #               curr_high_line < curr_low_line):
#     #             trend[i] = 2
            
#     #         # Reset bullish trend
#     #         if curr_rsi < curr_high_line and trend[i] > 0:
#     #             trend[i] = 0
            
#     #         # Bearish trend conditions
#     #         if (curr_rsi < curr_low_line and curr_high_line > curr_low_line and 
#     #             np.isnan(last_rsi_pivot_low[i]) and curr_low_line < prev_low_line and 
#     #             trend[i] >= 0 and trend[i] != 2):
#     #             trend[i] = -3
#     #         elif (curr_rsi < curr_high_line and curr_high_line < curr_low_line and 
#     #               np.isnan(last_rsi_pivot_low[i]) and curr_low_line < prev_low_line and 
#     #               trend[i] >= 0 and trend[i] != 2):
#     #             trend[i] = -3
#     #         elif (curr_rsi < curr_low_line and curr_high_line > curr_low_line and 
#     #               np.isnan(last_rsi_pivot_low[i]) and trend[i] > -3):
#     #             trend[i] = -1
#     #         elif (curr_rsi < curr_high_line and curr_high_line < curr_low_line and 
#     #               np.isnan(last_rsi_pivot_low[i]) and trend[i] > -3):
#     #             trend[i] = -1
#     #         elif (curr_rsi < curr_low_line and curr_rsi > curr_high_line and 
#     #               curr_high_line < curr_low_line):
#     #             trend[i] = 2
            
#     #         # Reset bearish trend
#     #         if curr_rsi > curr_low_line and trend[i] < 0:
#     #             trend[i] = 0
        
#     #     # Map trend values to colors - FIXED: Correct color mapping
#     #     for i in range(n):
#     #         if trend[i] == -3:
#     #             df.loc[df.index[i], 'gainzy_color'] = 'pink'      # Strong bearish (matches Pine Script)
#     #         elif trend[i] == 3:
#     #             df.loc[df.index[i], 'gainzy_color'] = 'light_green'  # Strong bullish (matches Pine Script)
#     #         elif trend[i] == 1:
#     #             df.loc[df.index[i], 'gainzy_color'] = 'green'     # Weak bullish
#     #         elif trend[i] == -1:
#     #             df.loc[df.index[i], 'gainzy_color'] = 'red'       # Weak bearish
#     #         elif trend[i] == 2:
#     #             df.loc[df.index[i], 'gainzy_color'] = 'blue'      # Neutral
#     #         else:
#     #             df.loc[df.index[i], 'gainzy_color'] = 'black'     # Default
        
#     #     return df['gainzy_color']

#     def calculate_gainzy_colors(self, df, close_col='close', rsi_length=14, pivot_length=10):
#         """
#         Calculate RSI Gainzy colors and add to DataFrame
        
#         Parameters:
#         df: pandas DataFrame with price data
#         close_col: name of the close price column (default: 'close')
#         rsi_length: RSI calculation period (default: 14)
#         pivot_length: pivot point calculation period (default: 10)
        
#         Returns:
#         df: DataFrame with added 'gainzy_color' column
#         """
        
#         # Make a copy to avoid modifying original
#         df = df.copy()
        
#         # Get close prices
#         close_prices = df[close_col].values
#         n = len(close_prices)
        
#         # Initialize gainzy_color column
#         df.loc[:, 'gainzy_color'] = 'black'
        
#         # Calculate RSI
#         rsi = self.calculate_rsi(close_prices, rsi_length)
        
#         # Find pivot points
#         rsi_pivot_high = self.find_pivot_highs(rsi, pivot_length, pivot_length)
#         rsi_pivot_low = self.find_pivot_lows(rsi, pivot_length, pivot_length)
        
#         # Initialize tracking variables - Use single values, not arrays
#         last_rsi_pivot_high = np.nan
#         last_rsi_pivot_low = np.nan
        
#         # Store pivot high values and bars - Use single values
#         prev_high_val = np.nan
#         last_high_val = np.nan
#         prev_high_bar = np.nan
#         last_high_bar = np.nan
        
#         # Store pivot low values and bars - Use single values
#         prev_low_val = np.nan
#         last_low_val = np.nan
#         prev_low_bar = np.nan
#         last_low_bar = np.nan
        
#         # Initialize current line points - Use single values
#         current_high_line_point = np.nan
#         current_low_line_point = np.nan
        
#         # Initialize trend - Use single value
#         trend = 0
        
#         # Arrays to store results for each bar
#         trend_results = np.zeros(n, dtype=int)
#         current_high_line_points = np.full(n, np.nan)
#         current_low_line_points = np.full(n, np.nan)
        
#         # Process each bar
#         for i in range(n):
#             # Reset pivot values each bar (matching Pine Script logic)
#             last_rsi_pivot_high = np.nan
#             last_rsi_pivot_low = np.nan
            
#             # Check for new pivot high - Fixed: Match Pine Script logic exactly
#             if (not np.isnan(rsi_pivot_high[i]) and 
#                 i >= pivot_length and 
#                 i < n - pivot_length and 
#                 not np.isnan(rsi[i - pivot_length]) and not np.isnan(rsi[i - pivot_length + 1]) and 
#                 rsi[i - pivot_length] != rsi[i - pivot_length + 1]):
#                 last_rsi_pivot_high = rsi_pivot_high[i]
            
#             # Check for new pivot low - Fixed: Match Pine Script logic exactly
#             if (not np.isnan(rsi_pivot_low[i]) and 
#                 i >= pivot_length and 
#                 i < n - pivot_length and 
#                 not np.isnan(rsi[i - pivot_length]) and not np.isnan(rsi[i - pivot_length + 1]) and 
#                 rsi[i - pivot_length] != rsi[i - pivot_length + 1]):
#                 last_rsi_pivot_low = rsi_pivot_low[i]
            
#             # Update pivot high tracking - Match Pine Script var logic
#             if not np.isnan(last_rsi_pivot_high):
#                 prev_high_val = last_high_val
#                 prev_high_bar = last_high_bar
#                 last_high_val = last_rsi_pivot_high
#                 last_high_bar = i - pivot_length
            
#             # Update pivot low tracking - Match Pine Script var logic
#             if not np.isnan(last_rsi_pivot_low):
#                 prev_low_val = last_low_val
#                 prev_low_bar = last_low_bar
#                 last_low_val = last_rsi_pivot_low
#                 last_low_bar = i - pivot_length
            
#             # Calculate current high line point - Match Pine Script logic exactly
#             current_high_line_point = prev_high_val
#             if (not np.isnan(prev_high_val) and not np.isnan(last_high_val) and 
#                 not np.isnan(prev_high_bar) and not np.isnan(last_high_bar) and
#                 last_high_bar != prev_high_bar):
                
#                 j = int(last_high_bar)
#                 # Extend line while within bounds - Fixed: Match Pine Script while loop
#                 while (prev_high_val + (last_high_val - prev_high_val) * (j + 1 - prev_high_bar) / (last_high_bar - prev_high_bar) < 100 and
#     prev_high_val + (last_high_val - prev_high_val) * (j + 1 - prev_high_bar) / (last_high_bar - prev_high_bar) > 0 and 
#                     j < i):
#                     j += 1
                
#                 # Calculate current line point
#                 current_high_line_point = (prev_high_val + 
#                                         (last_high_val - prev_high_val) * 
#                                         (j - prev_high_bar) / 
#                                         (last_high_bar - prev_high_bar))
            
#             # Calculate current low line point - Match Pine Script logic exactly
#             current_low_line_point = prev_low_val
#             if (not np.isnan(prev_low_val) and not np.isnan(last_low_val) and 
#                 not np.isnan(prev_low_bar) and not np.isnan(last_low_bar) and
#                 last_low_bar != prev_low_bar):
                
#                 j = int(last_low_bar)
#                 # Extend line while within bounds - Fixed: Match Pine Script while loop
#                 while (prev_low_val + (last_low_val - prev_low_val) * (j - prev_low_bar) / (last_low_bar - prev_low_bar) < 100 and 
#                     prev_low_val + (last_low_val - prev_low_val) * (j - prev_low_bar) / (last_low_bar - prev_low_bar) > 0 and 
#                     j < i):
#                     j += 1
                
#                 # Calculate current line point
#                 current_low_line_point = (prev_low_val + 
#                                         (last_low_val - prev_low_val) * 
#                                         (j - prev_low_bar) / 
#                                         (last_low_bar - prev_low_bar))
            
#             # Store line points for historical reference
#             current_high_line_points[i] = current_high_line_point
#             current_low_line_points[i] = current_low_line_point
            
#             # Calculate trend - Match Pine Script logic exactly
#             if i > 0:
#                 trend = trend_results[i-1]  # Carry forward previous trend
            
#             if np.isnan(rsi[i]):
#                 trend_results[i] = trend
#                 continue
            
#             curr_rsi = rsi[i]
#             curr_high_line = current_high_line_point if not np.isnan(current_high_line_point) else 0
#             curr_low_line = current_low_line_point if not np.isnan(current_low_line_point) else 0
            
#             # Get previous line values for comparison - Fixed: Use stored values
#             prev_high_line = current_high_line_points[i-1] if i > 0 and not np.isnan(current_high_line_points[i-1]) else 0
#             prev_low_line = current_low_line_points[i-1] if i > 0 and not np.isnan(current_low_line_points[i-1]) else 0
            
#             # Bullish trend conditions - Match Pine Script exactly
#             if (curr_rsi > curr_high_line and curr_high_line > curr_low_line and 
#                 np.isnan(last_rsi_pivot_high) and curr_high_line > prev_high_line and trend <= 0):
#                 trend = 3
#             elif (curr_rsi > curr_low_line and curr_high_line < curr_low_line and 
#                 np.isnan(last_rsi_pivot_high) and curr_low_line > prev_low_line and trend <= 0):
#                 trend = 3
#             elif (curr_rsi > curr_high_line and curr_high_line > curr_low_line and 
#                 np.isnan(last_rsi_pivot_high) and trend < 3):
#                 trend = 1
#             elif (curr_rsi > curr_low_line and curr_high_line < curr_low_line and 
#                 np.isnan(last_rsi_pivot_high) and trend < 3):
#                 trend = 1
#             elif (curr_rsi > curr_high_line and curr_rsi < curr_low_line and 
#                 curr_high_line < curr_low_line):
#                 trend = 2
            
#             # Reset bullish trend
#             if curr_rsi < curr_high_line and trend > 0:
#                 trend = 0
            
#             # Bearish trend conditions - Match Pine Script exactly
#             if (curr_rsi < curr_low_line and curr_high_line > curr_low_line and 
#                 np.isnan(last_rsi_pivot_low) and curr_low_line < prev_low_line and 
#                 trend >= 0 and trend != 2):
#                 trend = -3
#             elif (curr_rsi < curr_high_line and curr_high_line < curr_low_line and 
#                 np.isnan(last_rsi_pivot_low) and curr_low_line < prev_low_line and 
#                 trend >= 0 and trend != 2):
#                 trend = -3
#             elif (curr_rsi < curr_low_line and curr_high_line > curr_low_line and 
#                 np.isnan(last_rsi_pivot_low) and trend > -3):
#                 trend = -1
#             elif (curr_rsi < curr_high_line and curr_high_line < curr_low_line and 
#                 np.isnan(last_rsi_pivot_low) and trend > -3):
#                 trend = -1
#             elif (curr_rsi < curr_low_line and curr_rsi > curr_high_line and 
#                 curr_high_line < curr_low_line):
#                 trend = 2
            
#             # Reset bearish trend
#             if curr_rsi > curr_low_line and trend < 0:
#                 trend = 0
            
#             trend_results[i] = trend
        
#         # Map trend values to colors - Match Pine Script color mapping exactly
#         color_map = {
#             -3: 'pink',  # Pink - matches Pine Script color.rgb(248, 91, 227)
#             3: 'light_green',    # Light green - matches Pine Script color.rgb(62, 255, 69)
#             2: 'blue',                # Blue - matches Pine Script color.blue
#             1: 'green',               # Green - matches Pine Script color.green
#             -1: 'red',                # Red - matches Pine Script color.red
#             0: 'black'                # Black - default
#         }
        
#         for i in range(n):
#             color = color_map.get(trend_results[i], 'black')
#             df.loc[df.index[i], 'gainzy_color'] = color
        
#         return df['gainzy_color']

# # Example usage
# def test_rsi_gainzy():
#     """Test function with DataFrame"""
#     # Create sample DataFrame with more realistic price movement
#     np.random.seed(42)
#     dates = pd.date_range('2023-01-01', periods=200, freq='D')
    
#     # Create more realistic price data with trends
#     base_price = 100
#     prices = [base_price]
#     for i in range(1, 200):
#         # Add some trending behavior and volatility
#         trend = 0.1 if i < 50 else (-0.1 if i < 150 else 0.05)
#         noise = np.random.randn() * 2
#         new_price = prices[-1] + trend + noise
#         prices.append(max(50, min(200, new_price)))  # Keep prices reasonable
    
#     df = pd.DataFrame({
#         'date': dates,
#         'close': prices,
#         'high': [price + abs(np.random.randn()) for price in prices],
#         'low': [price - abs(np.random.randn()) for price in prices],
#         'volume': [1000 + np.random.randint(0, 500) for _ in range(200)]
#     })
    
#     # Initialize and calculate
#     rsi_gainzy = RSIGainzy()
#     gainzy_colors = rsi_gainzy.calculate_gainzy_colors(df, close_col='close')
#     df['gainzy_color'] = gainzy_colors
    
#     print("DataFrame with gainzy_color column:")
#     print(df[['date', 'close', 'gainzy_color']].tail(20))
#     print("\nUnique colors:", df['gainzy_color'].unique().tolist())
#     print("Color distribution:")
#     print(df['gainzy_color'].value_counts())
    
#     return df

# if __name__ == "__main__":
#     df_result = test_rsi_gainzy()

import pandas as pd
import numpy as np

class RSIGainzy:
    """
    RSI Gainzy Strategy - DataFrame Implementation
    Adds 'gainzy_color' column to the input DataFrame
    """
    
    def __init__(self):
        pass
    
    def calculate_rsi(self, close_prices: np.array, period: int = 14) -> np.array:
        """Calculate RSI using the same method as Pine Script ta.rsi()"""
        close_prices = np.array(close_prices, dtype=float)
        
        # Calculate price changes
        deltas = np.diff(close_prices)
        deltas = np.concatenate([[0], deltas])  # Add 0 for first element
        
        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        
        # Initialize RSI array
        rsi = np.full(len(close_prices), np.nan)
        
        if len(close_prices) < period + 1:
            return rsi
        
        # Calculate initial SMA for gains and losses
        avg_gain = np.mean(gains[1:period+1])
        avg_loss = np.mean(losses[1:period+1])
        
        # Calculate first RSI value
        if avg_loss == 0:
            rsi[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[period] = 100.0 - (100.0 / (1.0 + rs))
        
        # Calculate subsequent RSI values using Wilder's smoothing
        for i in range(period + 1, len(close_prices)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[i] = 100.0 - (100.0 / (1.0 + rs))
        
        return rsi
    
    def find_pivot_highs(self, values: np.array, left: int, right: int) -> np.array:
        """Find pivot highs - matches Pine Script ta.pivothigh logic"""
        n = len(values)
        pivots = np.full(n, np.nan)
        
        for i in range(left, n - right):
            if np.isnan(values[i]):
                continue
                
            is_pivot = True
            pivot_value = values[i]
            
            # Check left side
            for j in range(i - left, i):
                if not np.isnan(values[j]) and values[j] >= pivot_value:
                    is_pivot = False
                    break
            
            # Check right side if left side passed
            if is_pivot:
                for j in range(i + 1, i + right + 1):
                    if j < n and not np.isnan(values[j]) and values[j] >= pivot_value:
                        is_pivot = False
                        break
            
            if is_pivot:
                # Pine Script returns the pivot at the current bar when detected
                # but it refers to the bar that was left periods ago
                if i + right < n:
                    pivots[i + right] = pivot_value
                
        return pivots
    
    def find_pivot_lows(self, values: np.array, left: int, right: int) -> np.array:
        """Find pivot lows - matches Pine Script ta.pivotlow logic"""
        n = len(values)
        pivots = np.full(n, np.nan)
        
        for i in range(left, n - right):
            if np.isnan(values[i]):
                continue
                
            is_pivot = True
            pivot_value = values[i]
            
            # Check left side
            for j in range(i - left, i):
                if not np.isnan(values[j]) and values[j] <= pivot_value:
                    is_pivot = False
                    break
            
            # Check right side if left side passed
            if is_pivot:
                for j in range(i + 1, i + right + 1):
                    if j < n and not np.isnan(values[j]) and values[j] <= pivot_value:
                        is_pivot = False
                        break
            
            if is_pivot:
                # Pine Script returns the pivot at the current bar when detected
                # but it refers to the bar that was left periods ago
                if i + right < n:
                    pivots[i + right] = pivot_value
                
        return pivots

    def calculate_gainzy_colors(self, df, close_col='close', rsi_length=14, pivot_length=10):
        """
        Calculate RSI Gainzy colors and add to DataFrame
        
        Parameters:
        df: pandas DataFrame with price data
        close_col: name of the close price column (default: 'close')
        rsi_length: RSI calculation period (default: 14)
        pivot_length: pivot point calculation period (default: 10)
        
        Returns:
        df: DataFrame with added 'gainzy_color' column
        """
        
        # Make a copy to avoid modifying original
        df = df.copy()
        
        # Get close prices
        close_prices = df[close_col].values
        n = len(close_prices)
        
        # Initialize gainzy_color column
        df.loc[:, 'gainzy_color'] = 'black'
        
        # Calculate RSI
        rsi = self.calculate_rsi(close_prices, rsi_length)
        
        # Find pivot points
        rsi_pivot_high = self.find_pivot_highs(rsi, pivot_length, pivot_length)
        rsi_pivot_low = self.find_pivot_lows(rsi, pivot_length, pivot_length)
        
        # Initialize tracking variables - Use single values, not arrays
        prev_high_val = np.nan
        last_high_val = np.nan
        prev_high_bar = np.nan
        last_high_bar = np.nan
        
        # Store pivot low values and bars - Use single values
        prev_low_val = np.nan
        last_low_val = np.nan
        prev_low_bar = np.nan
        last_low_bar = np.nan
        
        # Initialize current line points - Use single values
        current_high_line_point = np.nan
        current_low_line_point = np.nan
        
        # Initialize trend - Use single value
        trend = 0
        
        # Arrays to store results for each bar
        trend_results = np.zeros(n, dtype=int)
        current_high_line_points = np.full(n, np.nan)
        current_low_line_points = np.full(n, np.nan)
        
        # Process each bar
        for i in range(n):
            # Get current pivot values (these are detected at current bar but refer to past bars)
            last_rsi_pivot_high = np.nan
            last_rsi_pivot_low = np.nan
            
            # Check for new pivot high - Fixed: Check the condition properly
            if not np.isnan(rsi_pivot_high[i]):
                # The pivot refers to the bar that was pivot_length bars ago
                pivot_bar_index = i - pivot_length
                if pivot_bar_index >= 0 and pivot_bar_index + 1 < len(rsi):
                    # Check the Pine Script condition: rsi[pivotLen] != rsi[pivotLen+1]
                    if rsi[pivot_bar_index] != rsi[pivot_bar_index + 1]:
                        last_rsi_pivot_high = rsi_pivot_high[i]
            
            # Check for new pivot low - Fixed: Check the condition properly
            if not np.isnan(rsi_pivot_low[i]):
                # The pivot refers to the bar that was pivot_length bars ago
                pivot_bar_index = i - pivot_length
                if pivot_bar_index >= 0 and pivot_bar_index + 1 < len(rsi):
                    # Check the Pine Script condition: rsi[pivotLen] != rsi[pivotLen+1]
                    if rsi[pivot_bar_index] != rsi[pivot_bar_index + 1]:
                        last_rsi_pivot_low = rsi_pivot_low[i]
            
            # Update pivot high tracking - Match Pine Script var logic
            if not np.isnan(last_rsi_pivot_high):
                prev_high_val = last_high_val
                prev_high_bar = last_high_bar
                last_high_val = last_rsi_pivot_high
                last_high_bar = i - pivot_length
            
            # Update pivot low tracking - Match Pine Script var logic
            if not np.isnan(last_rsi_pivot_low):
                prev_low_val = last_low_val
                prev_low_bar = last_low_bar
                last_low_val = last_rsi_pivot_low
                last_low_bar = i - pivot_length
            
            # Calculate current high line point - Match Pine Script logic exactly
            current_high_line_point = prev_high_val
            if (not np.isnan(prev_high_val) and not np.isnan(last_high_val) and 
                not np.isnan(prev_high_bar) and not np.isnan(last_high_bar) and
                last_high_bar != prev_high_bar):
                
                j = int(last_high_bar)
                # Extend line while within bounds - Fixed: Match Pine Script while loop
                while j < i:
                    next_point = prev_high_val + (last_high_val - prev_high_val) * (j + 1 - prev_high_bar) / (last_high_bar - prev_high_bar)
                    if next_point >= 100 or next_point <= 0:
                        break
                    j += 1
                
                # Calculate current line point
                if last_high_bar != prev_high_bar:
                    current_high_line_point = (prev_high_val + 
                                            (last_high_val - prev_high_val) * 
                                            (j - prev_high_bar) / 
                                            (last_high_bar - prev_high_bar))
            
            # Calculate current low line point - Match Pine Script logic exactly
            current_low_line_point = prev_low_val
            if (not np.isnan(prev_low_val) and not np.isnan(last_low_val) and 
                not np.isnan(prev_low_bar) and not np.isnan(last_low_bar) and
                last_low_bar != prev_low_bar):
                
                j = int(last_low_bar)
                # Extend line while within bounds - Fixed: Match Pine Script while loop
                while j < i:
                    next_point = prev_low_val + (last_low_val - prev_low_val) * (j - prev_low_bar) / (last_low_bar - prev_low_bar)
                    if next_point >= 100 or next_point <= 0:
                        break
                    j += 1
                
                # Calculate current line point
                if last_low_bar != prev_low_bar:
                    current_low_line_point = (prev_low_val + 
                                            (last_low_val - prev_low_val) * 
                                            (j - prev_low_bar) / 
                                            (last_low_bar - prev_low_bar))
            
            # Store line points for historical reference
            current_high_line_points[i] = current_high_line_point
            current_low_line_points[i] = current_low_line_point
            
            # Calculate trend - Match Pine Script logic exactly
            if i > 0:
                trend = trend_results[i-1]  # Carry forward previous trend
            
            if np.isnan(rsi[i]):
                trend_results[i] = trend
                continue
            
            curr_rsi = rsi[i]
            curr_high_line = current_high_line_point if not np.isnan(current_high_line_point) else 0
            curr_low_line = current_low_line_point if not np.isnan(current_low_line_point) else 0
            
            # Get previous line values for comparison - Fixed: Use stored values
            prev_high_line = current_high_line_points[i-1] if i > 0 and not np.isnan(current_high_line_points[i-1]) else 0
            prev_low_line = current_low_line_points[i-1] if i > 0 and not np.isnan(current_low_line_points[i-1]) else 0
            
            # Bullish trend conditions - Match Pine Script exactly
            if (curr_rsi > curr_high_line and curr_high_line > curr_low_line and 
                np.isnan(last_rsi_pivot_high) and curr_high_line > prev_high_line and trend <= 0):
                trend = 3
            elif (curr_rsi > curr_low_line and curr_high_line < curr_low_line and 
                np.isnan(last_rsi_pivot_high) and curr_low_line > prev_low_line and trend <= 0):
                trend = 3
            elif (curr_rsi > curr_high_line and curr_high_line > curr_low_line and 
                np.isnan(last_rsi_pivot_high) and trend < 3):
                trend = 1
            elif (curr_rsi > curr_low_line and curr_high_line < curr_low_line and 
                np.isnan(last_rsi_pivot_high) and trend < 3):
                trend = 1
            elif (curr_rsi > curr_high_line and curr_rsi < curr_low_line and 
                curr_high_line < curr_low_line):
                trend = 2
            
            # Reset bullish trend
            if curr_rsi < curr_high_line and trend > 0:
                trend = 0
            
            # Bearish trend conditions - Match Pine Script exactly
            if (curr_rsi < curr_low_line and curr_high_line > curr_low_line and 
                np.isnan(last_rsi_pivot_low) and curr_low_line < prev_low_line and 
                trend >= 0 and trend != 2):
                trend = -3
            elif (curr_rsi < curr_high_line and curr_high_line < curr_low_line and 
                np.isnan(last_rsi_pivot_low) and curr_low_line < prev_low_line and 
                trend >= 0 and trend != 2):
                trend = -3
            elif (curr_rsi < curr_low_line and curr_high_line > curr_low_line and 
                np.isnan(last_rsi_pivot_low) and trend > -3):
                trend = -1
            elif (curr_rsi < curr_high_line and curr_high_line < curr_low_line and 
                np.isnan(last_rsi_pivot_low) and trend > -3):
                trend = -1
            elif (curr_rsi < curr_low_line and curr_rsi > curr_high_line and 
                curr_high_line < curr_low_line):
                trend = 2
            
            # Reset bearish trend
            if curr_rsi > curr_low_line and trend < 0:
                trend = 0
            
            trend_results[i] = trend
        
        # Map trend values to colors - Match Pine Script color mapping exactly
        color_map = {
            -3: 'pink',               # Pink - matches Pine Script color.rgb(248, 91, 227)
            3: 'light_green',         # Light green - matches Pine Script color.rgb(62, 255, 69)
            2: 'blue',                # Blue - matches Pine Script color.blue
            1: 'green',               # Green - matches Pine Script color.green
            -1: 'red',                # Red - matches Pine Script color.red
            0: 'black'                # Black - default
        }
        
        for i in range(n):
            color = color_map.get(trend_results[i], 'black')
            df.loc[df.index[i], 'gainzy_color'] = color
        
        return df['gainzy_color']

# Example usage
def test_rsi_gainzy():
    """Test function with DataFrame"""
    # Create sample DataFrame with more realistic price movement
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    
    # Create more realistic price data with trends
    base_price = 100
    prices = [base_price]
    for i in range(1, 200):
        # Add some trending behavior and volatility
        trend = 0.1 if i < 50 else (-0.1 if i < 150 else 0.05)
        noise = np.random.randn() * 2
        new_price = prices[-1] + trend + noise
        prices.append(max(50, min(200, new_price)))  # Keep prices reasonable
    
    df = pd.DataFrame({
        'date': dates,
        'close': prices,
        'high': [price + abs(np.random.randn()) for price in prices],
        'low': [price - abs(np.random.randn()) for price in prices],
        'volume': [1000 + np.random.randint(0, 500) for _ in range(200)]
    })
    
    # Initialize and calculate
    rsi_gainzy = RSIGainzy()
    gainzy_colors = rsi_gainzy.calculate_gainzy_colors(df, close_col='close')
    df['gainzy_color'] = gainzy_colors
    
    print("DataFrame with gainzy_color column:")
    print(df[['date', 'close', 'gainzy_color']].tail(20))
    print("\nUnique colors:", df['gainzy_color'].unique().tolist())
    print("Color distribution:")
    print(df['gainzy_color'].value_counts())
    
    return df

if __name__ == "__main__":
    df_result = test_rsi_gainzy()