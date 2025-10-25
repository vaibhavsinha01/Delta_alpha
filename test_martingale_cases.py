#!/usr/bin/env python3
"""
Comprehensive test for all 14 martingale cases to verify leverage escalation logic
"""

import time
import sys
import os

# Add the current directory to path to import from main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class MartingaleManager:
    def __init__(self, base_capital, base_leverage=1):
        self.base_capital = base_capital
        self.base_leverage = base_leverage
        self.current_level = 0
        self.leverage_multipliers = [1, 2, 4, 8, 16]
        self.max_levels = 5
        self.last_trade_result = None
        self.balance_before = None

        # Position tracking
        self.entry_signal = None
        self.position_order_id = None
        self.last_tp_price = None
        self.last_sl_price = None
        self.last_entry_price = None
        self.last_direction = None
        self.last_quantity = None
        self.h_pos = 0
        
        # Double trigger tracking
        self.last_loss_timestamp = None
        self.last_loss_type = None  # 'sl' or 'fake'
        self.pending_second_increment = False 
        self.start_elevated_after_martingale = False
        self.double_trigger_occurred_this_cycle = False
        self.skip_fake_losses_this_cycle = False
        self.in_martingale_cycle = False
        
        # Fake loss flag tracking for elevated starts
        self.fake_loss_flag = False
        self.sl_cycle_started = False

    def get_leverage(self):
        """Get current leverage based on RM1 system with post-martingale elevation"""
        try:
            # If we just completed martingale and are at level 0, start at level 1 instead
            if self.current_level == 0 and self.start_elevated_after_martingale:
                effective_level = 1  # Start at 20x instead of 10x
            else:
                effective_level = self.current_level
                
            leverage = self.base_leverage * self.leverage_multipliers[effective_level]
            return leverage
        except Exception as e:
            print(f"Error getting leverage: {e}")
            return self.base_leverage

    def update_trade_result(self, result, is_fake_trigger=False):
        try:
            current_time = time.time()
            
            if result == 'win':
                # Handle win logic with fake loss flag consideration
                if self.current_level > 0:
                    # Martingale cycle completed - check for fake loss flag
                    if self.fake_loss_flag:
                        # Fake loss flag is set, next trade starts elevated
                        self.start_elevated_after_martingale = True
                        self.fake_loss_flag = False  # Clear the flag after using it
                        print("Martingale complete with fake loss flag! Next at 20x (elevated start)")
                    else:
                        # Normal martingale completion, return to base
                        self.start_elevated_after_martingale = False
                        print("Martingale complete, back to base")
                elif self.current_level == 0 and self.start_elevated_after_martingale:
                    # We're at elevated start (20x), next win returns to base (10x)
                    self.start_elevated_after_martingale = False
                    print("Elevated cycle complete, back to 10x")
                
                # Reset all tracking
                self.current_level = 0
                self.last_loss_timestamp = None
                self.last_loss_type = None
                self.pending_second_increment = False
                self.skip_fake_losses_this_cycle = False
                self.sl_cycle_started = False
                print(f"Trade won! Reset to L0, leverage: {self.get_leverage()}x")
                    
            elif result == 'loss':
                loss_type = 'fake' if is_fake_trigger else 'sl'
                print(f"LOSS detected: type={loss_type}, level={self.current_level}")
                
                # Check for double trigger (SL + fake loss in same trade)
                if self.last_loss_timestamp is not None:
                    time_diff = current_time - self.last_loss_timestamp
                    
                    if time_diff <= 15 and self.last_loss_type != loss_type:
                        print(f"DOUBLE TRIGGER! {self.last_loss_type.upper()} + {loss_type.upper()}")
                        print("Double trigger detected - treating as SL only")
                        
                        # Double trigger is treated as SL event only
                        if self.last_loss_type == 'fake':
                            # Undo the fake loss increment that already happened
                            self.current_level -= 1
                            print("Undoing fake loss increment for double trigger")
                        
                        # Now treat as SL only
                        self.sl_cycle_started = True
                        self.current_level += 1
                        
                        # CRITICAL: Clear fake loss flag for double trigger since it's treated as SL only
                        if self.fake_loss_flag:
                            self.fake_loss_flag = False
                            print("Clearing fake loss flag for double trigger (treated as SL only)")
                        
                        # Clear tracking
                        self.last_loss_timestamp = None
                        self.last_loss_type = None
                        print(f"DOUBLE TRIGGER handled as SL only, level: {self.current_level}")
                        return
                
                # Normal loss handling
                if loss_type == 'sl':
                    # SL loss - increment level and mark SL cycle as started
                    self.sl_cycle_started = True
                    if self.current_level >= self.max_levels - 1:
                        # Reset to elevated start if fake loss flag is set
                        if self.fake_loss_flag:
                            self.current_level = 1  # Start at 20x
                            # DON'T clear fake_loss_flag here - it should be preserved for elevated start
                            print(f"Max level reached with fake loss flag, resetting to level 1 (20x)")
                        else:
                            self.current_level = 0  # Back to base
                            print(f"Max level reached, resetting to 0")
                    else:
                        # CRITICAL FIX: Handle elevated start properly
                        if self.current_level == 0 and self.start_elevated_after_martingale:
                            # We're at elevated start (20x), next SL should go to level 2 (40x)
                            self.current_level = 2
                            self.start_elevated_after_martingale = False  # Clear elevated flag
                            print(f"SL LOSS at elevated start: Level {self.current_level} (40x)")
                        else:
                            self.current_level += 1
                            print(f"SL LOSS: Level {self.current_level}")
                        
                elif loss_type == 'fake':
                    # Fake loss handling
                    if not self.sl_cycle_started:
                        # No SL cycle started yet - allow fake loss to increase level
                        if self.current_level >= self.max_levels - 1:
                            if self.fake_loss_flag:
                                self.current_level = 1  # Start at 20x
                                self.fake_loss_flag = False
                                print(f"Max level reached with fake loss flag, resetting to level 1 (20x)")
                            else:
                                self.current_level = 0  # Back to base
                                print(f"Max level reached, resetting to 0")
                        else:
                            # CRITICAL FIX: Handle elevated start properly for fake losses
                            if self.current_level == 0 and self.start_elevated_after_martingale:
                                # We're at elevated start (20x), fake loss should go to level 2 (40x)
                                self.current_level = 2
                                self.start_elevated_after_martingale = False  # Clear elevated flag
                                print(f"FAKE LOSS at elevated start: Level {self.current_level} (40x)")
                            else:
                                self.current_level += 1
                                print(f"FAKE LOSS (no SL cycle): Level {self.current_level}")
                    else:
                        # SL cycle has started - fake loss doesn't increase level but sets flag
                        self.fake_loss_flag = True
                        print(f"FAKE LOSS (SL cycle active): Flag set, level remains {self.current_level}")
                
                self.last_loss_timestamp = current_time
                self.last_loss_type = loss_type
                    
            print(f"Status: Level={self.current_level}, Elevated={self.start_elevated_after_martingale}, FakeFlag={self.fake_loss_flag}, SLCycle={self.sl_cycle_started}")
            print(f"Leverage: {self.get_leverage()}x, Level: {self.current_level}")
            
        except Exception as e:
            print(f"Error in update_trade_result: {e}")

def test_all_14_cases():
    """Test all 14 martingale cases"""
    print("=" * 80)
    print("TESTING ALL 14 MARTINGALE SCENARIOS")
    print("=" * 80)
    
    # Test Case 1: (initial leverage 10) -> sl -> (20) -> fake loss max limit reached -> (20) -> sl -> (40) -> sl -> (80) -> win -> 20(since the fake loss max limit was previously reached)
    print("\nCASE 1: SL -> fake loss limit -> SL -> SL -> Win -> 20x (elevated start)")
    test1 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test1.current_level}, Leverage {test1.get_leverage()}x")
    
    test1.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test1.current_level}, Leverage {test1.get_leverage()}x")
    
    # Simulate fake loss limit reached during SL cycle
    test1.fake_loss_flag = True
    print(f"Fake loss limit reached, flag set: {test1.fake_loss_flag}")
    
    test1.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test1.current_level}, Leverage {test1.get_leverage()}x")
    
    test1.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test1.current_level}, Leverage {test1.get_leverage()}x")
    
    test1.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test1.current_level}, Leverage {test1.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 20x (elevated start) - {'PASS' if test1.get_leverage() == 20 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 2: (initial leverage 10) -> fake loss max limit reached -> 20(since the fake loss is without the start of sl -> no cycle for it) -> win -> 10
    print("\nCASE 2: fake loss limit (no SL) -> Win -> 10x")
    test2 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test2.current_level}, Leverage {test2.get_leverage()}x")
    
    test2.update_trade_result('loss', is_fake_trigger=True)  # fake loss
    print(f"After fake loss: Level {test2.current_level}, Leverage {test2.get_leverage()}x")
    
    test2.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test2.current_level}, Leverage {test2.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (base) - {'PASS' if test2.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 3: (initial leverage 10) -> double trigger(sl + fake loss at the same time - same trade) -> 20 -> sl -> 40 -> sl -> 80 -> 160 -> sl -> 10(no elevated level since the fake loss for the double trigger isn't counted , double trigger counted as an sl)
    print("\nCASE 3: double trigger -> SL -> SL -> SL -> Win -> 10x (no elevated start)")
    test3 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test3.current_level}, Leverage {test3.get_leverage()}x")
    
    # Double trigger
    test3.update_trade_result('loss', is_fake_trigger=True)
    test3.last_loss_timestamp = time.time() - 5
    test3.last_loss_type = 'fake'
    test3.update_trade_result('loss', is_fake_trigger=False)
    print(f"After double trigger: Level {test3.current_level}, Leverage {test3.get_leverage()}x")
    
    test3.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test3.current_level}, Leverage {test3.get_leverage()}x")
    
    test3.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test3.current_level}, Leverage {test3.get_leverage()}x")
    
    test3.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test3.current_level}, Leverage {test3.get_leverage()}x")
    
    test3.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test3.current_level}, Leverage {test3.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (base, no elevated start) - {'PASS' if test3.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 4: (initial leverage 10) -> double trigger(sl + fake loss at the same time - same trade) -> 20 -> fake loss limit reached -> 20(since the sl cycle has started) -> sl -> 40 -> win -> 20(elevated level since the fake loss limit reached not due to double trigger - which is treated only as a sl) -> sl -> 40 -> win -> 10
    print("\nCASE 4: double trigger -> fake loss limit -> SL -> Win -> 20x -> SL -> Win -> 10x")
    test4 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test4.current_level}, Leverage {test4.get_leverage()}x")
    
    # Double trigger
    test4.update_trade_result('loss', is_fake_trigger=True)
    test4.last_loss_timestamp = time.time() - 5
    test4.last_loss_type = 'fake'
    test4.update_trade_result('loss', is_fake_trigger=False)
    print(f"After double trigger: Level {test4.current_level}, Leverage {test4.get_leverage()}x")
    
    # Fake loss limit reached during SL cycle
    test4.fake_loss_flag = True
    print(f"Fake loss limit reached, flag set: {test4.fake_loss_flag}")
    
    test4.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test4.current_level}, Leverage {test4.get_leverage()}x")
    
    test4.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test4.current_level}, Leverage {test4.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 20x (elevated start) - {'PASS' if test4.get_leverage() == 20 else 'FAIL'}")
    
    test4.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test4.current_level}, Leverage {test4.get_leverage()}x")
    
    test4.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test4.current_level}, Leverage {test4.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (back to base) - {'PASS' if test4.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 5: (initial leverage 10) -> double trigger(sl+fake loss at the same time - same trade) -> 20 -> double trigger(sl+fake loss at the same time - same trade) -> 40 -> fake loss -> 40 -> fake loss -> 40(since sl occured once before) -> win -> 20(since there was a previous fake loss) -> win -> 10
    print("\nCASE 5: double trigger -> double trigger -> fake loss -> fake loss -> Win -> 20x -> Win -> 10x")
    test5 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test5.current_level}, Leverage {test5.get_leverage()}x")
    
    # First double trigger
    test5.update_trade_result('loss', is_fake_trigger=True)
    test5.last_loss_timestamp = time.time() - 5
    test5.last_loss_type = 'fake'
    test5.update_trade_result('loss', is_fake_trigger=False)
    print(f"After first double trigger: Level {test5.current_level}, Leverage {test5.get_leverage()}x")
    
    # Second double trigger
    test5.update_trade_result('loss', is_fake_trigger=True)
    test5.last_loss_timestamp = time.time() - 5
    test5.last_loss_type = 'fake'
    test5.update_trade_result('loss', is_fake_trigger=False)
    print(f"After second double trigger: Level {test5.current_level}, Leverage {test5.get_leverage()}x")
    
    # Fake losses (SL cycle has started)
    test5.update_trade_result('loss', is_fake_trigger=True)  # fake loss
    print(f"After fake loss: Level {test5.current_level}, Leverage {test5.get_leverage()}x")
    
    test5.update_trade_result('loss', is_fake_trigger=True)  # fake loss
    print(f"After fake loss: Level {test5.current_level}, Leverage {test5.get_leverage()}x")
    
    test5.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test5.current_level}, Leverage {test5.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 20x (elevated start) - {'PASS' if test5.get_leverage() == 20 else 'FAIL'}")
    
    test5.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test5.current_level}, Leverage {test5.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (back to base) - {'PASS' if test5.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 6: (initial leverage 10) -> double trigger(sl + fake loss) -> 20 -> sl -> 40 -> fake loss -> 40 -> sl -> 80 -> sl -> 160 -> sl -> 20(elevated start due to fake loss stack) -> win -> 10
    print("\nCASE 6: double trigger -> SL -> fake loss -> SL -> SL -> SL -> 20x -> Win -> 10x")
    test6 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test6.current_level}, Leverage {test6.get_leverage()}x")
    
    # Double trigger
    test6.update_trade_result('loss', is_fake_trigger=True)
    test6.last_loss_timestamp = time.time() - 5
    test6.last_loss_type = 'fake'
    test6.update_trade_result('loss', is_fake_trigger=False)
    print(f"After double trigger: Level {test6.current_level}, Leverage {test6.get_leverage()}x")
    
    test6.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test6.current_level}, Leverage {test6.get_leverage()}x")
    
    # Fake loss during SL cycle
    test6.fake_loss_flag = True
    print(f"Fake loss flag set: {test6.fake_loss_flag}")
    
    test6.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test6.current_level}, Leverage {test6.get_leverage()}x")
    
    test6.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test6.current_level}, Leverage {test6.get_leverage()}x")
    
    test6.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test6.current_level}, Leverage {test6.get_leverage()}x")
    
    test6.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test6.current_level}, Leverage {test6.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 20x (elevated start) - {'PASS' if test6.get_leverage() == 20 else 'FAIL'}")
    
    test6.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test6.current_level}, Leverage {test6.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (back to base) - {'PASS' if test6.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 7: (initial leverage 10) -> double trigger(sl + fake loss) -> 20 -> double trigger(sl + fake loss) -> 40 -> win -> 10 -> win -> 10
    print("\nCASE 7: double trigger -> double trigger -> Win -> 10x -> Win -> 10x")
    test7 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test7.current_level}, Leverage {test7.get_leverage()}x")
    
    # First double trigger
    test7.update_trade_result('loss', is_fake_trigger=True)
    test7.last_loss_timestamp = time.time() - 5
    test7.last_loss_type = 'fake'
    test7.update_trade_result('loss', is_fake_trigger=False)
    print(f"After first double trigger: Level {test7.current_level}, Leverage {test7.get_leverage()}x")
    
    # Second double trigger
    test7.update_trade_result('loss', is_fake_trigger=True)
    test7.last_loss_timestamp = time.time() - 5
    test7.last_loss_type = 'fake'
    test7.update_trade_result('loss', is_fake_trigger=False)
    print(f"After second double trigger: Level {test7.current_level}, Leverage {test7.get_leverage()}x")
    
    test7.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test7.current_level}, Leverage {test7.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (base) - {'PASS' if test7.get_leverage() == 10 else 'FAIL'}")
    
    test7.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test7.current_level}, Leverage {test7.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (base) - {'PASS' if test7.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 8: (initial leverage 10) -> win -> 10
    print("\nCASE 8: Win -> 10x")
    test8 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test8.current_level}, Leverage {test8.get_leverage()}x")
    
    test8.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test8.current_level}, Leverage {test8.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (base) - {'PASS' if test8.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 9: (initial leverage 10) -> sl -> 20 -> sl -> 40 -> win > 10
    print("\nCASE 9: SL -> SL -> Win -> 10x")
    test9 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test9.current_level}, Leverage {test9.get_leverage()}x")
    
    test9.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test9.current_level}, Leverage {test9.get_leverage()}x")
    
    test9.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test9.current_level}, Leverage {test9.get_leverage()}x")
    
    test9.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test9.current_level}, Leverage {test9.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (base) - {'PASS' if test9.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 10: (initial leverage 10) -> sl -> 20 -> fake loss -> 20 -> win -> 20(elevated start due to previous fake loss) -> sl -> 40 -> win -> 10
    print("\nCASE 10: SL -> fake loss -> Win -> 20x -> SL -> Win -> 10x")
    test10 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test10.current_level}, Leverage {test10.get_leverage()}x")
    
    test10.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test10.current_level}, Leverage {test10.get_leverage()}x")
    
    # Fake loss during SL cycle
    test10.fake_loss_flag = True
    print(f"Fake loss flag set: {test10.fake_loss_flag}")
    
    test10.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test10.current_level}, Leverage {test10.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 20x (elevated start) - {'PASS' if test10.get_leverage() == 20 else 'FAIL'}")
    
    test10.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test10.current_level}, Leverage {test10.get_leverage()}x")
    
    test10.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test10.current_level}, Leverage {test10.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (back to base) - {'PASS' if test10.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 11: (initial leverage 10) -> sl -> 20 -> sl -> 40 -> fake loss -> 40 -> win -> 20(this is for fake loss - elevated start) -> double trigger(sl+stack) -> 40 -> win -> 10(no elevated start , due to no fake loss) -> fake loss -> 20(increment because no sl in this cycle so nothing stored in fake loss flag) -> win -> 10
    print("\nCASE 11: SL -> SL -> fake loss -> Win -> 20x -> double trigger -> Win -> 10x -> fake loss -> Win -> 10x")
    test11 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test11.current_level}, Leverage {test11.get_leverage()}x")
    
    test11.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test11.current_level}, Leverage {test11.get_leverage()}x")
    
    test11.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test11.current_level}, Leverage {test11.get_leverage()}x")
    
    # Fake loss during SL cycle
    test11.fake_loss_flag = True
    print(f"Fake loss flag set: {test11.fake_loss_flag}")
    
    test11.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test11.current_level}, Leverage {test11.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 20x (elevated start) - {'PASS' if test11.get_leverage() == 20 else 'FAIL'}")
    
    # Double trigger
    test11.update_trade_result('loss', is_fake_trigger=True)
    test11.last_loss_timestamp = time.time() - 5
    test11.last_loss_type = 'fake'
    test11.update_trade_result('loss', is_fake_trigger=False)
    print(f"After double trigger: Level {test11.current_level}, Leverage {test11.get_leverage()}x")
    
    test11.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test11.current_level}, Leverage {test11.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (back to base) - {'PASS' if test11.get_leverage() == 10 else 'FAIL'}")
    
    # Fake loss without SL cycle
    test11.update_trade_result('loss', is_fake_trigger=True)  # fake loss
    print(f"After fake loss: Level {test11.current_level}, Leverage {test11.get_leverage()}x")
    
    test11.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test11.current_level}, Leverage {test11.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (back to base) - {'PASS' if test11.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 12: (initial leverage 10) -> sl -> 20 -> sl -> 40 -> fake loss -> 40 -> win -> 20(since there is a previous fake loss and the flag was set - now flag is cleared) -> double trigger(sl + fake loss stack) -> 40 -> win -> 10(no previous fake loss flag) -> sl -> 20 -> sl -> 40 -> sl -> 80 -> fake loss(fake loss flag set) -> 80 -> win -> 20(fake loss flag cleared - elevated start) -> win -> 10
    print("\nCASE 12: Complex scenario with multiple fake loss flags")
    test12 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test12.current_level}, Leverage {test12.get_leverage()}x")
    
    # First part: SL -> SL -> fake loss -> Win -> 20x
    test12.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test12.current_level}, Leverage {test12.get_leverage()}x")
    
    test12.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test12.current_level}, Leverage {test12.get_leverage()}x")
    
    # Fake loss during SL cycle
    test12.fake_loss_flag = True
    print(f"Fake loss flag set: {test12.fake_loss_flag}")
    
    test12.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test12.current_level}, Leverage {test12.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 20x (elevated start) - {'PASS' if test12.get_leverage() == 20 else 'FAIL'}")
    
    # Double trigger
    test12.update_trade_result('loss', is_fake_trigger=True)
    test12.last_loss_timestamp = time.time() - 5
    test12.last_loss_type = 'fake'
    test12.update_trade_result('loss', is_fake_trigger=False)
    print(f"After double trigger: Level {test12.current_level}, Leverage {test12.get_leverage()}x")
    
    test12.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test12.current_level}, Leverage {test12.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (back to base) - {'PASS' if test12.get_leverage() == 10 else 'FAIL'}")
    
    # Second part: SL -> SL -> SL -> fake loss -> Win -> 20x -> Win -> 10x
    test12.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test12.current_level}, Leverage {test12.get_leverage()}x")
    
    test12.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test12.current_level}, Leverage {test12.get_leverage()}x")
    
    test12.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test12.current_level}, Leverage {test12.get_leverage()}x")
    
    # Fake loss during SL cycle
    test12.fake_loss_flag = True
    print(f"Fake loss flag set: {test12.fake_loss_flag}")
    
    test12.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test12.current_level}, Leverage {test12.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 20x (elevated start) - {'PASS' if test12.get_leverage() == 20 else 'FAIL'}")
    
    test12.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test12.current_level}, Leverage {test12.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (back to base) - {'PASS' if test12.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 13: (initial leverage 10) -> double trigger(sl + fake loss) -> 20 -> win -> 10
    print("\nCASE 13: double trigger -> Win -> 10x")
    test13 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test13.current_level}, Leverage {test13.get_leverage()}x")
    
    # Double trigger
    test13.update_trade_result('loss', is_fake_trigger=True)
    test13.last_loss_timestamp = time.time() - 5
    test13.last_loss_type = 'fake'
    test13.update_trade_result('loss', is_fake_trigger=False)
    print(f"After double trigger: Level {test13.current_level}, Leverage {test13.get_leverage()}x")
    
    test13.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test13.current_level}, Leverage {test13.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (base) - {'PASS' if test13.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 14: (initial leverage 10) -> double trigger(sl + fake loss) -> 20 -> fake loss -> 20 -> win -> 20(elevated level due to prev fake loss)
    print("\nCASE 14: double trigger -> fake loss -> Win -> 20x")
    test14 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test14.current_level}, Leverage {test14.get_leverage()}x")
    
    # Double trigger
    test14.update_trade_result('loss', is_fake_trigger=True)
    test14.last_loss_timestamp = time.time() - 5
    test14.last_loss_type = 'fake'
    test14.update_trade_result('loss', is_fake_trigger=False)
    print(f"After double trigger: Level {test14.current_level}, Leverage {test14.get_leverage()}x")
    
    # Fake loss during SL cycle
    test14.fake_loss_flag = True
    print(f"Fake loss flag set: {test14.fake_loss_flag}")
    
    test14.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test14.current_level}, Leverage {test14.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 20x (elevated start) - {'PASS' if test14.get_leverage() == 20 else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    # Test Case 15: (initial leverage 10) -> sl -> 20 -> fake loss -> 20 -> sl -> 40 -> win -> 20 -> sl -> 40 -> win -> 10
    print("\nCASE 15: SL -> fake loss -> SL -> Win -> 20x -> SL -> Win -> 10x")
    test15 = MartingaleManager(1000, 10)
    print(f"Initial: Level {test15.current_level}, Leverage {test15.get_leverage()}x")
    
    test15.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test15.current_level}, Leverage {test15.get_leverage()}x")
    
    # Fake loss during SL cycle
    test15.fake_loss_flag = True
    print(f"Fake loss flag set: {test15.fake_loss_flag}")
    
    test15.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test15.current_level}, Leverage {test15.get_leverage()}x")
    
    test15.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test15.current_level}, Leverage {test15.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 20x (elevated start) - {'PASS' if test15.get_leverage() == 20 else 'FAIL'}")
    
    test15.update_trade_result('loss', is_fake_trigger=False)  # SL
    print(f"After SL: Level {test15.current_level}, Leverage {test15.get_leverage()}x")
    
    test15.update_trade_result('win', is_fake_trigger=False)  # Win
    print(f"After Win: Level {test15.current_level}, Leverage {test15.get_leverage()}x")
    print(f"Expected: Level 0, Leverage 10x (back to base) - {'PASS' if test15.get_leverage() == 10 else 'FAIL'}")
    
    print("\n" + "=" * 80)
    print("ALL 15 TEST CASES COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    test_all_14_cases()
