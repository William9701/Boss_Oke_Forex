import pandas as pd
import MetaTrader5 as mt5

# Load data
if not mt5.initialize():
    print("Failed")
    exit()

rates = mt5.copy_rates_from_pos('USDJPY', mt5.TIMEFRAME_MN1, 0, 300)
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
mt5.shutdown()

# Test the 155-162 zone specifically
zone_bottom = 155.0
zone_top = 162.0
zone_mid = 158.5

print("=== TESTING ZONE 155-162 ON USDJPY ===\n")

touches = 0
reversals = 0
recent_touches = 0

i = 0
while i < len(df) - 1:
    bar_high = df['high'].iloc[i]
    bar_low = df['low'].iloc[i]
    bar_close = df['close'].iloc[i]
    bar_time = df['time'].iloc[i]

    # Did price touch this zone?
    if bar_low <= zone_top and bar_high >= zone_bottom:
        touches += 1
        print(f"Touch #{touches}: {bar_time.strftime('%Y-%m')} - H:{bar_high:.2f} L:{bar_low:.2f} C:{bar_close:.2f}")

        if i < 50:
            recent_touches += 1

        # Check for reversal
        if i < len(df) - 3:
            prev_close = df['close'].iloc[i - 1] if i > 0 else bar_close

            if prev_close > zone_mid or bar_close > zone_mid:
                # Check bounce DOWN
                for j in range(1, 4):
                    if df['close'].iloc[i + j] < zone_bottom:
                        reversals += 1
                        print(f"  -> REVERSED DOWN (bar {i+j}: {df['close'].iloc[i+j]:.2f})")
                        break
            else:
                # Check bounce UP
                for j in range(1, 4):
                    if df['close'].iloc[i + j] > zone_top:
                        reversals += 1
                        print(f"  -> REVERSED UP (bar {i+j}: {df['close'].iloc[i+j]:.2f})")
                        break

        i += 3
    else:
        i += 1

reversal_rate = (reversals / touches * 100) if touches > 0 else 0

print(f"\n=== RESULTS ===")
print(f"Zone: {zone_bottom} - {zone_top}")
print(f"Touches: {touches}")
print(f"Recent touches: {recent_touches}")
print(f"Reversals: {reversals}")
print(f"Reversal rate: {reversal_rate:.1f}%")
print(f"\nMeets criteria (5+ touches, 55%+ reversal)? {touches >= 5 and reversal_rate >= 55}")
