import pandas as pd
import MetaTrader5 as mt5
import matplotlib.pyplot as plt

# Load USDJPY data
if not mt5.initialize():
    print("MT5 initialization failed")
    exit()

rates = mt5.copy_rates_from_pos('USDJPY', mt5.TIMEFRAME_MN1, 0, 50)
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

mt5.shutdown()

print("=== LAST 50 BARS OF USDJPY (Most Recent First) ===\n")
print(f"{'Date':<12} {'High':>10} {'Low':>10} {'Close':>10}")
print("=" * 45)

for i in range(min(20, len(df))):
    row = df.iloc[i]
    print(f"{row['time'].strftime('%Y-%m'):<12} {row['high']:>10.2f} {row['low']:>10.2f} {row['close']:>10.2f}")

print("\n=== IDENTIFYING SWING HIGHS IN TOP RANGE (155+) ===\n")

# Find bars with highs above 155
top_bars = df[df['high'] >= 155].copy()
print(f"Found {len(top_bars)} bars with highs >= 155:\n")

for i, row in top_bars.iterrows():
    print(f"{row['time'].strftime('%Y-%m')}: High={row['high']:.2f}, Low={row['low']:.2f}, Close={row['close']:.2f}")

# Count distinct swing highs manually
print("\n=== WHAT ZONE SHOULD CAPTURE THESE? ===")
if len(top_bars) > 0:
    max_high = top_bars['high'].max()
    min_high_in_range = top_bars['high'].min()

    print(f"\nHighest high: {max_high:.2f}")
    print(f"Lowest high in 155+ range: {min_high_in_range:.2f}")
    print(f"Range span: {max_high - min_high_in_range:.2f}")

    # Suggest zone
    zone_bottom = 155.0
    zone_top = 162.0

    print(f"\nSuggested zone: {zone_bottom} - {zone_top}")
    print(f"Zone height: {zone_top - zone_bottom:.2f} ({(zone_top-zone_bottom)/zone_bottom*100:.2f}%)")
