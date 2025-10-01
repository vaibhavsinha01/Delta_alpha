# config.py

# BINANCE_API_KEY = "34nj4RR3uMcECFaa8OIf6v4zSls2MzqmT952KpWVf2TmWSXPznJFKzFjh3555JgT"
# BINANCE_API_SECRET = "GMBWYiKYfrnRMyAzBVQzVQ3pNyXZovQSIUhN1c69oszwmaY5LPSvQbV7qhjiweq5"
BINANCE_API_KEY = "otVLRJLjAbZuuLZbzO7bNLCFoVyb6Nrja9kM0MtLqpWHGKVovvlHRatsejw0roJH"
BINANCE_API_SECRET = "3YeoEi76yUWBpUcQ607ZhQGc9hWYq0qQfLXWksKtojRJz1Wl43bd9oc1MP5InOok"
BINANCE_SYMBOL = 'ETHUSDT'  # Trading pair - changed from BTCUSDT
BINANCE_INTERVAL = '15m'  # Candle intervals
BINANCE_TESTNET_STATUS = 0 # use this to trade on the testnet and set the value to 0 to trade on the mainnet , remainder that there are separate api_keys,api_secrets for the binance_testnet_status
BYBIT_API_KEY = "aasoVM0IEQQe0ompqj"
BYBIT_API_SECRET = "iIRaNq4d26IocVvYPnpS3Tb5Do9IVNRu7n5S"

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

RENTRY_TIME_BINANCE = 300 # this is the time in seconds to enter once the trade has been closed for binance
MASTER_HEIKEN_CHOICE = 1

DESIRED_TYPES = [2,4,-2,-4]

# CONFIG FOR THE DELTA EXCHANGE

DELTA_API_KEY = "0SD98vx0k1P6sBef58CVNEHGgn1rVr"
DELTA_API_SECRET = "eIisBd8rPuHWLshC85uK5zNnGnZLg1P9gmSJ8rl0gVjLDGqr2xUbrvuB0iMr"
DELTA_SYMBOL = "ETHUSD" # use ETHUSDT when using binance to fetch and use ETHUSD when using the delta-exchange to fetch
DELTA_SYMBOL_PLACE_ORDER = "ETHUSD" # used for placing order
DELTA_TOKEN = 3136
DELTA_MIN_LOT = 0.01
DELTA_BASE_LEVERAGE = 10 # change the base leverage also
DELTA_FAKE_LOSS_MAX_AMOUNT = 0.1 # this amount is in dollars 
DELTA_INTERVAL = "5m" 
DELTA_SL_BUFFER_POINTS = 10
DELTA_TP_PERCENT = 0.48
DELTA_INITIAL_CAPITAL = 600
N_CANDLE_LOOKBACK = 5
