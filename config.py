# config.py

# Binance API Configuration - USE THIS FILE TO CHANGE THE API,SECRET KEYS AND THE SYMBOL,INTERVAL
# BINANCE_API_KEY = '1337874f97ecf53736b7bfa8f68db40fa20441fc441feb181a76d082dfbf6f15'  # Your Binance API key
# BINANCE_API_SECRET = '1f9ee8e187873426d7583734d0cd0661a0c1e0281ef0d9bf66013ade515d48d9'  # Your Binance API secret
BINANCE_API_KEY = "34nj4RR3uMcECFaa8OIf6v4zSls2MzqmT952KpWVf2TmWSXPznJFKzFjh3555JgT"
BINANCE_API_SECRET = "GMBWYiKYfrnRMyAzBVQzVQ3pNyXZovQSIUhN1c69oszwmaY5LPSvQbV7qhjiweq5"
BINANCE_SYMBOL = 'ETHUSDT'  # Trading pair - changed from BTCUSDT
BINANCE_INTERVAL = '15m'  # Candle intervals
BINANCE_TESTNET_STATUS = 0 # use this to trade on the testnet and set the value to 0 to trade on the mainnet , remainder that there are separate api_keys,api_secrets for the binance_testnet_status

# Don't change the variables here they have nothing to do with the values in the code in main file
RSI_PERIOD = 14
RSI_GAIZY_COLORS = ['green', 'red', 'others']
IB_BOX_LOOKBACK = 5
RANGE_FILTER_LENGTH = 20
# Don't change the variables here they have nothing to do with the values in the code in main file

# Martingale - don't change any of these 
MARTINGALE_ENABLED = True # keep it as true for martingale and false for no martingale 
MARTINGALE_MULTIPLIER = 2
MARTINGALE_MAX_STEPS = 5
MARTINGALE_MODE = 'RM1' 

# Risk - change these values to adjust the tp/sl
SL_BUFFER_POINTS = 3    # X 
TP_PERCENT = 0.25        # Y % 2.5% is 0.25
X_LOSS_THRESHOLD = 10     # Points threshold for x_loss to trigger martingale
BINANCE_BASE_LEVERAGE = 10

# Strategy Control - instead of this you can run separate files for different strategies - don't change
A = 0 
K = 0  

INITIAL_CAPITAL = 10000  # Initial trading amount in USDT - used to trade

# HERE PLEASE MAKE USE OF THE MILITARY TIMINGS SO 15:30 MEANS 3:30 PM AND THIS IS FOR THE INDIAN STANDARD TIME
START_HOUR = 0
START_MINUTE = 00
END_HOUR = 23
END_MINUTE = 59

RENTRY_TIME_BINANCE = 900 # this is the time in seconds to enter once the trade has been closed for binance
MASTER_HEIKEN_CHOICE = 1

# DESIRED_TYPES = [1,2,3,-1,-2,-3]
# DESIRED_TYPES = [-1,-2,-3] # only take sell trades 
# DESIRED_TYPES = [1,2,3] # only take buy trades
# DESIRED_TYPES = [1,2,3,-1,-2,-3]
DESIRED_TYPES = [2,-2]
"""
Configuration File - `config.py`
Important Note -> always ensure that the code is saved properly CTRL+S before exiting
This file contains all key configuration parameters required for running the Binance trading bot. Modify only the recommended sections; others are intended to remain constant unless you fully understand the logic they're tied to. The file is divided into the following sections:

1. Binance API Configuration:
- `BINANCE_API_KEY`: Your unique Binance API key. Required for accessing your Binance account programmatically.
- `BINANCE_API_SECRET`: Your Binance API secret key. Keep this confidential to avoid unauthorized access.
- `BINANCE_SYMBOL`: The trading pair used for executing trades (e.g., BTCUSDT, ETHUSDT).
- `BINANCE_INTERVAL`: The time interval for candlestick data (e.g., '1m' for 1-minute candles).
- `BINANCE_TESTNET_STATUS`: Set to `1` to use Binance's testnet for paper trading; set to `0` for live trading on the mainnet. Note that testnet requires separate API credentials.

2. Indicator and Strategy Variables (Do Not Modify):
- `RSI_PERIOD`: The lookback period for calculating the Relative Strength Index (RSI).
- `RSI_GAIZY_COLORS`: Placeholder for visualization logic (e.g., RSI color scheme).
- `IB_BOX_LOOKBACK`: Lookback period used for detecting Inside Bar patterns.
- `RANGE_FILTER_LENGTH`: Period used for volatility or range-based filters.

3. Martingale Settings (Advanced Users Only):
- `MARTINGALE_ENABLED`: Enables or disables the Martingale loss recovery strategy.
- `MARTINGALE_MULTIPLIER`: The factor by which the trade size is increased after a loss.
- `MARTINGALE_MAX_STEPS`: Maximum number of times Martingale can retry to recover a loss.
- `MARTINGALE_MODE`: Logic mode (e.g., RM1) that dictates how Martingale is applied.

4. Risk Management Settings:
- `SL_BUFFER_POINTS`: Number of points used to buffer the stop-loss beyond market structure.
- `TP_PERCENT`: Take-profit target as a percentage of entry price.
- `X_LOSS_THRESHOLD`: Point-based loss limit to trigger Martingale retry logic.

5. Strategy Control Flags:
- `A`, `K`: Generic switches used to enable/disable certain custom strategies within the main bot logic.

6. Capital Allocation:
- `INITIAL_CAPITAL`: The simulated or real capital (in USDT) used for trading. Important for risk and position sizing.

7. Trading Time Control (Indian Standard Time - IST):
- `START_HOUR`, `START_MINUTE`: Start time (24-hour format) for when the bot is allowed to trade.
- `END_HOUR`, `END_MINUTE`: End time (24-hour format) for stopping all trading operations. Adjust these to restrict trading to specific market sessions (e.g., Asian, European, or American).

To trade the full day, use the default values (00:00 to 23:59). For specific sessions (e.g., 5:30 AM to 8:00 PM), update these accordingly using 24-hour time format.

Important Note -> always ensure that the code is saved properly CTRL+S before exiting
"""

# CONFIG FOR THE DELTA EXCHANGE

DELTA_API_KEY = "0SD98vx0k1P6sBef58CVNEHGgn1rVr"
DELTA_API_SECRET = "eIisBd8rPuHWLshC85uK5zNnGnZLg1P9gmSJ8rl0gVjLDGqr2xUbrvuB0iMr"
DELTA_SYMBOL = "ETHUSD" # use ETHUSDT when using binance to fetch and use ETHUSD when using the delta-exchange to fetch
DELTA_SYMBOL_PLACE_ORDER = "ETHUSD" # used for placing order
DELTA_TOKEN = 3136
DELTA_MIN_LOT = 0.01
DELTA_BASE_LEVERAGE = 10 # change the base leverage also
DELTA_FAKE_LOSS_MAX_AMOUNT = 1 # this amount is in dollars 
DELTA_INTERVAL = "15m" 
DELTA_SL_BUFFER_POINTS = 15
DELTA_TP_PERCENT = 0.6
DELTA_INITIAL_CAPITAL = 4000

"""
Delta Exchange Trading Configuration - `config.py`

This section defines all the required parameters for executing algorithmic trades using Delta Exchange, particularly tailored for **demo trading environments**. Each variable serves a critical function in either authentication, trade execution, or risk management. Below is an in-depth explanation of each configuration:

1. API Credentials:
- `DELTA_API_KEY`: The API key for authenticating with Delta Exchange's demo account. This key is unique to your account and is used for all authenticated requests.
- `DELTA_API_SECRET`: The corresponding API secret for the key above. Keep this confidential and never expose it publicly. ⚠️ **Note:** There are different keys for the demo trading vs live trading

2. Trading Asset Configuration:
- `DELTA_SYMBOL`: The trading pair to operate on (e.g., ETHUSDT, BTCUSDT). This string must exactly match the symbol format used by Delta Exchange.
- `DELTA_TOKEN`: An internal token identifier used by Delta Exchange APIs to recognize the trading instrument. ⚠️ **Note:** Delta Exchange uses different token IDs for demo vs. live trading. For example:
  - ETHUSDT: `1699` for testnet and `3136` for live trading.
  - Ensure you set this correctly to avoid placing trades on the wrong asset.

3. Trade Sizing:
- `DELTA_MIN_LOT`: The minimum lot size for the selected symbol. For ETHUSDT, use `0.01`. For BTCUSDT, use `0.001`. Setting an incorrect value here can lead to order rejections or unexpected behavior.

4. Leverage:
- `DELTA_BASE_LEVERAGE`: The leverage applied to trades. A leverage of 5 means the position size is 5 times the actual capital used. Adjust according to your risk profile and market volatility.

5. Fake Trade Loss Management:
- `DELTA_FAKE_LOSS_MAX_AMOUNT`: This is a threshold (in USDT) for fake trade losses. If losses from simulated fake trades exceed this amount, the bot may escalate to the next Martingale step to attempt recovery. Useful for detecting underperformance or inefficiencies.

6. Candle Timeframe:
- `DELTA_INTERVAL`: The candlestick (K-line) timeframe for market analysis and signal generation (e.g., '1m' for 1-minute candles). This should match the timeframe used in your strategy logic.

7. Risk Parameters:
- `DELTA_SL_BUFFER_POINTS`: Number of points (not percent) to buffer below the support or resistance level when placing stop-losses. Ensures tighter or looser SLs depending on market behavior.
- `DELTA_TP_PERCENT`: Take-profit level expressed as a percentage of entry price. For example, a value of `0.4` means the trade will be closed once 0.4% profit is achieved.

8. Capital Allocation:
- `DELTA_INITIAL_CAPITAL`: The starting capital (in USDT) allocated for the strategy.
"""
