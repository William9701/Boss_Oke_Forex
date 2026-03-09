import pandas as pd
import MetaTrader5 as mt5

def get_monthly_data(symbol='EURUSD', num_bars=300):
    if not mt5.initialize():
        return None

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_MN1, 0, num_bars)
    if rates is None:
        mt5.shutdown()
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')

    mt5.shutdown()
    return df

def test_zone_touches(df, bottom, top, name):
    """Count touches in a specific zone"""
    touches = 0

    for idx in range(len(df)):
        bar_high = df['high'].iloc[idx]
        bar_low = df['low'].iloc[idx]

        if bar_low <= top and bar_high >= bottom:
            touches += 1

    return touches

# Get data
df = get_monthly_data('EURUSD', 300)

if df is not None:
    print("="*70)
    print("TESTING ZONES AROUND DIFFERENT PRICE LEVELS")
    print("="*70 + "\n")

    # Zone height to test (1.7%)
    zone_height_pct = 0.017

    # Test zones around different price points
    test_prices = [1.49, 1.41, 1.34, 1.24, 1.10, 1.06, 1.03, 0.84]

    results = []

    for price in test_prices:
        bottom = price * (1 - zone_height_pct/2)
        top = price * (1 + zone_height_pct/2)

        touches = test_zone_touches(df, bottom, top, f"{price:.2f}")

        results.append({
            'price': price,
            'bottom': bottom,
            'top': top,
            'touches': touches
        })

    # Sort by touch count
    results.sort(key=lambda x: x['touches'], reverse=True)

    print("ZONES SORTED BY TOUCH COUNT:\n")
    for r in results:
        print(f"Price ~{r['price']:.2f}: {r['bottom']:.5f} - {r['top']:.5f} => {r['touches']} touches")

    print("\n" + "="*70)
    print("INSIGHT: Which price levels have the most touches?")
    print("="*70)
