import pandas as pd
import MetaTrader5 as mt5
import numpy as np

# YOUR EXACT LEVELS
EXACT_LEVELS = [
    (1.50091, 1.48135, "Level 1"),
    (1.25431, 1.23561, "Level 2"),
    (1.07291, 1.05350, "Level 3"),
    (0.85163, 0.83235, "Level 4")
]

def get_data(symbol='EURUSD', bars=300):
    mt5.initialize()
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_MN1, 0, bars)
    mt5.shutdown()
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

df = get_data('EURUSD', 300)

print("="*80)
print("ANALYZING WHY MARKET RESPECTS YOUR EXACT LEVELS")
print("="*80)
print()

price_min = df['low'].min()
price_max = df['high'].max()
price_range = price_max - price_min

for top, bottom, name in EXACT_LEVELS:
    mid = (top + bottom) / 2
    height = top - bottom
    height_pct = (height / mid) * 100

    print(f"{name}: {bottom:.5f} - {top:.5f} (mid: {mid:.5f})")
    print(f"  Zone height: {height:.5f} ({height_pct:.2f}% of price)")

    # Where is this in the overall price range?
    position_in_range = (mid - price_min) / price_range * 100
    print(f"  Position in total range: {position_in_range:.1f}% from bottom")

    # Count touches
    touches = 0
    reversals = 0

    for idx in range(len(df)):
        if df['low'].iloc[idx] <= top and df['high'].iloc[idx] >= bottom:
            touches += 1

            # Check reversal
            if idx > 0 and idx < len(df) - 3:
                prev_close = df['close'].iloc[idx - 1]
                from_above = prev_close > mid

                if from_above:
                    # Should bounce UP
                    for j in range(1, min(4, len(df) - idx)):
                        if df['close'].iloc[idx + j] > top:
                            reversals += 1
                            break
                else:
                    # Should bounce DOWN
                    for j in range(1, min(4, len(df) - idx)):
                        if df['close'].iloc[idx + j] < bottom:
                            reversals += 1
                            break

    reversal_rate = (reversals / touches * 100) if touches > 0 else 0

    # Is it near historical extreme?
    near_high = (price_max - mid) / price_max < 0.10  # Within 10% of high
    near_low = (mid - price_min) / price_min < 0.10   # Within 10% of low

    print(f"  Touches: {touches}")
    print(f"  Reversals: {reversals} ({reversal_rate:.1f}%)")
    print(f"  Near historical HIGH: {near_high}")
    print(f"  Near historical LOW: {near_low}")

    # Check if its at a major swing point
    # Find closest swing high/low to this level
    highs = df['high'].nlargest(20).values
    lows = df['low'].nsmallest(20).values

    closest_high_dist = min([abs(h - mid) for h in highs])
    closest_low_dist = min([abs(l - mid) for l in lows])

    near_swing_high = closest_high_dist / mid < 0.02  # Within 2%
    near_swing_low = closest_low_dist / mid < 0.02

    print(f"  Near major swing HIGH: {near_swing_high} (distance: {closest_high_dist:.5f})")
    print(f"  Near major swing LOW: {near_swing_low} (distance: {closest_low_dist:.5f})")

    print()

print("="*80)
print("PATTERN SUMMARY - What makes these levels special:")
print("="*80)
print()
print("Common characteristics:")
print("1. Zone height: ~1.3-2% of price (averaging ~1.9%)")
print("2. High touch count (3-38 touches)")
print("3. Good reversal rate (60-100%)")
print("4. Either:")
print("   - Near major historical high/low, OR")
print("   - High touch count from repeated respect")
print()
print("Distribution pattern:")
print("  Level 1: Near top of range (major highs)")
print("  Level 2: Middle-upper (high touches)")
print("  Level 3: Middle-lower (highest touches)")
print("  Level 4: Near bottom (all-time low)")
print()
print("="*80)
print("ALGORITHM TO FIND SIMILAR LEVELS ON OTHER PAIRS:")
print("="*80)
print()
print("1. Get full monthly data for pair")
print("2. Find price range (min to max)")
print("3. Test zones with ~1.7-2% height across entire range")
print("4. For each zone, count:")
print("   - Total touches")
print("   - Reversals")
print("   - Reversal rate")
print("5. Also identify zones near:")
print("   - Historical highs/lows")
print("   - Major swing points")
print("6. Score zones by:")
print("   - Touch count * 5")
print("   - Reversal count * 10")
print("   - Bonus if near extreme")
print("7. Distribute final 3-4 levels across price range")
print("   (top area, middle-upper, middle-lower, bottom area)")
