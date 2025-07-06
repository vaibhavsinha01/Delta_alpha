# config.py

# Binance API Configuration
BINANCE_API_KEY = '1ff87751c4a5a314b617856c252f342ee4aeff38797361ab676088330b1c26b1'  # Your Binance API key
BINANCE_API_SECRET = '4a924ff228b870e760d42891db0a6b50a61139453232de53d7b80b7d3a7744ef'  # Your Binance API secret
BINANCE_SYMBOL = 'BTCUSDT'  # Trading pair
BINANCE_INTERVAL = '1m'  # Candle interval

# RSI & Gaizy
RSI_PERIOD = 14
RSI_GAIZY_COLORS = ['green', 'red', 'others']

# IB Box
IB_BOX_LOOKBACK = 5

# Range Filter
RANGE_FILTER_LENGTH = 20

# Martingale
MARTINGALE_ENABLED = True
MARTINGALE_MULTIPLIER = 2
MARTINGALE_MAX_STEPS = 5

# Martingale mode: 'RM1' for classic, 'RM2' for add Y/31 to capital after win
MARTINGALE_MODE = 'RM1'  # or 'RM2'

# Risk
SL_BUFFER_POINTS = 10   # X 
TP_PERCENT = 2.5        # Y %
X_LOSS_THRESHOLD = 5    # Points threshold for x_loss to trigger martingale

# Strategy Control
A = 0 
K = 0  

INITIAL_CAPITAL = 200  # Initial trading amount in USDT
