import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates

import pandas as pd
import numpy as np

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates


def plot_inside_bar_boxes(df):
    df_mpf = df.copy()

    # Rename for mplfinance compatibility
    df_mpf.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)

    # Prepare breakout arrows
    df_mpf['GreenSignal'] = np.where(df_mpf['GreenArrow'], df_mpf['Close'], np.nan)
    df_mpf['RedSignal'] = np.where(df_mpf['RedArrow'], df_mpf['Close'], np.nan)

    addplots = [
        mpf.make_addplot(df_mpf['GreenSignal'], type='scatter', markersize=100, marker='^', color='green'),
        mpf.make_addplot(df_mpf['RedSignal'], type='scatter', markersize=100, marker='v', color='red')
    ]

    # Plot using mplfinance
    fig, axlist = mpf.plot(
        df_mpf,
        type='candle',
        style='charles',  # 🔄 Changed from 'yahoo' to 'charles' for cleaner plotting
        title='Inside Bar Boxes with Breakout Signals',
        ylabel='Price',
        addplot=addplots,
        figratio=(14, 7),
        tight_layout=True,
        returnfig=True,
        datetime_format='%Y-%m-%d',
        xrotation=45
    )

    ax = axlist[0]  # Main chart axis
    dates = df_mpf.index
    x = mdates.date2num(dates)

    # Box tracking logic
    in_box = False
    box_start = None
    box_end = None
    box_high = None
    box_low = None

    for i in range(len(df_mpf)):
        row = df_mpf.iloc[i]
        if not np.isnan(row['BoxHigh']) and not np.isnan(row['BoxLow']):
            if not in_box:
                # Start of new box
                in_box = True
                box_start = x[i]
                box_high = row['BoxHigh']
                box_low = row['BoxLow']
            box_end = x[i]
        else:
            if in_box:
                # Draw the box from box_start to box_end
                ax.fill_betweenx(
                    y=[box_low, box_high],
                    x1=box_start,
                    x2=box_end,
                    color='orange',
                    alpha=0.2
                )
                in_box = False

    # Final box if it ended at the last candle
    if in_box:
        ax.fill_betweenx(
            y=[box_low, box_high],
            x1=box_start,
            x2=box_end,
            color='orange',
            alpha=0.2
        )

    plt.show()

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle

class Box:
    """
    A class to mimic PineScript's box functionality
    """
    def __init__(self, start_index, high, end_index, low, color='blue', transparency=90):
        self.start_index = start_index
        self.end_index = end_index
        self.high = high
        self.low = low
        self.color = color
        self.transparency = transparency
        self.id = id(self)
        self.deleted = False
        
    def set_right(self, new_end):
        """Update the right edge of the box"""
        self.end_index = new_end
        
    def delete(self):
        """Mark box for deletion"""
        self.deleted = True
        
    def draw(self, ax, x_values):
        """Draw the box on the given matplotlib axis"""
        start_x = x_values[self.start_index]
        end_x = x_values[self.end_index]
        width = end_x - start_x
        height = self.high - self.low
        
        alpha = 1 - (self.transparency / 100)
        rect = Rectangle(
            (start_x, self.low),
            width,
            height,
            linewidth=1,
            edgecolor=self.color,
            facecolor=self.color,
            alpha=alpha
        )
        ax.add_patch(rect)

def calculate_inside_bar_boxes(df, high_low_buffer=0.0, mintick=0.05, bar_highlight=True, 
                              show_only_last_box=False, show_break=True, 
                              bg_color='blue', bg_transparency=90, inside_bars_color='orange'):
    """
    Calculate inside bar boxes similar to the PineScript implementation.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC data
    high_low_buffer : float
        Buffer zone around high-low (in mintick units)
    mintick : float
        Minimum tick size
    bar_highlight : bool
        Whether to mark inside bars
    show_only_last_box : bool
        Show only the last box
    show_break : bool
        Show box breakouts
    bg_color : str
        Background color for boxes
    bg_transparency : int
        Box transparency (0-100)
    inside_bars_color : str
        Color for inside bars
        
    Returns:
    --------
    pandas.DataFrame
        DataFrame with added box information and list of boxes
    """
    df = df.copy()

    # Ensure datetime index
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Initialize columns
    df['IsIB'] = False
    df['BoxHigh'] = np.nan
    df['BoxLow'] = np.nan
    df['GreenArrow'] = False
    df['RedArrow'] = False
    df['BarColor'] = np.nan  # For bar coloring equivalent to barcolor()

    # State tracking variables (equivalent to PineScript vars)
    box_high = np.nan
    box_low = np.nan
    bar_index = 1
    f_flag = False  # Equivalent to 'f' in PineScript
    boxes = []
    current_box = None

    # Process each bar - starting from second bar (index 1)
    for i in range(1, len(df)):
        prev = df.iloc[i - 1]  # Previous bar
        curr = df.iloc[i]      # Current bar
        prev_is_ib = df.iloc[i-1]['IsIB'] if i > 1 else False  # Previous bar IB status

        # Calculate buffered high/low for inside bar logic
        hp = prev['high'] + high_low_buffer * mintick
        lp = prev['low'] - high_low_buffer * mintick

        # Inside bar condition - exactly as in PineScript
        is_ib = (curr['close'] <= hp and curr['close'] >= lp and 
                 curr['open'] <= hp and curr['open'] >= lp)
        
        df.iat[i, df.columns.get_loc('IsIB')] = is_ib
        
        # Bar color logic
        if is_ib and bar_highlight:
            df.iat[i, df.columns.get_loc('BarColor')] = inside_bars_color
        
        # Box logic - simulating barstate.isconfirmed with each row calculation
        
        # Condition 1: New inside bar (current is IB, previous was not)
        if is_ib and not prev_is_ib:
            box_high = prev['high']
            box_low = prev['low']
            f_flag = True
            
            # Store box high/low values in dataframe
            df.iat[i, df.columns.get_loc('BoxHigh')] = box_high
            df.iat[i, df.columns.get_loc('BoxLow')] = box_low
            
            # Create new box - equivalent to box.new() in PineScript
            if show_only_last_box and current_box is not None:
                current_box = None  # "Delete" previous box
                boxes = [box for box in boxes if not box.deleted]  # Remove deleted boxes
                
            current_box = Box(i-1, box_high, i, box_low, bg_color, bg_transparency)
            boxes.append(current_box)
            bar_index = bar_index + 1
            
        # Condition 2: Continuing inside bar sequence
        elif is_ib and prev_is_ib:
            if not np.isnan(box_high):
                df.iat[i, df.columns.get_loc('BoxHigh')] = box_high
                df.iat[i, df.columns.get_loc('BoxLow')] = box_low
                
                # Update box right edge
                if current_box is not None:
                    current_box.set_right(i)
            bar_index = bar_index + 1
            
        # Condition 3: End of inside bar sequence (prev was IB, current is not)
        elif prev_is_ib and not is_ib:
            if current_box is not None:
                current_box.set_right(i)  # Update box right edge
                
            # Check for breakouts exactly as in PineScript
            if show_break and f_flag:
                if prev['close'] <= box_high and curr['close'] > box_high:
                    df.iat[i, df.columns.get_loc('GreenArrow')] = True
                elif prev['close'] >= box_low and curr['close'] < box_low:
                    df.iat[i, df.columns.get_loc('RedArrow')] = True
            
            bar_index = 1
            
        # Condition 4: No inside bar sequence
        elif not prev_is_ib and not is_ib:
            f_flag = False
    
    return df, boxes
