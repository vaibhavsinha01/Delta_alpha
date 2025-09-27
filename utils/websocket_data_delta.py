import websocket
import json

def on_message_delta(ws,message):
    try:
        data = json.loads(message)
        close_price = data['close']
        print(close_price)
    except Exception as e:
        print(f"Error in getting message {e}")

def on_error_delta(ws,error):
    print("Error:",error)

def on_close_delta(ws,close_status_code,close_msg):
    print("Connection closed")

def on_open_delta(ws):
    print("Connection opened")
    subscribe_msg = {
        "type":"subscribe",
        "payload":{
            "channels":[
                {
                    "name":"v2/ticker",
                    "symbols":["BTCUSD"],
                    "interval":"1m"
                }
            ]
        }
    }
    ws.send(json.dumps(subscribe_msg))

ws_url = "wss://socket.delta.exchange"
ws = websocket.WebSocketApp(ws_url,on_open=on_open_delta,on_message=on_message_delta,on_error=on_error_delta,on_close=on_close_delta)

ws.run_forever()