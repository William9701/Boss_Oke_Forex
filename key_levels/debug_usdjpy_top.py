import pandas as pd
import MetaTrader5 as mt5
import numpy as np

# Load USDJPY data
if not mt5.initialize():
    print("MT5 initialization failed")
    exit()

rates = mt5.copy_rates_from_pos('USDJPY', mt5.TIMEFRAME_MN1, 0, 300)
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

mt5.shutdown()

print("=== ANALYZING USDJPY TOP AREA (160-162) ===\n")

# Focus on the top area
top_zone_bottom = 160.0
top_zone_top = 162.0
zone_mid = 161.0

print(f"Testing zone: {top_zone_bottom} - {top_zone_top} (mid: {zone_mid})\n")

touches = []
for i in range(len(df)):
    bar_high = df['high'].iloc[i]
    bar_low = df['low'].iloc[i]
    bar_close = df['close'].iloc[i]
    bar_time = df['time'].iloc[i]

    # Did price touch this zone?
    if bar_low <= top_zone_top and bar_high >= top_zone_bottom:
        touches.append({
            'index': i,
            'time': bar_time,
            'high': bar_high,
            'low': bar_low,
            'close': bar_close
        })

print(f"Found {len(touches)} bars that touched 160-162 zone:\n")

for touch in touches:
    print(f"  {touch['time'].strftime('%Y-%m')} - High: {touch['high']:.2f}, Low: {touch['low']:.2f}, Close: {touch['close']:.2f}")

print("\n=== CHECKING SWING HIGHS NEAR TOP ===\n")

# Find swing highs in top 10% of range
price_max = df['high'].max()
price_min = df['low'].min()
top_10pct = price_max - ((price_max - price_min) * 0.10)

swing_highs = []
for i in range(5, len(df) - 5):
    bar_high = df['high'].iloc[i]

    # Is this a swing high? (higher than 5 bars on each side)
    is_swing_high = True
    for j in range(1, 6):
        if i - j >= 0 and bar_high <= df['high'].iloc[i - j]:
            is_swing_high = False
            break
        if i + j < len(df) and bar_high <= df['high'].iloc[i + j]:
            is_swing_high = False
            break

    if is_swing_high and bar_high >= top_10pct:
        swing_highs.append({
            'index': i,
            'time': df['time'].iloc[i],
            'high': bar_high
        })

print(f"Found {len(swing_highs)} swing highs in top 10% of range:\n")

for swing in swing_highs:
    print(f"  {swing['time'].strftime('%Y-%m')} - High: {swing['high']:.2f}")

print("\n=== ABSOLUTE HIGH ===")
max_idx = df['high'].idxmax()
print(f"  {df['time'].iloc[max_idx].strftime('%Y-%m')} - High: {df['high'].iloc[max_idx]:.2f}")
