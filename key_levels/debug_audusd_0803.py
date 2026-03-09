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

print("=== ANALYZING 0.80345 LEVEL ON AUDUSD ===\n")

# Test zones around 0.803-0.804
test_zones = [
    (0.800, 0.810, "1% zone around 0.805"),
    (0.798, 0.808, "1.25% zone"),
    (0.795, 0.810, "1.88% zone"),
    (0.790, 0.810, "2.5% zone"),
    (0.803, 0.813, "Starting at your line (1.2%)"),
]

for zone_bottom, zone_top, description in test_zones:
    zone_mid = (zone_bottom + zone_top) / 2
    height_pct = (zone_top - zone_bottom) / zone_bottom * 100

    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Zone: {zone_bottom:.3f} - {zone_top:.3f} (Mid: {zone_mid:.3f}, {height_pct:.2f}%)")
    print(f"{'='*60}")

    touches = 0
    reversals = 0
    recent_touches = 0
    touch_info = []

    i = 0
    while i < len(df) - 1:
        bar_high = df['high'].iloc[i]
        bar_low = df['low'].iloc[i]
        bar_close = df['close'].iloc[i]
        bar_time = df['time'].iloc[i]

        # Did price touch zone?
        if bar_low <= zone_top and bar_high >= zone_bottom:
            touches += 1

            if i < 50:
                recent_touches += 1

            touch_info.append({
                'date': bar_time.strftime('%Y-%m'),
                'high': bar_high,
                'low': bar_low,
                'close': bar_close
            })

            # Check for reversal
            reversed = False
            if i < len(df) - 3:
                prev_close = df['close'].iloc[i - 1] if i > 0 else bar_close

                if prev_close > zone_mid or bar_close > zone_mid:
                    # Check bounce DOWN
                    for j in range(1, 4):
                        if df['close'].iloc[i + j] < zone_bottom:
                            reversals += 1
                            reversed = True
                            break
                else:
                    # Check bounce UP
                    for j in range(1, 4):
                        if df['close'].iloc[i + j] > zone_top:
                            reversals += 1
                            reversed = True
                            break

            if len(touch_info) <= 15:  # Show first 15
                print(f"  Touch {touches}: {bar_time.strftime('%Y-%m')} H:{bar_high:.5f} L:{bar_low:.5f} {'[REV]' if reversed else ''}")

            i += 3
        else:
            i += 1

    reversal_rate = (reversals / touches * 100) if touches > 0 else 0

    print(f"\nTouches: {touches} (Recent: {recent_touches})")
    print(f"Reversals: {reversals} ({reversal_rate:.1f}%)")
    print(f"Meets V4 criteria (5+ touches, 55%+ reversal)? {touches >= 5 and reversal_rate >= 55}")

    if touches >= 5 and reversal_rate >= 55:
        score = touches * 8 + reversals * 12 + reversal_rate / 5 + recent_touches * 15
        print(f"SCORE: {score:.0f}")

print("\n\n=== WHAT V4 DETECTED FOR LEVEL 3 (GREEN) ===")
print("Zone: 0.74681 - 0.76548 (29T, 58.6%)")
print("This is BELOW your 0.803 level")

print("\n\n=== CHECKING IF 0.803 ZONE EXISTS IN V4 CANDIDATES ===")
print("The 0.803 level falls in the range between:")
print("  Level 2 (Blue): 0.88433 - 0.92412")
print("  Level 3 (Green): 0.74681 - 0.76548")
print("\nSo V4 should have found it in that section of price range!")
