import requests
import json
from datetime import datetime

def send_webhook(url, data):
    """
    Send trade data to Delta Exchange webhook
    """
    try:
        # Add timestamp to data
        data['timestamp'] = datetime.now().isoformat()
        
        # Format data for Delta Exchange
        payload = {
            'type': 'trade_signal',
            'data': data
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            print(f"Webhook sent successfully: {json.dumps(payload, indent=2)}")
            return True
        else:
            print(f"Webhook failed with status {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"Webhook error: {e}")
        return False

def format_trade_data(direction, entry_price, sl, tp, amount, strategy_type):
    """
    Format trade data for webhook
    """
    return {
        'direction': direction,
        'entry_price': entry_price,
        'stop_loss': sl,
        'take_profit': tp,
        'amount': amount,
        'strategy': strategy_type,
        'timestamp': datetime.now().isoformat()
    }
