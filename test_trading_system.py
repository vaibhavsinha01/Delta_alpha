import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from main_binance import MartingaleManager, RiskManager, TradeStateManager, check_entry_conditions

def generate_test_data(n_candles=100):
    """Generate synthetic OHLCV data for testing"""
    np.random.seed(42)  # For reproducibility
    
    # Generate base price series
    base_price = 100
    prices = [base_price]
    for _ in range(n_candles-1):
        change = np.random.normal(0, 1)  # Random walk
        new_price = prices[-1] * (1 + change/100)
        prices.append(new_price)
    
    # Create DataFrame
    dates = [datetime.now() - timedelta(minutes=i) for i in range(n_candles)]
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
        'close': [p * (1 + np.random.normal(0, 0.001)) for p in prices],
        'volume': np.random.uniform(1000, 5000, n_candles)
    })
    
    # Add indicator columns
    df['RSI'] = np.random.uniform(0, 100, n_candles)
    df['rsi_buy'] = df['RSI'] < 30
    df['rsi_sell'] = df['RSI'] > 70
    df['GreenArrow'] = np.random.choice([True, False], n_candles, p=[0.1, 0.9])
    df['RedArrow'] = np.random.choice([True, False], n_candles, p=[0.1, 0.9])
    df['RF_BuySignal'] = np.random.choice([True, False], n_candles, p=[0.1, 0.9])
    df['RF_SellSignal'] = np.random.choice([True, False], n_candles, p=[0.1, 0.9])
    df['gaizy_color'] = np.random.choice(['black', 'bright_green', 'dark_green', 'red', 'pink'], n_candles)
    
    return df

def test_martingale_manager():
    print("\n=== Testing MartingaleManager ===")
    martingale = MartingaleManager(base_amount=100, max_steps=3, multiplier=2, mode='RM1')
    
    # Test initial state
    print(f"Initial trade amount: {martingale.get_trade_amount()}")
    
    # Simulate a loss sequence
    for i in range(3):
        martingale.update_result('loss', -100)
        print(f"After loss {i+1}, trade amount: {martingale.get_trade_amount()}")
    
    # Test win reset
    martingale.update_result('win', 200)
    print(f"After win, trade amount: {martingale.get_trade_amount()}")

def test_risk_manager():
    print("\n=== Testing RiskManager ===")
    risk = RiskManager(sl_buffer_points=10, tp_percent=2, initial_capital=1000)
    
    # Test SL/TP calculation
    entry_price = 100
    prev_row = {'Low': 95, 'High': 105}
    second_last_row = {'Low': 94, 'High': 106}
    
    sl_buy, tp_buy = risk.calculate_sl_tp(entry_price, 'buy', prev_row, second_last_row)
    sl_sell, tp_sell = risk.calculate_sl_tp(entry_price, 'sell', prev_row, second_last_row)
    
    print(f"Buy SL: {sl_buy}, TP: {tp_buy}")
    print(f"Sell SL: {sl_sell}, TP: {tp_sell}")
    
    # Test equity tracking
    risk.update_equity(100)
    print(f"Equity after win: {risk.equity}")
    risk.update_equity(-50)
    print(f"Equity after loss: {risk.equity}")
    print(f"Max drawdown: {risk.max_drawdown}%")

def test_trade_state_manager():
    print("\n=== Testing TradeStateManager ===")
    state = TradeStateManager()
    
    # Test condition changes
    conditions1 = {'rsi_signal': True, 'ib_signal': False}
    conditions2 = {'rsi_signal': True, 'ib_signal': True}
    
    print(f"Conditions changed: {state.check_conditions_changed(conditions1)}")
    print(f"Conditions changed again: {state.check_conditions_changed(conditions2)}")
    
    # Test x_loss counting
    state.entry_price = 100
    state.close_trade('x_loss')
    print(f"X-loss count: {state.x_loss_count}")
    print(f"Should trigger martingale: {state.should_trigger_martingale()}")

def test_entry_conditions():
    print("\n=== Testing Entry Conditions ===")
    df = generate_test_data()
    trade_state = TradeStateManager()
    
    # Test different K values
    for K in [0, 1, 2, 3]:
        print(f"\nTesting K={K}")
        for i in range(2, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            second_last_row = df.iloc[i-2]
            
            signal = check_entry_conditions(row, prev_row, second_last_row)
            if signal:
                print(f"Signal generated at index {i}: {signal}")

def main():
    print("Starting trading system tests...")
    
    test_martingale_manager()
    test_risk_manager()
    test_trade_state_manager()
    test_entry_conditions()
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main() 