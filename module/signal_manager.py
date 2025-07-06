from config import *

class SignalManager:
    def __init__(self):
        self.signal_memory = {}  # Store used signals
        self.last_trade_result = None
        self.waiting_for_fail = A == 0  # If A=0, wait for one fail trade
        
    def should_take_trade(self, signals, k_value=K):
        """Determine if we should take a trade based on K parameter and signals"""
        if self.waiting_for_fail and self.last_trade_result != 'loss':
            return False
            
        if k_value == 0:  # All strategies
            return self._check_all_strategies(signals)
        elif k_value == 1:  # RSI1 + IB box
            return self._check_rsi_ib_strategy(signals)
        elif k_value == 2:  # RF + IB box
            return self._check_rf_ib_strategy(signals)
        elif k_value == 3:  # RF + RSI2
            return self._check_rf_rsi_strategy(signals)
        return False
        
    def _check_all_strategies(self, signals):
        """Check all strategy combinations"""
        return (self._check_rsi_ib_strategy(signals) or 
                self._check_rf_ib_strategy(signals) or 
                self._check_rf_rsi_strategy(signals))
                
    def _check_rsi_ib_strategy(self, signals):
        """Check RSI1 + IB box strategy"""
        if signals['rsi_gaizy'] == 'black':
            # For black signal, only use IB box signals
            return signals['ib_buy'] or signals['ib_sell']
            
        # For other colors, check RSI and IB box alignment
        if signals['rsi_gaizy'] in ['bright_green', 'dark_green']:
            return signals['ib_buy']  # Only buy for green
        elif signals['rsi_gaizy'] == 'red':
            return signals['ib_sell']  # Only sell for red
        elif signals['rsi_gaizy'] == 'pink':
            return signals['ib_sell']  # Strong sell for pink
        else:
            return signals['ib_buy'] or signals['ib_sell']  # Any valid trade
            
    def _check_rf_ib_strategy(self, signals):
        """Check RF + IB box strategy"""
        # Check if signals occurred in same candle
        if signals['rf_buy'] and signals['ib_buy']:
            return True
        if signals['rf_sell'] and signals['ib_sell']:
            return True
            
        # Check if RF signal was followed by IB box in next candle
        if signals['rf_buy_prev'] and signals['ib_buy']:
            return True
        if signals['rf_sell_prev'] and signals['ib_sell']:
            return True
            
        return False
        
    def _check_rf_rsi_strategy(self, signals):
        """Check RF + RSI2 strategy"""
        # RSI signal must be followed by RF signal in next candle
        if signals['rsi_buy_prev'] and signals['rf_buy']:
            return True
        if signals['rsi_sell_prev'] and signals['rf_sell']:
            return True
            
        # Or both signals in same candle
        if signals['rsi_buy'] and signals['rf_buy']:
            return True
        if signals['rsi_sell'] and signals['rf_sell']:
            return True
            
        return False
        
    def update_trade_result(self, result):
        """Update last trade result"""
        self.last_trade_result = result
        if result == 'loss' and self.waiting_for_fail:
            self.waiting_for_fail = False
            
    def is_signal_used(self, signal_type, signal_value):
        """Check if a signal has been used recently"""
        key = f"{signal_type}_{signal_value}"
        if key in self.signal_memory:
            return True
        self.signal_memory[key] = True
        return False
        
    def clear_old_signals(self):
        """Clear old signals from memory"""
        self.signal_memory.clear() 