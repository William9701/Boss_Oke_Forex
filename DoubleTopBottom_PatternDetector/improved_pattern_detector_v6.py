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

# Parameters - V6 WITH SEPARATE THRESHOLDS FOR TOPS AND BOTTOMS
SYMBOL = "USDJPY"
LOOKBACK_BARS = 240
SWING_ORDER = 5  # Number of bars on each side to identify a swing point

# V6: Different prominence for tops vs bottoms
MIN_PROMINENCE_TOPS = 7.0  # Keep 7% for tops
MIN_PROMINENCE_BOTTOMS = 5.0  # V6: Lower to 5% for bottoms (bottoms can be less prominent)

# V6: Separate horizontal thresholds for tops and bottoms
HORIZONTAL_THRESHOLD_TOPS = 3.5  # Tops should be tighter
HORIZONTAL_THRESHOLD_BOTTOMS = 12.0  # V6: Allow more variance for bottoms (up to 12%)

MAX_SLOPE_ANGLE_TOPS = 2.8  # Maximum slope angle for tops in degrees
MAX_SLOPE_ANGLE_BOTTOMS = 4.5  # V6: More lenient slope for bottoms (can slope more)
MIN_VALLEY_DROP = 5.0  # Minimum % drop between the two peaks
MIN_BARS_APART = 15  # V6: Minimum 15 bars apart (avoid very recent patterns)
MAX_BARS_APART = 120  # V6: INCREASED to 120 bars (10 years) to catch major long-term patterns
INTERSECTION_TOLERANCE = 2.0  # V6: Tolerance % for line intersection check

print(f"=== V6 Double Top/Bottom Detection on {SYMBOL} ===\n")
print(f"V6: SEPARATE THRESHOLDS FOR TOPS AND BOTTOMS")
print(f"  Tops:    Min prominence: {MIN_PROMINENCE_TOPS}%, Horizontal: {HORIZONTAL_THRESHOLD_TOPS}%, Angle: {MAX_SLOPE_ANGLE_TOPS}°")
print(f"  Bottoms: Min prominence: {MIN_PROMINENCE_BOTTOMS}%, Horizontal: {HORIZONTAL_THRESHOLD_BOTTOMS}%, Angle: {MAX_SLOPE_ANGLE_BOTTOMS}°")
print(f"Min valley drop: {MIN_VALLEY_DROP}%")
print(f"Swing order: {SWING_ORDER}\n")

# Helper function to calculate prominence
def calculate_prominence(prices, idx, is_high=True):
    """
    Calculate how prominent a swing point is compared to surrounding prices
    Prominence = how much the peak stands out from nearby prices
    """
    lookback = 15  # Look 15 bars on each side for prominence
    start_idx = max(0, idx - lookback)
    end_idx = min(len(prices) - 1, idx + lookback)

    center_price = prices[idx]

    if is_high:
        # For highs: find the lowest point nearby
        min_nearby = np.min(prices[start_idx:end_idx+1])
        # Prominence = how much higher than lowest nearby point
        prominence = (center_price - min_nearby) / center_price * 100.0
    else:
        # For lows: find the highest point nearby
        max_nearby = np.max(prices[start_idx:end_idx+1])
        # Prominence = how much lower than highest nearby point
        prominence = (max_nearby - center_price) / center_price * 100.0

    return prominence

# Helper function to calculate slope angle
def calculate_slope_angle(price1, price2, bar_distance):
    """Calculate the angle of the line connecting two price points"""
    if bar_distance == 0:
        return 0.0

    # Calculate price difference as percentage
    avg_price = (price1 + price2) / 2.0
    price_diff_percent = abs(price2 - price1) / avg_price * 100.0

    # Calculate angle in degrees
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

print(f"Found {len(swing_high_indices)} initial swing highs")
print(f"Found {len(swing_low_indices)} initial swing lows\n")

# V6: Filter swing points by prominence - DIFFERENT THRESHOLDS FOR TOPS AND BOTTOMS
print("=== V6: FILTERING BY PROMINENCE (SEPARATE THRESHOLDS) ===")
prominent_swing_highs = []
for idx in swing_high_indices:
    prominence = calculate_prominence(highs, idx, is_high=True)
    if prominence >= MIN_PROMINENCE_TOPS:
        prominent_swing_highs.append((idx, prominence))
        print(f"High at {pd.Timestamp(times[idx]).strftime('%Y-%m')}: {highs[idx]:.5f}, Prominence: {prominence:.2f}%")

# V6: Keep chronological order (sort by index, not prominence)
prominent_swing_highs.sort(key=lambda x: x[0])  # Sort by index (time order)

prominent_swing_lows = []
for idx in swing_low_indices:
    prominence = calculate_prominence(lows, idx, is_high=False)
    if prominence >= MIN_PROMINENCE_BOTTOMS:  # V6: Different threshold for bottoms
        prominent_swing_lows.append((idx, prominence))
        print(f"Low at {pd.Timestamp(times[idx]).strftime('%Y-%m')}: {lows[idx]:.5f}, Prominence: {prominence:.2f}%")

# V6: Keep chronological order (sort by index, not prominence)
prominent_swing_lows.sort(key=lambda x: x[0])  # Sort by index (time order)

swing_high_indices = np.array([x[0] for x in prominent_swing_highs])
swing_low_indices = np.array([x[0] for x in prominent_swing_lows])

print(f"\nAfter prominence filter:")
print(f"Prominent swing highs (>={MIN_PROMINENCE_TOPS}%): {len(swing_high_indices)}")
print(f"Prominent swing lows (>={MIN_PROMINENCE_BOTTOMS}%): {len(swing_low_indices)}\n")

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

        # DEBUG: Check for 2007-06 and 2015-06 pair specifically
        first_time = pd.Timestamp(times[first_idx])
        second_time = pd.Timestamp(times[second_idx])
        if (first_time.year == 2007 and second_time.year == 2015) or (first_time.year == 2015 and second_time.year == 2024):
            print(f"\nDEBUG: Checking {first_time.strftime('%Y-%m')} vs {second_time.strftime('%Y-%m')}")
            print(f"  Prices: {first_high:.5f} vs {second_high:.5f}")
            print(f"  Bar distance: {bar_distance}")

        # V6: Use TOPS threshold
        avg_high = (first_high + second_high) / 2.0
        height_diff = abs(first_high - second_high) / avg_high * 100.0

        if height_diff > HORIZONTAL_THRESHOLD_TOPS:
            if first_time.year == 2007 and second_time.year == 2015:
                print(f"  FAILED: Height diff {height_diff:.2f}% > {HORIZONTAL_THRESHOLD_TOPS}%")
            continue

        # Check slope angle
        slope_angle = calculate_slope_angle(first_high, second_high, bar_distance)
        if slope_angle > MAX_SLOPE_ANGLE_TOPS:
            if first_time.year == 2007 and second_time.year == 2015:
                print(f"  FAILED: Angle {slope_angle:.2f}° > {MAX_SLOPE_ANGLE}°")
            continue

        # V6: Check if line intersects chart (cuts through price action)
        tolerance_buffer = avg_high * INTERSECTION_TOLERANCE / 100.0
        line_cuts_through = False
        for k in range(first_idx + 1, second_idx):
            if highs[k] > (avg_high + tolerance_buffer):
                line_cuts_through = True
                if first_time.year == 2007 and second_time.year == 2015:
                    print(f"  FAILED: Line cuts through chart at index {k}")
                break

        if line_cuts_through:
            continue

        # Check for valley between them
        valley_slice = lows[first_idx:second_idx+1]
        valley_low = np.min(valley_slice)
        valley_drop = (avg_high - valley_low) / avg_high * 100.0

        if valley_drop < MIN_VALLEY_DROP:
            continue

        # V6: Check if market respected the level (price should NOT go higher immediately after)
        # Look at next 10-15 bars after second peak - price should not exceed second peak
        bars_to_check = min(15, len(highs) - second_idx - 1)
        if bars_to_check >= 10:
            max_high_after = max(highs[second_idx+1:second_idx+1+bars_to_check])
            if max_high_after > second_high:
                # Market went higher immediately after - NOT a valid top
                if first_time.year == 2009 and second_time.year == 2013:
                    print(f"  FAILED: Market went higher ({max_high_after:.5f}) after second peak ({second_high:.5f})")
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
        first_low = lows[first_idx]
        second_low = lows[second_idx]
        first_time = pd.Timestamp(times[first_idx])
        second_time = pd.Timestamp(times[second_idx])

        # DEBUG: Check specific pairs only
        is_debug = ((first_time.year <= 2012 and second_time.year >= 2018) or  # Major bottoms
                    (first_time.year == 2023 and second_time.year >= 2024))  # Recent bottoms

        if is_debug:
            print(f"\nDEBUG: Testing {first_time.strftime('%Y-%m')} ({first_low:.2f}) vs {second_time.strftime('%Y-%m')} ({second_low:.2f})")

        # Check bar distance
        bar_distance = second_idx - first_idx
        if bar_distance < MIN_BARS_APART or bar_distance > MAX_BARS_APART:
            if is_debug:
                print(f"  FAILED: Bar distance {bar_distance} (must be {MIN_BARS_APART}-{MAX_BARS_APART})")
            continue

        # V6: Use BOTTOMS threshold (more lenient)
        avg_low = (first_low + second_low) / 2.0
        height_diff = abs(first_low - second_low) / avg_low * 100.0

        if height_diff > HORIZONTAL_THRESHOLD_BOTTOMS:  # V6: 8% for bottoms
            if is_debug:
                print(f"  FAILED: Height diff {height_diff:.2f}% > {HORIZONTAL_THRESHOLD_BOTTOMS}%")
            continue

        # V6: Check slope angle (use BOTTOMS threshold)
        slope_angle = calculate_slope_angle(first_low, second_low, bar_distance)
        if slope_angle > MAX_SLOPE_ANGLE_BOTTOMS:
            if is_debug:
                print(f"  FAILED: Angle {slope_angle:.2f}° > {MAX_SLOPE_ANGLE_BOTTOMS}°")
            continue

        # V6: Check if line intersects chart (cuts through price action)
        tolerance_buffer = avg_low * INTERSECTION_TOLERANCE / 100.0
        line_cuts_through = False
        for k in range(first_idx + 1, second_idx):
            if lows[k] < (avg_low - tolerance_buffer):
                line_cuts_through = True
                break

        if line_cuts_through:
            if is_debug:
                print(f"  FAILED: Line cuts through chart")
            continue

        # Check for peak between them
        peak_slice = highs[first_idx:second_idx+1]
        peak_high = np.max(peak_slice)
        peak_rise = (peak_high - avg_low) / avg_low * 100.0

        if peak_rise < MIN_VALLEY_DROP:
            if is_debug:
                print(f"  FAILED: Peak rise {peak_rise:.2f}% < {MIN_VALLEY_DROP}%")
            continue

        # V6: Check if market respected the level (price should NOT go lower immediately after)
        # Look at next 10-15 bars after second bottom - price should not go below second bottom
        bars_to_check = min(15, len(lows) - second_idx - 1)
        if bars_to_check >= 10:
            min_low_after = min(lows[second_idx+1:second_idx+1+bars_to_check])
            if min_low_after < second_low:
                # Market went lower immediately after - NOT a valid bottom
                if is_debug:
                    print(f"  FAILED: Market went lower ({min_low_after:.5f}) after second bottom ({second_low:.5f})")
                continue

        # Valid Double Bottom found!
        print(f"VALID Double Bottom: {first_time.strftime('%Y-%m')} ({first_low:.5f}) -> {second_time.strftime('%Y-%m')} ({second_low:.5f})")
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

# Mark prominent swing highs
for idx in swing_high_indices:
    ax.scatter(times[idx], highs[idx], color='pink', s=100, alpha=0.5, zorder=3,
               edgecolors='red', linewidths=1.5, label='Prominent High' if idx == swing_high_indices[0] else '')

# Mark prominent swing lows
for idx in swing_low_indices:
    ax.scatter(times[idx], lows[idx], color='lightblue', s=100, alpha=0.5, zorder=3,
               edgecolors='blue', linewidths=1.5, label='Prominent Low' if idx == swing_low_indices[0] else '')

# Draw Double Tops with connecting horizontal line
for dt in double_tops:
    # Draw horizontal line connecting the two tops
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
plt.title(f'{SYMBOL} - V6 Pattern Detection (SEPARATE THRESHOLDS)\n' +
         f'Double Tops: {len(double_tops)}, Double Bottoms: {len(double_bottoms)} | ' +
         f'Tops: {MIN_PROMINENCE_TOPS}%/{HORIZONTAL_THRESHOLD_TOPS}%, Bottoms: {MIN_PROMINENCE_BOTTOMS}%/{HORIZONTAL_THRESHOLD_BOTTOMS}%',
         fontsize=14, fontweight='bold')
plt.xlabel('Date', fontsize=12)
plt.ylabel('Price', fontsize=12)
plt.grid(True, alpha=0.3)
plt.tight_layout()

output_path = r'C:\Users\ASUS\Desktop\Boss_Oke_Forex\DoubleTopBottom_PatternDetector\pattern_detection_v6.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\nChart saved to: {output_path}")

mt5.shutdown()
plt.close()
