"""
Simple Professional Trendline Detector - Version 2
=================================================
CHANGES FROM V1:
- Detects current market trend direction
- Draws ONLY the relevant trendline (support in uptrend, resistance in downtrend)
- Validates angle (filters out < 5° or > 70°)
- More dynamic and accurate

Rules:
1. Find major swing points (highs and lows)
2. Detect current trend direction
3. Draw ONLY the active trendline based on trend
4. Validate: 5-70 degree angle
"""

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mt5_connector import MT5Connector, TIMEFRAMES


def find_major_swing_points(df, order=5):
    """
    Find major swing highs and lows

    Parameters:
    -----------
    df : pd.DataFrame
        OHLC data
    order : int
        Number of candles on each side to compare

    Returns:
    --------
    tuple : (swing_high_indices, swing_low_indices)
    """
    # Find swing highs (resistance pivots)
    swing_high_idx = argrelextrema(df['high'].values, np.greater, order=order)[0]

    # Find swing lows (support pivots)
    swing_low_idx = argrelextrema(df['low'].values, np.less, order=order)[0]

    return list(swing_high_idx), list(swing_low_idx)


def detect_trend_direction(df, lookback=20):
    """
    Detect current market trend direction

    Parameters:
    -----------
    df : pd.DataFrame
        OHLC data
    lookback : int
        Number of recent bars to analyze

    Returns:
    --------
    str : 'UPTREND' or 'DOWNTREND'
    """
    # Get recent data
    recent = df.tail(lookback)

    # Method 1: Price vs Moving Average
    ma_period = min(50, len(df) - 1)
    ma = df['close'].rolling(window=ma_period).mean().iloc[-1]
    current_price = df['close'].iloc[-1]

    # Method 2: Recent price action (comparing first and last in lookback)
    first_price = recent['close'].iloc[0]
    last_price = recent['close'].iloc[-1]
    price_change = last_price - first_price

    # Method 3: Higher highs and higher lows check
    recent_highs = recent['high'].values
    recent_lows = recent['low'].values

    higher_highs = recent_highs[-1] > recent_highs[0]
    higher_lows = recent_lows[-1] > recent_lows[0]

    # Combine signals
    uptrend_signals = 0
    downtrend_signals = 0

    if current_price > ma:
        uptrend_signals += 1
    else:
        downtrend_signals += 1

    if price_change > 0:
        uptrend_signals += 1
    else:
        downtrend_signals += 1

    if higher_highs and higher_lows:
        uptrend_signals += 1
    elif not higher_highs and not higher_lows:
        downtrend_signals += 1

    # Decision
    if uptrend_signals > downtrend_signals:
        return 'UPTREND'
    else:
        return 'DOWNTREND'


def calculate_angle(x1, y1, x2, y2):
    """
    Calculate trendline angle in degrees
    """
    if x2 == x1:
        return 90.0

    # Calculate slope
    slope = (y2 - y1) / (x2 - x1)

    # Convert to angle (normalize by average price)
    avg_price = (y1 + y2) / 2
    angle_rad = np.arctan(slope / avg_price * 100)
    angle_deg = np.degrees(angle_rad)

    return abs(angle_deg)


def find_recent_trendline(df, swing_indices, point_type='high', lookback=60):
    """
    Find the most SIGNIFICANT trendline
    Strategy: Connect the ABSOLUTE LOW/HIGH in lookback period to the MOST RECENT swing point
    """
    if len(swing_indices) < 1:
        return None

    # Get lookback window (last N bars)
    lookback_start = max(0, len(df) - lookback)

    # Find the ABSOLUTE highest/lowest point in the lookback period
    if point_type == 'high':
        # For resistance: find HIGHEST high in lookback
        idx1 = df['high'].iloc[lookback_start:].idxmax()
        price1 = df['high'].iloc[idx1]
    else:
        # For support: find LOWEST low in lookback
        idx1 = df['low'].iloc[lookback_start:].idxmin()
        price1 = df['low'].iloc[idx1]

    # Find the most recent significant swing point (not the current bar)
    # Must be at least 3 bars before current and AFTER the first point
    recent_swings = [idx for idx in swing_indices if idx < len(df) - 3 and idx > idx1]

    if len(recent_swings) == 0:
        # No swing found after idx1, try to find one before
        before_swings = [idx for idx in swing_indices if idx < idx1 and idx >= lookback_start]
        if len(before_swings) > 0:
            # Use the closest swing before idx1
            idx2 = idx1
            price2 = price1
            idx1 = before_swings[-1]
            if point_type == 'high':
                price1 = df['high'].iloc[idx1]
            else:
                price1 = df['low'].iloc[idx1]
        else:
            return None
    else:
        # Use the most recent swing point
        idx2 = recent_swings[-1]
        if point_type == 'high':
            price2 = df['high'].iloc[idx2]
        else:
            price2 = df['low'].iloc[idx2]

    # Calculate slope and angle
    slope = (price2 - price1) / (idx2 - idx1) if idx2 != idx1 else 0
    intercept = price1 - slope * idx1
    angle = calculate_angle(idx1, price1, idx2, price2)

    # VALIDATE ANGLE (5° to 70°)
    if angle < 5 or angle > 70:
        print(f"  [{point_type.upper()}] Angle {angle:.1f}° out of range (5-70°) - REJECTED")
        return None

    # Direction
    direction = "BULLISH" if slope > 0 else "BEARISH"

    return {
        'idx1': int(idx1),
        'idx2': int(idx2),
        'price1': price1,
        'price2': price2,
        'slope': slope,
        'intercept': intercept,
        'angle': angle,
        'direction': direction,
        'type': 'resistance' if point_type == 'high' else 'support'
    }


def draw_chart_with_trendline(df, symbol='EURUSD', timeframe='MN1'):
    """
    Draw chart with ONE relevant trendline based on trend direction
    """
    print(f"\n{'='*70}")
    print(f"ANALYZING: {symbol} {timeframe}")
    print(f"Bars: {len(df)} | Period: {df['time'].iloc[0].strftime('%Y-%m-%d')} to {df['time'].iloc[-1].strftime('%Y-%m-%d')}")
    print(f"{'='*70}\n")

    # Detect current trend direction
    trend = detect_trend_direction(df, lookback=20)
    print(f"DETECTED TREND: {trend}")
    print(f"Current Price: {df['close'].iloc[-1]:.5f}\n")

    # Find swing points
    swing_highs, swing_lows = find_major_swing_points(df, order=5)

    print(f"Found {len(swing_highs)} swing highs")
    print(f"Found {len(swing_lows)} swing lows\n")

    # Based on trend, find ONLY the relevant trendline
    if trend == 'UPTREND':
        print("Drawing SUPPORT trendline (market in uptrend)...")
        active_line = find_recent_trendline(df, swing_lows, 'low', lookback=60)
        line_color = '#2979FF'
        line_label = 'Support'
    else:  # DOWNTREND
        print("Drawing RESISTANCE trendline (market in downtrend)...")
        active_line = find_recent_trendline(df, swing_highs, 'high', lookback=60)
        line_color = '#D32F2F'
        line_label = 'Resistance'

    if active_line is None:
        print("ERROR: Could not find valid trendline!")
        return None

    # Create chart
    fig, ax = plt.subplots(figsize=(24, 13))

    # Plot candlesticks
    for idx, row in df.iterrows():
        color = '#00C853' if row['close'] >= row['open'] else '#FF1744'

        # Wick
        ax.plot([idx, idx], [row['low'], row['high']],
                color=color, linewidth=1.2, alpha=0.9)

        # Body
        body_height = abs(row['close'] - row['open'])
        body_bottom = min(row['open'], row['close'])
        rect = Rectangle((idx - 0.4, body_bottom), 0.8, body_height,
                         facecolor=color, edgecolor=color, alpha=0.95)
        ax.add_patch(rect)

    # Draw the active trendline
    print(f"\n{line_label.upper()} TRENDLINE")
    print("-" * 70)

    idx1 = active_line['idx1']
    idx2 = active_line['idx2']
    price1 = active_line['price1']
    price2 = active_line['price2']
    slope = active_line['slope']
    intercept = active_line['intercept']
    angle = active_line['angle']
    direction = active_line['direction']

    # Extend line to current bar
    x_end = len(df) - 1
    y_start = slope * idx1 + intercept
    y_end = slope * x_end + intercept

    # Draw trendline
    ax.plot([idx1, x_end], [y_start, y_end],
           color=line_color, linestyle='--', linewidth=4,
           alpha=0.85, label=f'{line_label} Trendline ({direction})', zorder=10)

    # Mark swing points
    marker = '^' if trend == 'UPTREND' else 'v'
    ax.scatter([idx1, idx2], [price1, price2],
              color=line_color, s=300, zorder=15, marker=marker,
              edgecolors='white', linewidths=3)

    # Annotate
    mid_x = (idx1 + x_end) // 2
    mid_y = slope * mid_x + intercept
    y_offset = -0.02 if trend == 'UPTREND' else 0.02

    ax.annotate(f'{line_label.upper()}\nAngle: {angle:.1f}°\n{direction}\n{trend}',
               xy=(mid_x, mid_y), xytext=(mid_x, mid_y + y_offset),
               fontsize=12, fontweight='bold', color=line_color,
               bbox=dict(boxstyle='round,pad=0.8', facecolor='white',
                        edgecolor=line_color, linewidth=2, alpha=0.95),
               ha='center')

    print(f"Point 1: Bar {idx1} ({df['time'].iloc[idx1].strftime('%Y-%m')}) @ {price1:.5f}")
    print(f"Point 2: Bar {idx2} ({df['time'].iloc[idx2].strftime('%Y-%m')}) @ {price2:.5f}")
    print(f"Slope: {slope:.8f}")
    print(f"Angle: {angle:.2f}°")
    print(f"Direction: {direction}")
    print(f"Trend: {trend}\n")

    # Current price line
    current_price = df['close'].iloc[-1]
    ax.axhline(y=current_price, color='#FFC107', linestyle='-',
              linewidth=3, alpha=0.9, label=f'Current Price: {current_price:.5f}', zorder=5)

    # Highlight latest candle
    last_idx = len(df) - 1
    last_row = df.iloc[-1]
    color = '#00C853' if last_row['close'] >= last_row['open'] else '#FF1744'
    ax.scatter([last_idx], [current_price], color=color, s=400,
              zorder=20, edgecolors='yellow', linewidths=4, marker='o')

    # Styling
    ax.set_xlabel('Bar Index', fontsize=15, fontweight='bold')
    ax.set_ylabel('Price', fontsize=15, fontweight='bold')
    ax.set_title(f'{symbol} {timeframe} - Smart Trendline Detection (V2)\nTrend: {trend}',
                fontsize=20, fontweight='bold', pad=25)
    ax.legend(loc='upper left', fontsize=13, framealpha=0.98,
             edgecolor='black', fancybox=True, shadow=True)
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.7)
    ax.set_facecolor('#FAFAFA')

    plt.tight_layout()
    return fig


if __name__ == "__main__":
    connector = MT5Connector()

    if connector.connect():
        # Fetch MONTHLY data
        # Test with different symbols
        symbol_name = 'EURUSD'
        print(f"Fetching {symbol_name}...")
        df = connector.get_ohlc_data(symbol_name, TIMEFRAMES['MN1'], 120)

        if df is not None:
            # Draw chart
            fig = draw_chart_with_trendline(df, symbol_name, 'MN1')

            if fig is not None:
                # Save
                filename = f'{symbol_name.lower()}_trendline_v2.png'
                fig.savefig(filename, dpi=150, bbox_inches='tight')

                print(f"{'='*70}")
                print(f"CHART SAVED: {filename}")
                print(f"{'='*70}")

        connector.disconnect()
