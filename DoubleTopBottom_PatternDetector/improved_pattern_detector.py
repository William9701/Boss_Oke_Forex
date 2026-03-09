import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.signal import argrelextrema

# Initialize MT5
if not mt5.initialize():
    print("MT5 initialization failed")
    exit()

# Parameters
SYMBOL = "GBPUSD"
LOOKBACK_BARS = 240
SWING_ORDER = 5  # Number of bars on each side to identify a swing point

# Double Top/Bottom criteria
HORIZONTAL_THRESHOLD = 3.5  # Max % difference for peaks to be considered horizontal
MAX_SLOPE_ANGLE = 3.2  # Maximum slope angle in degrees (angle check - FINAL)
MIN_VALLEY_DROP = 5.0  # Minimum % drop between the two peaks
MIN_BARS_APART = 3  # Minimum bars between two peaks
MAX_BARS_APART = 50  # Maximum bars between two peaks

print(f"=== IMPROVED Double Top/Bottom Detection on {SYMBOL} ===\n")
print(f"Using REAL swing point detection (scipy)")
print(f"Horizontal threshold: {HORIZONTAL_THRESHOLD}%")
print(f"Max slope angle: {MAX_SLOPE_ANGLE} degrees")
print(f"Min valley drop: {MIN_VALLEY_DROP}%")
print(f"Swing order: {SWING_ORDER}\n")

# Helper function to calculate slope angle
def calculate_slope_angle(price1, price2, bar_distance):
    """Calculate the angle of the line connecting two price points"""
    if bar_distance == 0:
        return 0.0

    # Calculate price difference as percentage
    avg_price = (price1 + price2) / 2.0
    price_diff_percent = abs(price2 - price1) / avg_price * 100.0

    # Calculate angle in degrees
    # tan(angle) = rise / run = price_diff_percent / bar_distance
    angle_radians = np.arctan(price_diff_percent / bar_distance)
    angle_degrees = np.degrees(angle_radians)

    return angle_degrees

# Get monthly data
rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_MN1, 0, LOOKBACK_BARS)
if rates is None:
    print("Failed to get data")
    mt5.shutdown()
    exit()

# Create DataFrame
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

print(f"Loaded {len(df)} monthly bars\n")

# Extract price arrays
highs = df['high'].values
lows = df['low'].values
times = df['time'].values

# Find swing highs and swing lows using scipy
swing_high_indices = argrelextrema(highs, np.greater, order=SWING_ORDER)[0]
swing_low_indices = argrelextrema(lows, np.less, order=SWING_ORDER)[0]

print(f"Found {len(swing_high_indices)} swing highs")
print(f"Found {len(swing_low_indices)} swing lows\n")

# Storage for detected patterns
double_tops = []
double_bottoms = []

# Detect Double Tops
print("=== DETECTING DOUBLE TOPS ===")
for i in range(len(swing_high_indices)):
    for j in range(i + 1, len(swing_high_indices)):
        first_idx = swing_high_indices[i]
        second_idx = swing_high_indices[j]

        # Check bar distance
        bar_distance = second_idx - first_idx
        if bar_distance < MIN_BARS_APART or bar_distance > MAX_BARS_APART:
            continue

        first_high = highs[first_idx]
        second_high = highs[second_idx]

        # Check if they're horizontally aligned (similar price level)
        avg_high = (first_high + second_high) / 2.0
        height_diff = abs(first_high - second_high) / avg_high * 100.0

        if height_diff > HORIZONTAL_THRESHOLD:
            continue

        # NEW: Check slope angle
        slope_angle = calculate_slope_angle(first_high, second_high, bar_distance)
        if slope_angle > MAX_SLOPE_ANGLE:
            continue  # Too slanted

        # Check for valley between them
        valley_slice = lows[first_idx:second_idx+1]
        valley_low = np.min(valley_slice)
        valley_drop = (avg_high - valley_low) / avg_high * 100.0

        if valley_drop < MIN_VALLEY_DROP:
            continue

        # Valid Double Top found!
        first_time = pd.Timestamp(times[first_idx])
        second_time = pd.Timestamp(times[second_idx])
        print(f"Double Top: {first_time.strftime('%Y-%m')} ({first_high:.5f}) -> {second_time.strftime('%Y-%m')} ({second_high:.5f})")
        print(f"  Height diff: {height_diff:.2f}%, Angle: {slope_angle:.2f}°, Valley drop: {valley_drop:.2f}%, Bars: {bar_distance}")

        double_tops.append({
            'first_idx': first_idx,
            'second_idx': second_idx,
            'first_price': first_high,
            'second_price': second_high,
            'first_time': times[first_idx],
            'second_time': times[second_idx],
            'height_diff': height_diff,
            'valley_drop': valley_drop
        })

# Detect Double Bottoms
print("\n=== DETECTING DOUBLE BOTTOMS ===")
for i in range(len(swing_low_indices)):
    for j in range(i + 1, len(swing_low_indices)):
        first_idx = swing_low_indices[i]
        second_idx = swing_low_indices[j]

        # Check bar distance
        bar_distance = second_idx - first_idx
        if bar_distance < MIN_BARS_APART or bar_distance > MAX_BARS_APART:
            continue

        first_low = lows[first_idx]
        second_low = lows[second_idx]

        # Check if they're horizontally aligned (similar price level)
        avg_low = (first_low + second_low) / 2.0
        height_diff = abs(first_low - second_low) / avg_low * 100.0

        if height_diff > HORIZONTAL_THRESHOLD:
            continue

        # NEW: Check slope angle
        slope_angle = calculate_slope_angle(first_low, second_low, bar_distance)
        if slope_angle > MAX_SLOPE_ANGLE:
            continue  # Too slanted

        # Check for peak between them
        peak_slice = highs[first_idx:second_idx+1]
        peak_high = np.max(peak_slice)
        peak_rise = (peak_high - avg_low) / avg_low * 100.0

        if peak_rise < MIN_VALLEY_DROP:
            continue

        # Valid Double Bottom found!
        first_time = pd.Timestamp(times[first_idx])
        second_time = pd.Timestamp(times[second_idx])
        print(f"Double Bottom: {first_time.strftime('%Y-%m')} ({first_low:.5f}) -> {second_time.strftime('%Y-%m')} ({second_low:.5f})")
        print(f"  Height diff: {height_diff:.2f}%, Angle: {slope_angle:.2f}°, Peak rise: {peak_rise:.2f}%, Bars: {bar_distance}")

        double_bottoms.append({
            'first_idx': first_idx,
            'second_idx': second_idx,
            'first_price': first_low,
            'second_price': second_low,
            'first_time': times[first_idx],
            'second_time': times[second_idx],
            'height_diff': height_diff,
            'peak_rise': peak_rise
        })

print(f"\n=== RESULTS ===")
print(f"Double Tops detected: {len(double_tops)}")
print(f"Double Bottoms detected: {len(double_bottoms)}")

# Create visualization
fig, ax = plt.subplots(figsize=(22, 11))

# Plot candlesticks
for idx, row in df.iterrows():
    color = 'green' if row['close'] >= row['open'] else 'red'
    ax.plot([row['time'], row['time']], [row['low'], row['high']],
            color=color, linewidth=1, alpha=0.7)
    ax.plot([row['time'], row['time']], [row['open'], row['close']],
            color=color, linewidth=3, alpha=0.7)

# Mark all swing highs (light markers for reference)
for idx in swing_high_indices:
    ax.scatter(times[idx], highs[idx], color='pink', s=50, alpha=0.3, zorder=3)

# Mark all swing lows (light markers for reference)
for idx in swing_low_indices:
    ax.scatter(times[idx], lows[idx], color='lightblue', s=50, alpha=0.3, zorder=3)

# Draw Double Tops with connecting horizontal line
for dt in double_tops:
    # Draw horizontal line connecting the two tops (like your red line!)
    ax.plot([dt['first_time'], dt['second_time']],
           [dt['first_price'], dt['second_price']],
           'r-', linewidth=3, alpha=0.8, zorder=6)

    # Mark the two peaks
    ax.scatter(dt['first_time'], dt['first_price'],
              color='red', s=400, marker='v', zorder=7,
              edgecolors='darkred', linewidths=3)
    ax.scatter(dt['second_time'], dt['second_price'],
              color='red', s=400, marker='v', zorder=7,
              edgecolors='darkred', linewidths=3)

    # Label
    mid_time = dt['first_time'] + (dt['second_time'] - dt['first_time']) / 2
    mid_price = (dt['first_price'] + dt['second_price']) / 2
    ax.text(mid_time, mid_price, 'DOUBLE TOP', fontsize=10, ha='center',
           va='bottom', color='white', fontweight='bold',
           bbox=dict(boxstyle='round', facecolor='red', alpha=0.9))

# Draw Double Bottoms with connecting horizontal line
for db in double_bottoms:
    # Draw horizontal line connecting the two bottoms
    ax.plot([db['first_time'], db['second_time']],
           [db['first_price'], db['second_price']],
           'g-', linewidth=3, alpha=0.8, zorder=6)

    # Mark the two bottoms
    ax.scatter(db['first_time'], db['first_price'],
              color='lime', s=400, marker='^', zorder=7,
              edgecolors='darkgreen', linewidths=3)
    ax.scatter(db['second_time'], db['second_price'],
              color='lime', s=400, marker='^', zorder=7,
              edgecolors='darkgreen', linewidths=3)

    # Label
    mid_time = db['first_time'] + (db['second_time'] - db['first_time']) / 2
    mid_price = (db['first_price'] + db['second_price']) / 2
    ax.text(mid_time, mid_price, 'DOUBLE BOTTOM', fontsize=10, ha='center',
           va='top', color='white', fontweight='bold',
           bbox=dict(boxstyle='round', facecolor='green', alpha=0.9))

ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=12))
plt.xticks(rotation=45)
plt.title(f'{SYMBOL} - IMPROVED Pattern Detection (Swing Points + Horizontal Line Check)\n' +
         f'Double Tops: {len(double_tops)}, Double Bottoms: {len(double_bottoms)} | ' +
         f'Horizontal: ≤{HORIZONTAL_THRESHOLD}%, Valley: ≥{MIN_VALLEY_DROP}%',
         fontsize=14, fontweight='bold')
plt.xlabel('Date', fontsize=12)
plt.ylabel('Price', fontsize=12)
plt.grid(True, alpha=0.3)
plt.tight_layout()

output_path = r'C:\Users\ASUS\Desktop\Boss_Oke_Forex\improved_pattern_detection.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\nChart saved to: {output_path}")

mt5.shutdown()
plt.close()
