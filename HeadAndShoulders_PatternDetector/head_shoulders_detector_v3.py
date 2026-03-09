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

# Parameters - V3 FOR MAJOR STRUCTURAL PATTERNS
SYMBOL = "USDJPY"
LOOKBACK_BARS = 240  # 20 years
SWING_ORDER = 5

# V3: Looser criteria for major multi-year patterns
MIN_PROMINENCE_SHOULDERS = 8.0  # Shoulders should be prominent
MIN_PROMINENCE_HEAD = 10.0      # Head must be very prominent
MIN_HEAD_TO_SHOULDER_RATIO = 1.10  # V3: Head must be 10% more extreme than shoulders
MIN_BARS_BETWEEN_POINTS = 5     # Minimum bars between L-H-R
MAX_BARS_BETWEEN_POINTS = 150   # V3: Maximum bars for the full pattern (12+ years)
SHOULDER_SYMMETRY_TOLERANCE = 30.0  # V3: Shoulders can differ by up to 30%
NECKLINE_TOLERANCE = 15.0  # V3: Neckline points can vary by 15%

print(f"=== V3 Head & Shoulders Detection on {SYMBOL} (MAJOR PATTERNS) ===\n")
print(f"Looking for large multi-year structural patterns")
print(f"Min prominence: Shoulders {MIN_PROMINENCE_SHOULDERS}%, Head {MIN_PROMINENCE_HEAD}%\n")

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

# Helper function to calculate prominence
def calculate_prominence(prices, idx, is_high=True):
    lookback = 20  # Wider lookback for major patterns
    start_idx = max(0, idx - lookback)
    end_idx = min(len(prices) - 1, idx + lookback)

    center_price = prices[idx]

    if is_high:
        min_nearby = np.min(prices[start_idx:end_idx+1])
        prominence = (center_price - min_nearby) / center_price * 100.0
    else:
        max_nearby = np.max(prices[start_idx:end_idx+1])
        prominence = (max_nearby - center_price) / center_price * 100.0

    return prominence

# Find swing highs and swing lows
swing_high_indices = argrelextrema(highs, np.greater, order=SWING_ORDER)[0]
swing_low_indices = argrelextrema(lows, np.less, order=SWING_ORDER)[0]

print(f"Found {len(swing_high_indices)} swing highs and {len(swing_low_indices)} swing lows\n")

# Filter by prominence
prominent_highs = []
for idx in swing_high_indices:
    prominence = calculate_prominence(highs, idx, is_high=True)
    if prominence >= MIN_PROMINENCE_SHOULDERS:
        prominent_highs.append((idx, highs[idx], prominence))
        print(f"High at {pd.Timestamp(times[idx]).strftime('%Y-%m')}: {highs[idx]:.2f}, Prominence: {prominence:.2f}%")

prominent_lows = []
for idx in swing_low_indices:
    prominence = calculate_prominence(lows, idx, is_high=False)
    if prominence >= MIN_PROMINENCE_SHOULDERS:
        prominent_lows.append((idx, lows[idx], prominence))
        print(f"Low at {pd.Timestamp(times[idx]).strftime('%Y-%m')}: {lows[idx]:.2f}, Prominence: {prominence:.2f}%")

print(f"\nAfter prominence filter: {len(prominent_highs)} highs, {len(prominent_lows)} lows\n")

# Storage for detected patterns
bearish_hs_patterns = []
inverse_hs_patterns = []

# ============= DETECT INVERSE HEAD AND SHOULDERS (BULLISH) =============
print("=== DETECTING INVERSE HEAD & SHOULDERS (Bullish) ===")

# V3: Find ONLY the best pattern - most prominent head with best shoulder symmetry
best_inverse_pattern = None
best_score = 0

for i in range(len(prominent_lows)):
    for j in range(i + 1, len(prominent_lows)):
        for k in range(j + 1, len(prominent_lows)):
            ls_idx, ls_low, ls_prom = prominent_lows[i]
            h_idx, h_low, h_prom = prominent_lows[j]
            rs_idx, rs_low, rs_prom = prominent_lows[k]

            # Check bar spacing
            bars_ls_to_h = h_idx - ls_idx
            bars_h_to_rs = rs_idx - h_idx

            if bars_ls_to_h < MIN_BARS_BETWEEN_POINTS or bars_h_to_rs < MIN_BARS_BETWEEN_POINTS:
                continue

            if (rs_idx - ls_idx) > MAX_BARS_BETWEEN_POINTS:
                continue

            # Head must be significantly lower than both shoulders
            if h_low >= ls_low * (1 - (MIN_HEAD_TO_SHOULDER_RATIO - 1.0)):
                continue
            if h_low >= rs_low * (1 - (MIN_HEAD_TO_SHOULDER_RATIO - 1.0)):
                continue

            # Head must have high prominence
            if h_prom < MIN_PROMINENCE_HEAD:
                continue

            # Shoulders should be roughly at similar level
            shoulder_diff = abs(ls_low - rs_low) / ((ls_low + rs_low) / 2.0) * 100.0
            if shoulder_diff > SHOULDER_SYMMETRY_TOLERANCE:
                continue

            # V3 FIX: Neckline should be at approximately the shoulder level
            # Use the shoulder level itself as the neckline (horizontal resistance)
            peak1_high = ls_low
            peak1_idx = ls_idx
            peak2_high = rs_low
            peak2_idx = rs_idx

            # Neckline peaks should be roughly at similar level
            neckline_diff = abs(peak1_high - peak2_high) / ((peak1_high + peak2_high) / 2.0) * 100.0
            if neckline_diff > NECKLINE_TOLERANCE:
                continue

            # V3 FIX: Score this pattern - prefer neckline CLOSE to shoulder levels
            # The neckline should be at approximately the same level as the shoulders
            avg_shoulder = (ls_low + rs_low) / 2.0
            avg_neckline = (peak1_high + peak2_high) / 2.0
            neckline_to_shoulder_diff = abs(avg_neckline - avg_shoulder) / avg_shoulder * 100.0

            # Higher score = better pattern
            # V3: Prefer the LOWEST head point (most extreme) and good prominence
            # Calculate how much lower the head is compared to average shoulder
            head_depth = (avg_shoulder - h_low) / avg_shoulder * 100.0

            # Higher score = better pattern (deeper head + good prominence)
            score = (head_depth * 5.0) + (h_prom * 3.0) - shoulder_diff - neckline_diff


            if score > best_score:
                best_score = score
                best_inverse_pattern = {
                    'ls_idx': ls_idx, 'ls_price': ls_low,
                    'h_idx': h_idx, 'h_price': h_low,
                    'rs_idx': rs_idx, 'rs_price': rs_low,
                    'peak1_idx': peak1_idx, 'peak1_price': peak1_high,
                    'peak2_idx': peak2_idx, 'peak2_price': peak2_high,
                    'h_prom': h_prom,
                    'shoulder_diff': shoulder_diff,
                    'neckline_diff': neckline_diff,
                    'score': score
                }

# Add only the BEST inverse pattern if found
if best_inverse_pattern:
    inverse_hs_patterns.append(best_inverse_pattern)
    ls_time = pd.Timestamp(times[best_inverse_pattern['ls_idx']])
    h_time = pd.Timestamp(times[best_inverse_pattern['h_idx']])
    rs_time = pd.Timestamp(times[best_inverse_pattern['rs_idx']])

    print(f"\nBEST INVERSE H&S FOUND (Score: {best_inverse_pattern['score']:.2f}):")
    print(f"  Left Shoulder:  {ls_time.strftime('%Y-%m')} at {best_inverse_pattern['ls_price']:.2f}")
    print(f"  Head:           {h_time.strftime('%Y-%m')} at {best_inverse_pattern['h_price']:.2f} (prominence: {best_inverse_pattern['h_prom']:.2f}%)")
    print(f"  Right Shoulder: {rs_time.strftime('%Y-%m')} at {best_inverse_pattern['rs_price']:.2f}")
    print(f"  Shoulder diff: {best_inverse_pattern['shoulder_diff']:.2f}%")
    print(f"  Neckline: Peak1 at {pd.Timestamp(times[best_inverse_pattern['peak1_idx']]).strftime('%Y-%m')} ({best_inverse_pattern['peak1_price']:.2f}), Peak2 at {pd.Timestamp(times[best_inverse_pattern['peak2_idx']]).strftime('%Y-%m')} ({best_inverse_pattern['peak2_price']:.2f})")
    print(f"  Neckline diff: {best_inverse_pattern['neckline_diff']:.2f}%")

# ============= DETECT BEARISH HEAD AND SHOULDERS =============
print("\n=== DETECTING BEARISH HEAD & SHOULDERS ===")

# V3: Find ONLY the best pattern - most prominent head with best shoulder symmetry
best_bearish_pattern = None
best_score = 0

for i in range(len(prominent_highs)):
    for j in range(i + 1, len(prominent_highs)):
        for k in range(j + 1, len(prominent_highs)):
            ls_idx, ls_high, ls_prom = prominent_highs[i]
            h_idx, h_high, h_prom = prominent_highs[j]
            rs_idx, rs_high, rs_prom = prominent_highs[k]

            # Check bar spacing
            bars_ls_to_h = h_idx - ls_idx
            bars_h_to_rs = rs_idx - h_idx

            if bars_ls_to_h < MIN_BARS_BETWEEN_POINTS or bars_h_to_rs < MIN_BARS_BETWEEN_POINTS:
                continue

            if (rs_idx - ls_idx) > MAX_BARS_BETWEEN_POINTS:
                continue

            # Head must be significantly higher than both shoulders
            if h_high <= ls_high * MIN_HEAD_TO_SHOULDER_RATIO:
                continue
            if h_high <= rs_high * MIN_HEAD_TO_SHOULDER_RATIO:
                continue

            # Head must have high prominence
            if h_prom < MIN_PROMINENCE_HEAD:
                continue

            # Shoulders should be roughly at similar level
            shoulder_diff = abs(ls_high - rs_high) / ((ls_high + rs_high) / 2.0) * 100.0
            if shoulder_diff > SHOULDER_SYMMETRY_TOLERANCE:
                continue

            # Find neckline valleys (support between L-H and H-R)
            valley1_idx = ls_idx
            valley1_low = lows[ls_idx]
            for idx in range(ls_idx, h_idx + 1):
                if lows[idx] < valley1_low:
                    valley1_low = lows[idx]
                    valley1_idx = idx

            valley2_idx = h_idx
            valley2_low = lows[h_idx]
            for idx in range(h_idx, rs_idx + 1):
                if lows[idx] < valley2_low:
                    valley2_low = lows[idx]
                    valley2_idx = idx

            # Neckline valleys should be roughly at similar level
            neckline_diff = abs(valley1_low - valley2_low) / ((valley1_low + valley2_low) / 2.0) * 100.0
            if neckline_diff > NECKLINE_TOLERANCE:
                continue

            # V3: Score this pattern - prefer high head prominence and low shoulder difference
            score = h_prom * 10.0 - shoulder_diff - neckline_diff

            if score > best_score:
                best_score = score
                best_bearish_pattern = {
                    'ls_idx': ls_idx, 'ls_price': ls_high,
                    'h_idx': h_idx, 'h_price': h_high,
                    'rs_idx': rs_idx, 'rs_price': rs_high,
                    'valley1_idx': valley1_idx, 'valley1_price': valley1_low,
                    'valley2_idx': valley2_idx, 'valley2_price': valley2_low,
                    'h_prom': h_prom,
                    'shoulder_diff': shoulder_diff,
                    'neckline_diff': neckline_diff,
                    'score': score
                }

# Add only the BEST bearish pattern if found
if best_bearish_pattern:
    bearish_hs_patterns.append(best_bearish_pattern)
    ls_time = pd.Timestamp(times[best_bearish_pattern['ls_idx']])
    h_time = pd.Timestamp(times[best_bearish_pattern['h_idx']])
    rs_time = pd.Timestamp(times[best_bearish_pattern['rs_idx']])

    print(f"\nBEST BEARISH H&S FOUND (Score: {best_bearish_pattern['score']:.2f}):")
    print(f"  Left Shoulder:  {ls_time.strftime('%Y-%m')} at {best_bearish_pattern['ls_price']:.2f}")
    print(f"  Head:           {h_time.strftime('%Y-%m')} at {best_bearish_pattern['h_price']:.2f} (prominence: {best_bearish_pattern['h_prom']:.2f}%)")
    print(f"  Right Shoulder: {rs_time.strftime('%Y-%m')} at {best_bearish_pattern['rs_price']:.2f}")
    print(f"  Shoulder diff: {best_bearish_pattern['shoulder_diff']:.2f}%")
    print(f"  Neckline: Valley1 at {pd.Timestamp(times[best_bearish_pattern['valley1_idx']]).strftime('%Y-%m')} ({best_bearish_pattern['valley1_price']:.2f}), Valley2 at {pd.Timestamp(times[best_bearish_pattern['valley2_idx']]).strftime('%Y-%m')} ({best_bearish_pattern['valley2_price']:.2f})")
    print(f"  Neckline diff: {best_bearish_pattern['neckline_diff']:.2f}%")

print(f"\n=== RESULTS ===")
print(f"Bearish H&S detected: {len(bearish_hs_patterns)}")
print(f"Inverse H&S detected: {len(inverse_hs_patterns)}")

# Create visualization
fig, ax = plt.subplots(figsize=(22, 11))

# Plot candlesticks
for idx, row in df.iterrows():
    color = 'green' if row['close'] >= row['open'] else 'red'
    ax.plot([row['time'], row['time']], [row['low'], row['high']],
            color=color, linewidth=1, alpha=0.7)
    ax.plot([row['time'], row['time']], [row['open'], row['close']],
            color=color, linewidth=3, alpha=0.7)

# Mark all prominent swing points
for idx, price, prom in prominent_highs:
    ax.scatter(times[idx], price, color='pink', s=100, alpha=0.5, zorder=3,
               edgecolors='red', linewidths=1.5)

for idx, price, prom in prominent_lows:
    ax.scatter(times[idx], price, color='lightblue', s=100, alpha=0.5, zorder=3,
               edgecolors='blue', linewidths=1.5)

# Draw Inverse H&S patterns
for pattern in inverse_hs_patterns:
    # Draw structure lines (L->H->R)
    ax.plot([times[pattern['ls_idx']], times[pattern['h_idx']]],
           [pattern['ls_price'], pattern['h_price']],
           'g-', linewidth=3, alpha=0.8, zorder=6)
    ax.plot([times[pattern['h_idx']], times[pattern['rs_idx']]],
           [pattern['h_price'], pattern['rs_price']],
           'g-', linewidth=3, alpha=0.8, zorder=6)

    # V3: NO NECKLINE - just the 3 points

    # Mark key points
    ax.scatter([times[pattern['ls_idx']], times[pattern['h_idx']], times[pattern['rs_idx']]],
              [pattern['ls_price'], pattern['h_price'], pattern['rs_price']],
              color='lime', s=400, marker='^', zorder=8, edgecolors='darkgreen', linewidths=3)

    # Label
    mid_time = times[pattern['h_idx']]
    ax.text(mid_time, pattern['h_price'] - 10, 'INVERSE H&S', fontsize=12, ha='center',
           va='top', color='white', fontweight='bold',
           bbox=dict(boxstyle='round', facecolor='green', alpha=0.9))

# Draw Bearish H&S patterns
for pattern in bearish_hs_patterns:
    # Draw structure lines (L->H->R)
    ax.plot([times[pattern['ls_idx']], times[pattern['h_idx']]],
           [pattern['ls_price'], pattern['h_price']],
           'r-', linewidth=3, alpha=0.8, zorder=6)
    ax.plot([times[pattern['h_idx']], times[pattern['rs_idx']]],
           [pattern['h_price'], pattern['rs_price']],
           'r-', linewidth=3, alpha=0.8, zorder=6)

    # V3: NO NECKLINE - just the 3 points

    # Mark key points
    ax.scatter([times[pattern['ls_idx']], times[pattern['h_idx']], times[pattern['rs_idx']]],
              [pattern['ls_price'], pattern['h_price'], pattern['rs_price']],
              color='red', s=400, marker='v', zorder=8, edgecolors='darkred', linewidths=3)

    # Label
    mid_time = times[pattern['h_idx']]
    ax.text(mid_time, pattern['h_price'] + 10, 'BEARISH H&S', fontsize=12, ha='center',
           va='bottom', color='white', fontweight='bold',
           bbox=dict(boxstyle='round', facecolor='red', alpha=0.9))

ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=12))
plt.xticks(rotation=45)
plt.title(f'{SYMBOL} - V3 Head & Shoulders Detection (MAJOR STRUCTURAL PATTERNS)\n' +
         f'Bearish: {len(bearish_hs_patterns)}, Inverse: {len(inverse_hs_patterns)}',
         fontsize=14, fontweight='bold')
plt.xlabel('Date', fontsize=12)
plt.ylabel('Price', fontsize=12)
plt.grid(True, alpha=0.3)
plt.tight_layout()

output_path = r'C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\head_shoulders_v3_detection.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\nChart saved to: {output_path}")

mt5.shutdown()
plt.close()
