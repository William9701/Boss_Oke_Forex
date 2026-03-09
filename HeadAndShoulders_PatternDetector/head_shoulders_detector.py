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
SWING_ORDER = 5

# Head & Shoulders criteria
SHOULDER_SIMILARITY = 3.5  # Max % difference between shoulders
MIN_HEAD_HEIGHT = 3.0      # Min % head must be above shoulders
MAX_NECKLINE_ANGLE = 15.0  # Max angle for neckline slope
MIN_BARS_APART = 3         # Min bars between peaks/troughs
MAX_BARS_APART = 50        # Max bars between peaks/troughs

print(f"=== Head & Shoulders Pattern Detection on {SYMBOL} ===\n")
print(f"Shoulder similarity: {SHOULDER_SIMILARITY}%")
print(f"Min head height: {MIN_HEAD_HEIGHT}%")
print(f"Max neckline angle: {MAX_NECKLINE_ANGLE}°\n")

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

# Find swing highs and swing lows
swing_high_indices = argrelextrema(highs, np.greater, order=SWING_ORDER)[0]
swing_low_indices = argrelextrema(lows, np.less, order=SWING_ORDER)[0]

print(f"Found {len(swing_high_indices)} swing highs")
print(f"Found {len(swing_low_indices)} swing lows\n")

# Storage for detected patterns
head_shoulders = []
inverse_head_shoulders = []

# Detect Head & Shoulders patterns
print("=== DETECTING HEAD & SHOULDERS ===")
for i in range(len(swing_high_indices) - 2):
    left_shoulder_idx = swing_high_indices[i]
    head_idx = swing_high_indices[i + 1]
    right_shoulder_idx = swing_high_indices[i + 2]

    # Check spacing
    if (head_idx - left_shoulder_idx < MIN_BARS_APART or
        right_shoulder_idx - head_idx < MIN_BARS_APART or
        right_shoulder_idx - left_shoulder_idx > MAX_BARS_APART):
        continue

    ls_high = highs[left_shoulder_idx]
    h_high = highs[head_idx]
    rs_high = highs[right_shoulder_idx]

    # Head must be highest
    if h_high <= ls_high or h_high <= rs_high:
        continue

    # Check head height above shoulders
    head_vs_ls = (h_high - ls_high) / ls_high * 100.0
    head_vs_rs = (h_high - rs_high) / rs_high * 100.0

    if head_vs_ls < MIN_HEAD_HEIGHT or head_vs_rs < MIN_HEAD_HEIGHT:
        continue

    # Check shoulder similarity
    shoulder_diff = abs(ls_high - rs_high) / ls_high * 100.0
    if shoulder_diff > SHOULDER_SIMILARITY:
        continue

    # Find neckline points (lows between shoulders and head)
    # Low between LS and H
    neckline_left_idx = None
    neckline_left_low = float('inf')
    for k in range(left_shoulder_idx, head_idx + 1):
        if lows[k] < neckline_left_low:
            neckline_left_low = lows[k]
            neckline_left_idx = k

    # Low between H and RS
    neckline_right_idx = None
    neckline_right_low = float('inf')
    for k in range(head_idx, right_shoulder_idx + 1):
        if lows[k] < neckline_right_low:
            neckline_right_low = lows[k]
            neckline_right_idx = k

    if neckline_left_idx is None or neckline_right_idx is None:
        continue

    # Check neckline angle
    bar_distance = neckline_right_idx - neckline_left_idx
    if bar_distance > 0:
        price_diff = abs(neckline_right_low - neckline_left_low) / neckline_left_low * 100.0
        angle = np.degrees(np.arctan(price_diff / bar_distance))
        if angle > MAX_NECKLINE_ANGLE:
            continue

    print(f"H&S: LS={pd.Timestamp(times[left_shoulder_idx]).strftime('%Y-%m')} ({ls_high:.5f}), " +
          f"H={pd.Timestamp(times[head_idx]).strftime('%Y-%m')} ({h_high:.5f}), " +
          f"RS={pd.Timestamp(times[right_shoulder_idx]).strftime('%Y-%m')} ({rs_high:.5f})")
    print(f"  Shoulder diff: {shoulder_diff:.2f}%, Head height: {min(head_vs_ls, head_vs_rs):.2f}%")

    head_shoulders.append({
        'ls_idx': left_shoulder_idx,
        'h_idx': head_idx,
        'rs_idx': right_shoulder_idx,
        'neckline_left_idx': neckline_left_idx,
        'neckline_right_idx': neckline_right_idx,
        'ls_price': ls_high,
        'h_price': h_high,
        'rs_price': rs_high,
        'neckline_left_price': neckline_left_low,
        'neckline_right_price': neckline_right_low
    })

# Detect Inverse Head & Shoulders patterns
print("\n=== DETECTING INVERSE HEAD & SHOULDERS ===")
for i in range(len(swing_low_indices) - 2):
    left_shoulder_idx = swing_low_indices[i]
    head_idx = swing_low_indices[i + 1]
    right_shoulder_idx = swing_low_indices[i + 2]

    # Check spacing
    if (head_idx - left_shoulder_idx < MIN_BARS_APART or
        right_shoulder_idx - head_idx < MIN_BARS_APART or
        right_shoulder_idx - left_shoulder_idx > MAX_BARS_APART):
        continue

    ls_low = lows[left_shoulder_idx]
    h_low = lows[head_idx]
    rs_low = lows[right_shoulder_idx]

    # Head must be lowest
    if h_low >= ls_low or h_low >= rs_low:
        continue

    # Check head depth below shoulders
    head_vs_ls = (ls_low - h_low) / ls_low * 100.0
    head_vs_rs = (rs_low - h_low) / rs_low * 100.0

    if head_vs_ls < MIN_HEAD_HEIGHT or head_vs_rs < MIN_HEAD_HEIGHT:
        continue

    # Check shoulder similarity
    shoulder_diff = abs(ls_low - rs_low) / ls_low * 100.0
    if shoulder_diff > SHOULDER_SIMILARITY:
        continue

    # Find neckline points (highs between shoulders and head)
    neckline_left_idx = None
    neckline_left_high = 0
    for k in range(left_shoulder_idx, head_idx + 1):
        if highs[k] > neckline_left_high:
            neckline_left_high = highs[k]
            neckline_left_idx = k

    neckline_right_idx = None
    neckline_right_high = 0
    for k in range(head_idx, right_shoulder_idx + 1):
        if highs[k] > neckline_right_high:
            neckline_right_high = highs[k]
            neckline_right_idx = k

    if neckline_left_idx is None or neckline_right_idx is None:
        continue

    # Check neckline angle
    bar_distance = neckline_right_idx - neckline_left_idx
    if bar_distance > 0:
        price_diff = abs(neckline_right_high - neckline_left_high) / neckline_left_high * 100.0
        angle = np.degrees(np.arctan(price_diff / bar_distance))
        if angle > MAX_NECKLINE_ANGLE:
            continue

    print(f"IHS: LS={pd.Timestamp(times[left_shoulder_idx]).strftime('%Y-%m')} ({ls_low:.5f}), " +
          f"H={pd.Timestamp(times[head_idx]).strftime('%Y-%m')} ({h_low:.5f}), " +
          f"RS={pd.Timestamp(times[right_shoulder_idx]).strftime('%Y-%m')} ({rs_low:.5f})")
    print(f"  Shoulder diff: {shoulder_diff:.2f}%, Head depth: {min(head_vs_ls, head_vs_rs):.2f}%")

    inverse_head_shoulders.append({
        'ls_idx': left_shoulder_idx,
        'h_idx': head_idx,
        'rs_idx': right_shoulder_idx,
        'neckline_left_idx': neckline_left_idx,
        'neckline_right_idx': neckline_right_idx,
        'ls_price': ls_low,
        'h_price': h_low,
        'rs_price': rs_low,
        'neckline_left_price': neckline_left_high,
        'neckline_right_price': neckline_right_high
    })

print(f"\n=== RESULTS ===")
print(f"Head & Shoulders: {len(head_shoulders)}")
print(f"Inverse Head & Shoulders: {len(inverse_head_shoulders)}")

# Create visualization
fig, ax = plt.subplots(figsize=(22, 11))

# Plot candlesticks
for idx, row in df.iterrows():
    color = 'green' if row['close'] >= row['open'] else 'red'
    ax.plot([row['time'], row['time']], [row['low'], row['high']],
            color=color, linewidth=1, alpha=0.7)
    ax.plot([row['time'], row['time']], [row['open'], row['close']],
            color=color, linewidth=3, alpha=0.7)

# Draw Head & Shoulders patterns
for hs in head_shoulders:
    # Draw structure lines (LS → H → RS)
    ax.plot([times[hs['ls_idx']], times[hs['h_idx']], times[hs['rs_idx']]],
           [hs['ls_price'], hs['h_price'], hs['rs_price']],
           'r-', linewidth=3, alpha=0.8, zorder=6)

    # Draw neckline
    ax.plot([times[hs['neckline_left_idx']], times[hs['neckline_right_idx']]],
           [hs['neckline_left_price'], hs['neckline_right_price']],
           'r--', linewidth=3, alpha=0.8, zorder=6)

    # Labels
    ax.text(times[hs['ls_idx']], hs['ls_price'], 'L', fontsize=12, ha='center',
           va='bottom', color='white', fontweight='bold',
           bbox=dict(boxstyle='circle', facecolor='red', alpha=0.9))
    ax.text(times[hs['h_idx']], hs['h_price'], 'H', fontsize=12, ha='center',
           va='bottom', color='white', fontweight='bold',
           bbox=dict(boxstyle='circle', facecolor='darkred', alpha=0.9))
    ax.text(times[hs['rs_idx']], hs['rs_price'], 'R', fontsize=12, ha='center',
           va='bottom', color='white', fontweight='bold',
           bbox=dict(boxstyle='circle', facecolor='red', alpha=0.9))

    # Pattern label
    mid_time = times[hs['h_idx']]
    mid_price = hs['h_price'] * 1.02
    ax.text(mid_time, mid_price, 'HEAD & SHOULDERS', fontsize=10, ha='center',
           va='bottom', color='red', fontweight='bold')

# Draw Inverse Head & Shoulders patterns
for ihs in inverse_head_shoulders:
    # Draw structure lines (LS → H → RS)
    ax.plot([times[ihs['ls_idx']], times[ihs['h_idx']], times[ihs['rs_idx']]],
           [ihs['ls_price'], ihs['h_price'], ihs['rs_price']],
           'g-', linewidth=3, alpha=0.8, zorder=6)

    # Draw neckline
    ax.plot([times[ihs['neckline_left_idx']], times[ihs['neckline_right_idx']]],
           [ihs['neckline_left_price'], ihs['neckline_right_price']],
           'g--', linewidth=3, alpha=0.8, zorder=6)

    # Labels
    ax.text(times[ihs['ls_idx']], ihs['ls_price'], 'L', fontsize=12, ha='center',
           va='top', color='white', fontweight='bold',
           bbox=dict(boxstyle='circle', facecolor='lime', alpha=0.9))
    ax.text(times[ihs['h_idx']], ihs['h_price'], 'H', fontsize=12, ha='center',
           va='top', color='white', fontweight='bold',
           bbox=dict(boxstyle='circle', facecolor='darkgreen', alpha=0.9))
    ax.text(times[ihs['rs_idx']], ihs['rs_price'], 'R', fontsize=12, ha='center',
           va='top', color='white', fontweight='bold',
           bbox=dict(boxstyle='circle', facecolor='lime', alpha=0.9))

    # Pattern label
    mid_time = times[ihs['h_idx']]
    mid_price = ihs['h_price'] * 0.98
    ax.text(mid_time, mid_price, 'INVERSE H&S', fontsize=10, ha='center',
           va='top', color='lime', fontweight='bold')

ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=12))
plt.xticks(rotation=45)
plt.title(f'{SYMBOL} - Head & Shoulders Pattern Detection\n' +
         f'H&S: {len(head_shoulders)}, IHS: {len(inverse_head_shoulders)}',
         fontsize=14, fontweight='bold')
plt.xlabel('Date', fontsize=12)
plt.ylabel('Price', fontsize=12)
plt.grid(True, alpha=0.3)
plt.tight_layout()

output_path = r'C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\head_shoulders_detection.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\nChart saved to: {output_path}")

mt5.shutdown()
plt.close()
