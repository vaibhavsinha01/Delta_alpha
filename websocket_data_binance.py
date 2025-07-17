import websocket
import json
import threading
import time

class WebsocketClass:
    def __init__(self):
        self.ws = None
        self.latest_close = None
        self.is_running = False
        self.ws_thread = None

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            kline = data['k']
            self.latest_close = float(kline['c'])
            # print(f"WebSocket price update: {self.latest_close}")
        except Exception as e:
            print(f"Error processing WebSocket message: {e}")

    def on_error(self, ws, error):
        print(f"WebSocket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket Connection closed")
        self.is_running = False

    def on_open(self, ws):
        print("WebSocket Connection opened")
        self.is_running = True

    def start_websocket(self):
        """Start WebSocket connection in a separate thread"""
        try:
            symbol = "ethusdt"  # Must be lowercase
            interval = "15m"     # 15-minute candle
            stream_url = f"wss://stream.binance.com:9443/ws/{symbol}@kline_{interval}"

            # Connect to Binance WebSocket
            self.ws = websocket.WebSocketApp(
                stream_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )

            # Start WebSocket in a separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Give some time for connection to establish
            time.sleep(2)
            print("WebSocket started successfully")
            
        except Exception as e:
            print(f"Error starting WebSocket: {e}")

    def get_latest_price(self):
        """Get the latest price from WebSocket"""
        return self.latest_close

    def stop_websocket(self):
        """Stop WebSocket connection"""
        if self.ws:
            self.ws.close()
        self.is_running = False