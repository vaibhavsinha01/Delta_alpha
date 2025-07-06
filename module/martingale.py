from config import *

class MartingaleManager:
    def __init__(self, base_amount=INITIAL_CAPITAL, mode=MARTINGALE_MODE):
        self.base_amount = base_amount
        self.current_amount = base_amount
        self.current_step = 0
        self.mode = mode
        self.consecutive_losses = 0
        self.last_win_amount = 0
        
    def get_trade_amount(self):
        """Get the current trade amount based on martingale mode"""
        if self.mode == 'RM1':
            # Use predefined leverage multipliers
            leverage = MARTINGALE_LEVERAGE_MULTIPLIERS[min(self.current_step, len(MARTINGALE_LEVERAGE_MULTIPLIERS)-1)]
            return self.base_amount * leverage
        else:  # RM2
            return self.current_amount
            
    def update_result(self, result, pnl):
        """Update martingale state based on trade result"""
        if result == 'win':
            self.consecutive_losses = 0
            self.last_win_amount = pnl
            
            if self.mode == 'RM2':
                # Add Y/31 to capital for next trade
                self.current_amount = self.base_amount + (pnl / 31)
            else:  # RM1
                # Reset to base amount after win
                self.current_amount = self.base_amount
                self.current_step = 0
                
        else:  # loss
            self.consecutive_losses += 1
            
            if self.mode == 'RM1':
                if self.current_step < MARTINGALE_MAX_STEPS - 1:
                    self.current_step += 1
                else:
                    # Reset after max steps
                    self.current_step = 0
                    self.current_amount = self.base_amount
            else:  # RM2
                # Keep same amount for next trade
                pass
                
        # Check if we need to reset due to max consecutive losses
        if self.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
            self.reset()
            
    def reset(self):
        """Reset martingale to initial state"""
        self.current_amount = self.base_amount
        self.current_step = 0
        self.consecutive_losses = 0
        self.last_win_amount = 0
        
    def force_martingale(self):
        """Force martingale step for next trade (used for x_loss)"""
        if self.mode == 'RM1':
            if self.current_step < MARTINGALE_MAX_STEPS - 1:
                self.current_step += 1
            else:
                self.reset()
        # No action needed for RM2 as it maintains same amount 