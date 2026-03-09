import pandas as pd
import MetaTrader5 as mt5

# Load AUDUSD data
if not mt5.initialize():
    print("Failed")
    exit()

rates = mt5.copy_rates_from_pos('AUDUSD', mt5.TIMEFRAME_MN1, 0, 300)
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
mt5.shutdown()

print("=== ANALYZING YOUR 0.88 LEVEL ON AUDUSD ===\n")

# Test different zone configurations around 0.88
test_zones = [
    (0.875, 0.885, "Tight 1% zone"),
    (0.880, 0.890, "Your level (1% zone)"),
    (0.885, 0.895, "Shifted up"),
    (0.87, 0.89, "2.3% zone"),
    (0.88, 0.92, "Wide zone (V4 detected)")
]

for zone_bottom, zone_top, description in test_zones:
    zone_mid = (zone_bottom + zone_top) / 2

    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Zone: {zone_bottom:.3f} - {zone_top:.3f} (Mid: {zone_mid:.3f})")
    print(f"{'='*60}")

    touches = 0
    reversals = 0
    touch_dates = []

    i = 0
    while i < len(df) - 1:
        bar_high = df['high'].iloc[i]
        bar_low = df['low'].iloc[i]
        bar_close = df['close'].iloc[i]
        bar_time = df['time'].iloc[i]

        # Did price touch zone?
        if bar_low <= zone_top and bar_high >= zone_bottom:
            touches += 1
            touch_dates.append(bar_time.strftime('%Y-%m'))

            # Check for reversal
            if i < len(df) - 3:
                prev_close = df['close'].iloc[i - 1] if i > 0 else bar_close

                if prev_close > zone_mid or bar_close > zone_mid:
                    # Check bounce DOWN
                    for j in range(1, 4):
                        if df['close'].iloc[i + j] < zone_bottom:
                            reversals += 1
                            break
                else:
                    # Check bounce UP
                    for j in range(1, 4):
                        if df['close'].iloc[i + j] > zone_top:
                            reversals += 1
                            break

            i += 3
        else:
            i += 1

    reversal_rate = (reversals / touches * 100) if touches > 0 else 0

    print(f"Touches: {touches}")
    print(f"Reversals: {reversals} ({reversal_rate:.1f}%)")
    print(f"Meets V4 criteria (5+ touches, 55%+ reversal)? {touches >= 5 and reversal_rate >= 55}")
    print(f"\nTouch dates: {', '.join(touch_dates[:15])}{'...' if len(touch_dates) > 15 else ''}")

print("\n\n=== FINDING ALL BARS NEAR 0.88 ===\n")

# Find all bars that touched near 0.88
near_088 = df[(df['low'] <= 0.90) & (df['high'] >= 0.86)].copy()

print(f"Found {len(near_088)} bars with price between 0.86-0.90:\n")
print(f"{'Date':<12} {'High':>8} {'Low':>8} {'Close':>8}")
print("=" * 40)

for i, row in near_088.head(20).iterrows():
    print(f"{row['time'].strftime('%Y-%m'):<12} {row['high']:>8.5f} {row['low']:>8.5f} {row['close']:>8.5f}")

if len(near_088) > 20:
    print(f"\n... and {len(near_088) - 20} more bars")
