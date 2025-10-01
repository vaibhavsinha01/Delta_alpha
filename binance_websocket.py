import json
import websocket
from collections import deque
import pandas as pd

BINANCE_SOCKET = "wss://stream.binance.com:9443/ws/ethusdt@kline_15m"
ohlcv_window = deque(maxlen=30)

def get_ohlcv_df(window):
    # Converts the latest window buffer to a DataFrame
    df = pd.DataFrame(list(window))
    return df

def process_ohlcv_window(window):
    df = get_ohlcv_df(window)
    print(df)  # Or return df for further use

def on_message(ws, message):
    data = json.loads(message)
    kline = data['k']
    # Add both closed and updating candle
    ohlcv = {
        "time": kline['t'],                  # Start time of the candlestick
        "open": float(kline['o']),
        "high": float(kline['h']),
        "low": float(kline['l']),
        "close": float(kline['c']),
        "volume": float(kline['v']),
        "is_closed": kline['x']
    }
    # Remove candle if already present with this start time (for updating last candle)
    if ohlcv_window and ohlcv_window[-1]['time'] == ohlcv['time']:
        ohlcv_window[-1] = ohlcv
    else:
        ohlcv_window.append(ohlcv)
    process_ohlcv_window(ohlcv_window)

def on_error(ws, error):
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")

def on_open(ws):
    print("Connection opened")

if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        BINANCE_SOCKET,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    ws.run_forever()
