# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# import yfinance as yf
# from datetime import datetime, timedelta

# class RSIBuySellIndicator:
#     """
#     RSI Buy/Sell Signal Indicator
#     Identifies overbought and oversold conditions for trading signals
    
#     Original Pine Script by: Duy Thanh Nguyen (Vietnam)
#     Converted to Python
#     """
    
#     def __init__(self, rsi_length=14, rsi_upper=70, rsi_lower=30):
#         """
#         Initialize the RSI Buy/Sell indicator
        
#         Parameters:
#         rsi_length (int): Period for RSI calculation (default: 14)
#         rsi_upper (int): RSI upper threshold for sell signals (default: 70)
#         rsi_lower (int): RSI lower threshold for buy signals (default: 30)
#         """
#         self.rsi_length = rsi_length
#         self.rsi_upper = rsi_upper
#         self.rsi_lower = rsi_lower
    
#     def rma(self, series, length):
#         """
#         Calculate Running Moving Average (RMA) - equivalent to Pine Script's rma()
#         This is an exponential moving average with alpha = 1/length
#         """
#         alpha = 1.0 / length
#         return series.ewm(alpha=alpha, adjust=False).mean()
    
#     def calculate_rsi(self, prices):
#         """
#         Calculate RSI using the same method as Pine Script
        
#         Parameters:
#         prices (pd.Series): Price series (typically close prices)
        
#         Returns:
#         pd.Series: RSI values
#         """
#         # Calculate price changes
#         changes = prices.diff()
        
#         # Separate gains and losses
#         gains = np.maximum(changes, 0)
#         losses = -np.minimum(changes, 0)
        
#         # Calculate RMA of gains and losses
#         avg_gains = self.rma(gains, self.rsi_length)
#         avg_losses = self.rma(losses, self.rsi_length)
        
#         # Calculate RSI
#         rs = avg_gains / avg_losses
#         rsi = 100 - (100 / (1 + rs))
        
#         # Handle edge cases
#         rsi = rsi.fillna(50)  # Fill NaN with neutral RSI
        
#         return rsi
    
#     def generate_signals(self, prices):
#         """
#         Generate buy/sell signals based on RSI crossovers
        
#         Parameters:
#         prices (pd.Series): Price series
        
#         Returns:
#         tuple: (rsi, buy_signals, sell_signals)
#         """
#         # Calculate RSI
#         rsi = self.calculate_rsi(prices)
        
#         # Generate signals based on Pine Script logic
#         # Buy signal: RSI was below lower threshold and now crosses above it
#         buy_signals = (rsi.shift(1) < self.rsi_lower) & (rsi >= self.rsi_lower)
        
#         # Sell signal: RSI was above upper threshold and now crosses below it
#         sell_signals = (rsi.shift(1) > self.rsi_upper) & (rsi <= self.rsi_upper)
        
#         return rsi, buy_signals, sell_signals
    
#     def analyze_data(self, data):
#         """
#         Analyze price data and return complete results
        
#         Parameters:
#         data (pd.DataFrame): DataFrame with 'Close' column
        
#         Returns:
#         pd.DataFrame: DataFrame with RSI and signals
#         """
#         # Ensure we have the right column name
#         if 'Close' not in data.columns and 'close' in data.columns:
#             data = data.rename(columns={'close': 'Close'})
        
#         # Calculate RSI and signals
#         rsi, buy_signals, sell_signals = self.generate_signals(data['Close'])
        
#         # Create results DataFrame
#         results = data.copy()
#         results['RSI'] = rsi
#         results['RSI_Buy_Signal'] = buy_signals
#         results['RSI_Sell_Signal'] = sell_signals
        
#         return results
    
#     def plot_analysis(self, results, title="RSI Buy/Sell Analysis"):
#         """
#         Plot price chart with RSI and buy/sell signals
        
#         Parameters:
#         results (pd.DataFrame): Results from analyze_data()
#         title (str): Chart title
#         """
#         fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), 
#                                        gridspec_kw={'height_ratios': [2, 1]})
        
#         # Plot price and signals
#         ax1.plot(results.index, results['Close'], label='Close Price', linewidth=1)
        
#         # Plot buy signals
#         buy_points = results[results['RSI_Buy_Signal']]
#         if not buy_points.empty:
#             ax1.scatter(buy_points.index, buy_points['Close'], 
#                        color='green', marker='^', s=100, label='Buy Signal', zorder=5)
        
#         # Plot sell signals
#         sell_points = results[results['RSI_Sell_Signal']]
#         if not sell_points.empty:
#             ax1.scatter(sell_points.index, sell_points['Close'], 
#                        color='red', marker='v', s=100, label='Sell Signal', zorder=5)
        
#         ax1.set_title(f'{title} - Price Chart')
#         ax1.set_ylabel('Price')
#         ax1.legend()
#         ax1.grid(True, alpha=0.3)
        
#         # Plot RSI
#         ax2.plot(results.index, results['RSI'], label='RSI', color='purple')
#         ax2.axhline(y=self.rsi_upper, color='r', linestyle='--', alpha=0.7, label=f'Overbought ({self.rsi_upper})')
#         ax2.axhline(y=self.rsi_lower, color='g', linestyle='--', alpha=0.7, label=f'Oversold ({self.rsi_lower})')
#         ax2.axhline(y=50, color='gray', linestyle='-', alpha=0.5, label='Neutral (50)')
        
#         # Highlight RSI signal areas
#         ax2.fill_between(results.index, self.rsi_upper, 100, alpha=0.2, color='red', label='Overbought Zone')
#         ax2.fill_between(results.index, 0, self.rsi_lower, alpha=0.2, color='green', label='Oversold Zone')
        
#         ax2.set_title('RSI Indicator')
#         ax2.set_ylabel('RSI')
#         ax2.set_xlabel('Date')
#         ax2.set_ylim(0, 100)
#         ax2.legend()
#         ax2.grid(True, alpha=0.3)
        
#         plt.tight_layout()
#         plt.show()
    
#     def get_signal_summary(self, results):
#         """
#         Get summary of buy/sell signals
        
#         Parameters:
#         results (pd.DataFrame): Results from analyze_data()
        
#         Returns:
#         dict: Summary statistics
#         """
#         buy_count = results['RSI_Buy_Signal'].sum()
#         sell_count = results['RSI_Sell_Signal'].sum()
        
#         buy_dates = results[results['RSI_Buy_Signal']].index.tolist()
#         sell_dates = results[results['RSI_Sell_Signal']].index.tolist()
        
#         current_rsi = results['RSI'].iloc[-1]
        
#         summary = {
#             'total_buy_signals': buy_count,
#             'total_sell_signals': sell_count,
#             'current_rsi': round(current_rsi, 2),
#             'latest_buy_dates': buy_dates[-5:] if buy_dates else [],
#             'latest_sell_dates': sell_dates[-5:] if sell_dates else [],
#             'rsi_parameters': {
#                 'length': self.rsi_length,
#                 'upper_threshold': self.rsi_upper,
#                 'lower_threshold': self.rsi_lower
#             }
#         }
        
#         return summary


# # Example Usage
# def example_usage():
#     """
#     Example of how to use the RSI Buy/Sell Indicator
#     """
#     print("RSI Buy/Sell Signal Indicator - Example Usage")
#     print("=" * 50)
    
#     # Initialize the indicator
#     rsi_indicator = RSIBuySellIndicator(rsi_length=14, rsi_upper=70, rsi_lower=30)
    
#     # Download sample data (Apple stock for last 6 months)
#     print("Downloading sample data (AAPL)...")
#     end_date = datetime.now()
#     start_date = end_date - timedelta(days=180)
    
#     try:
#         # Download data using yfinance
#         data = yf.download('AAPL', start=start_date, end=end_date)
#         print(f"Downloaded {len(data)} days of data")
        
#         # Analyze the data
#         print("Analyzing data...")
#         results = rsi_indicator.analyze_data(data)
        
#         # Get signal summary
#         summary = rsi_indicator.get_signal_summary(results)
        
#         # Print summary
#         print("\nSignal Summary:")
#         print(f"Total Buy Signals: {summary['total_buy_signals']}")
#         print(f"Total Sell Signals: {summary['total_sell_signals']}")
#         print(f"Current RSI: {summary['current_rsi']}")
#         print(f"RSI Length: {summary['rsi_parameters']['length']}")
#         print(f"Upper Threshold: {summary['rsi_parameters']['upper_threshold']}")
#         print(f"Lower Threshold: {summary['rsi_parameters']['lower_threshold']}")
        
#         if summary['latest_buy_dates']:
#             print(f"\nLatest Buy Signals:")
#             for date in summary['latest_buy_dates']:
#                 print(f"  - {date.strftime('%Y-%m-%d')}")
        
#         if summary['latest_sell_dates']:
#             print(f"\nLatest Sell Signals:")
#             for date in summary['latest_sell_dates']:
#                 print(f"  - {date.strftime('%Y-%m-%d')}")
        
#         # Plot the analysis
#         print("\nGenerating chart...")
#         rsi_indicator.plot_analysis(results, "AAPL - RSI Buy/Sell Analysis")
        
#         # Show recent signals with prices
#         print("\nRecent Signals with Prices:")
#         recent_signals = results[results['RSI_Buy_Signal'] | results['RSI_Sell_Signal']].tail(10)
#         for idx, row in recent_signals.iterrows():
#             signal_type = "BUY" if row['RSI_Buy_Signal'] else "SELL"
#             print(f"{idx.strftime('%Y-%m-%d')}: {signal_type} at ${row['Close']:.2f} (RSI: {row['RSI']:.2f})")
        
#     except Exception as e:
#         print(f"Error downloading data: {e}")
#         print("Please install yfinance: pip install yfinance")
        
#         # Create sample data for demonstration
#         print("\nCreating sample data for demonstration...")
#         dates = pd.date_range(start='2024-01-01', end='2024-06-01', freq='D')
#         np.random.seed(42)
#         prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
#         sample_data = pd.DataFrame({'Close': prices}, index=dates)
        
#         results = rsi_indicator.analyze_data(sample_data)
#         summary = rsi_indicator.get_signal_summary(results)
        
#         print(f"Sample Analysis - Buy Signals: {summary['total_buy_signals']}, Sell Signals: {summary['total_sell_signals']}")
#         rsi_indicator.plot_analysis(results, "Sample Data - RSI Analysis")


# if __name__ == "__main__":
#     example_usage()

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

class RSIBuySellIndicator:
    """
    RSI Buy/Sell Signal Indicator
    Identifies overbought and oversold conditions for trading signals
    
    Original Pine Script by: Duy Thanh Nguyen (Vietnam)
    Converted to Python - Corrected to match Pine Script logic exactly
    """
    
    def __init__(self, rsi_length=14, rsi_upper=70, rsi_lower=30):
        """
        Initialize the RSI Buy/Sell indicator
        
        Parameters:
        rsi_length (int): Period for RSI calculation (default: 14)
        rsi_upper (int): RSI upper threshold for sell signals (default: 70)
        rsi_lower (int): RSI lower threshold for buy signals (default: 30)
        """
        self.rsi_length = rsi_length
        self.rsi_upper = rsi_upper
        self.rsi_lower = rsi_lower
    
    def pine_rma(self, src, length):
        """
        Calculate RMA exactly as Pine Script does
        Pine Script RMA logic:
        alpha = length
        sum = na(sum[1]) ? sma(src, length) : (src + (alpha - 1) * nz(sum[1])) / alpha
        """
        alpha = length
        result = pd.Series(index=src.index, dtype=float)
        
        # Initialize with SMA for the first 'length' values
        sma_initial = src.rolling(window=length).mean()
        
        for i in range(len(src)):
            if i < length - 1:
                result.iloc[i] = np.nan
            elif i == length - 1:
                # First valid value is SMA
                result.iloc[i] = sma_initial.iloc[i]
            else:
                # Subsequent values use RMA formula
                prev_rma = result.iloc[i-1]
                if pd.isna(prev_rma):
                    result.iloc[i] = sma_initial.iloc[i]
                else:
                    result.iloc[i] = (src.iloc[i] + (alpha - 1) * prev_rma) / alpha
        
        return result
    
    def calculate_rsi(self, prices):
        """
        Calculate RSI using Pine Script logic exactly
        
        Pine Script logic:
        up = rma(max(change(src), 0), len)
        down = rma(-min(change(src), 0), len)
        rsi = down == 0 ? 100 : up == 0 ? 0 : 100 - (100 / (1 + up / down))
        
        Parameters:
        prices (pd.Series): Price series (typically close prices)
        
        Returns:
        pd.Series: RSI values
        """
        # Calculate price changes (equivalent to change(src) in Pine Script)
        changes = prices.diff()
        
        # Calculate up and down movements
        # up = max(change(src), 0)
        up_moves = np.maximum(changes, 0)
        # down = -min(change(src), 0)  
        down_moves = -np.minimum(changes, 0)
        
        # Calculate RMA of up and down movements
        up_rma = self.pine_rma(up_moves, self.rsi_length)
        down_rma = self.pine_rma(down_moves, self.rsi_length)
        
        # Calculate RSI using Pine Script logic
        rsi = pd.Series(index=prices.index, dtype=float)
        
        for i in range(len(prices)):
            down_val = down_rma.iloc[i]
            up_val = up_rma.iloc[i]
            
            if pd.isna(down_val) or pd.isna(up_val):
                rsi.iloc[i] = np.nan
            elif down_val == 0:
                rsi.iloc[i] = 100
            elif up_val == 0:
                rsi.iloc[i] = 0
            else:
                rsi.iloc[i] = 100 - (100 / (1 + up_val / down_val))
        
        return rsi
    
    def generate_signals(self, prices):
        """
        Generate buy/sell signals based on Pine Script logic exactly
        
        Pine Script logic:
        isup() => rsi[1] > len1 and rsi <= len1
        isdown() => rsi[1] < len2 and rsi >= len2
        
        Parameters:
        prices (pd.Series): Price series
        
        Returns:
        tuple: (rsi, buy_signals, sell_signals)
        """
        # Calculate RSI
        rsi = self.calculate_rsi(prices)
        
        # Generate signals based on Pine Script logic
        # Sell signal: rsi[1] > rsi_upper and rsi <= rsi_upper (RSI was above threshold and now crosses down to threshold)
        sell_signals = (rsi.shift(1) > self.rsi_upper) & (rsi <= self.rsi_upper)
        
        # Buy signal: rsi[1] < rsi_lower and rsi >= rsi_lower (RSI was below threshold and now crosses up to threshold)
        buy_signals = (rsi.shift(1) < self.rsi_lower) & (rsi >= self.rsi_lower)
        
        return rsi, buy_signals, sell_signals
    
    def analyze_data(self, data):
        """
        Analyze price data and return complete results
        
        Parameters:
        data (pd.DataFrame): DataFrame with 'Close' column
        
        Returns:
        pd.DataFrame: DataFrame with RSI and signals
        """
        # Ensure we have the right column name
        if 'Close' not in data.columns and 'close' in data.columns:
            data = data.rename(columns={'close': 'Close'})
        
        # Calculate RSI and signals
        rsi, buy_signals, sell_signals = self.generate_signals(data['Close'])
        
        # Create results DataFrame
        results = data.copy()
        results['RSI'] = rsi
        results['RSI_Buy_Signal'] = buy_signals
        results['RSI_Sell_Signal'] = sell_signals
        
        return results
    
    def get_signal_summary(self, results):
        """
        Get summary of buy/sell signals
        
        Parameters:
        results (pd.DataFrame): Results from analyze_data()
        
        Returns:
        dict: Summary statistics
        """
        buy_count = results['RSI_Buy_Signal'].sum()
        sell_count = results['RSI_Sell_Signal'].sum()
        
        buy_dates = results[results['RSI_Buy_Signal']].index.tolist()
        sell_dates = results[results['RSI_Sell_Signal']].index.tolist()
        
        current_rsi = results['RSI'].iloc[-1] if not results['RSI'].isna().all() else np.nan
        
        summary = {
            'total_buy_signals': buy_count,
            'total_sell_signals': sell_count,
            'current_rsi': round(current_rsi, 2) if not pd.isna(current_rsi) else None,
            'latest_buy_dates': buy_dates[-5:] if buy_dates else [],
            'latest_sell_dates': sell_dates[-5:] if sell_dates else [],
            'rsi_parameters': {
                'length': self.rsi_length,
                'upper_threshold': self.rsi_upper,
                'lower_threshold': self.rsi_lower
            }
        }
        
        return summary


# Example Usage
def example_usage():
    """
    Example of how to use the RSI Buy/Sell Indicator
    """
    print("RSI Buy/Sell Signal Indicator - Corrected Version")
    print("=" * 50)
    
    # Initialize the indicator
    rsi_indicator = RSIBuySellIndicator(rsi_length=14, rsi_upper=70, rsi_lower=30)
    
    # Download sample data (Apple stock for last 6 months)
    print("Downloading sample data (AAPL)...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    try:
        # Download data using yfinance
        data = yf.download('AAPL', start=start_date, end=end_date)
        print(f"Downloaded {len(data)} days of data")
        
        # Analyze the data
        print("Analyzing data...")
        results = rsi_indicator.analyze_data(data)
        
        # Get signal summary
        summary = rsi_indicator.get_signal_summary(results)
        
        # Print summary
        print("\nSignal Summary:")
        print(f"Total Buy Signals: {summary['total_buy_signals']}")
        print(f"Total Sell Signals: {summary['total_sell_signals']}")
        print(f"Current RSI: {summary['current_rsi']}")
        print(f"RSI Length: {summary['rsi_parameters']['length']}")
        print(f"Upper Threshold: {summary['rsi_parameters']['upper_threshold']}")
        print(f"Lower Threshold: {summary['rsi_parameters']['lower_threshold']}")
        
        if summary['latest_buy_dates']:
            print(f"\nLatest Buy Signals:")
            for date in summary['latest_buy_dates']:
                print(f"  - {date.strftime('%Y-%m-%d')}")
        
        if summary['latest_sell_dates']:
            print(f"\nLatest Sell Signals:")
            for date in summary['latest_sell_dates']:
                print(f"  - {date.strftime('%Y-%m-%d')}")
        
        # Show recent signals with prices
        print("\nRecent Signals with Prices:")
        recent_signals = results[results['RSI_Buy_Signal'] | results['RSI_Sell_Signal']].tail(10)
        for idx, row in recent_signals.iterrows():
            signal_type = "BUY" if row['RSI_Buy_Signal'] else "SELL"
            rsi_val = row['RSI'] if not pd.isna(row['RSI']) else 'N/A'
            print(f"{idx.strftime('%Y-%m-%d')}: {signal_type} at ${row['Close']:.2f} (RSI: {rsi_val})")
        
        # Show last 10 RSI values for verification
        print("\nLast 10 RSI values:")
        last_rsi = results[['Close', 'RSI']].tail(10)
        for idx, row in last_rsi.iterrows():
            rsi_val = f"{row['RSI']:.2f}" if not pd.isna(row['RSI']) else 'N/A'
            print(f"{idx.strftime('%Y-%m-%d')}: Close=${row['Close']:.2f}, RSI={rsi_val}")
        
    except Exception as e:
        print(f"Error downloading data: {e}")
        print("Please install yfinance: pip install yfinance")
        
        # Create sample data for demonstration
        print("\nCreating sample data for demonstration...")
        dates = pd.date_range(start='2024-01-01', end='2024-06-01', freq='D')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
        sample_data = pd.DataFrame({'Close': prices}, index=dates)
        
        results = rsi_indicator.analyze_data(sample_data)
        summary = rsi_indicator.get_signal_summary(results)
        
        print(f"Sample Analysis - Buy Signals: {summary['total_buy_signals']}, Sell Signals: {summary['total_sell_signals']}")


if __name__ == "__main__":
    example_usage()