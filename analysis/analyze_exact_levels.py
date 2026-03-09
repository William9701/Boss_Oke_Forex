import pandas as pd
import MetaTrader5 as mt5
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Your exact manual levels
MANUAL_LEVELS = [
    (1.50091, 1.48135),  # Level 1
    (1.25431, 1.23561),  # Level 2
    (1.07291, 1.05350),  # Level 3
    (0.85163, 0.83235)   # Level 4
]

def get_monthly_data(symbol='EURUSD', num_bars=300):
    """Get monthly OHLC data from MT5"""
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return None

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_MN1, 0, num_bars)

    if rates is None or len(rates) == 0:
        print(f"Failed to get data for {symbol}")
        mt5.shutdown()
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')

    print(f"Loaded {len(df)} monthly bars for {symbol}")
    print(f"Date range: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    print(f"Price range: {df['low'].min():.5f} to {df['high'].max():.5f}\n")

    mt5.shutdown()
    return df

def analyze_level_deeply(df, level_top, level_bottom, level_num):
    """Deeply analyze what happens at this specific level"""
    level_mid = (level_top + level_bottom) / 2

    print(f"\n{'='*70}")
    print(f"LEVEL {level_num}: {level_bottom:.5f} - {level_top:.5f} (Mid: {level_mid:.5f})")
    print(f"{'='*70}\n")

    # Find ALL bars that touched this zone
    touches = []

    for idx in range(len(df)):
        bar_high = df['high'].iloc[idx]
        bar_low = df['low'].iloc[idx]
        bar_close = df['close'].iloc[idx]
        bar_open = df['open'].iloc[idx]
        bar_time = df['time'].iloc[idx]

        # Did price touch this zone?
        if bar_low <= level_top and bar_high >= level_bottom:
            touches.append({
                'index': idx,
                'time': bar_time,
                'open': bar_open,
                'high': bar_high,
                'low': bar_low,
                'close': bar_close,
                'in_zone': True
            })

    print(f"Total bars that touched this level: {len(touches)}\n")

    # Show each touch
    print("TOUCH DETAILS:")
    print("-" * 70)
    for i, touch in enumerate(touches, 1):
        print(f"{i:2d}. {touch['time'].strftime('%Y-%m')}: "
              f"O:{touch['open']:.5f} H:{touch['high']:.5f} "
              f"L:{touch['low']:.5f} C:{touch['close']:.5f}")

    # Analyze reversals
    print(f"\n{'='*70}")
    print("REVERSAL ANALYSIS:")
    print("-" * 70)

    reversals = 0
    for i, touch in enumerate(touches):
        idx = touch['index']

        if idx == 0 or idx >= len(df) - 3:
            continue

        prev_close = df['close'].iloc[idx - 1]

        # Determine if coming from above or below
        from_above = prev_close > level_mid

        # Check what happened in next 3 bars
        next_closes = [df['close'].iloc[idx + j] for j in range(1, min(4, len(df) - idx))]

        if from_above:
            # Should bounce UP
            bounced_up = any(c > level_top for c in next_closes)
            if bounced_up:
                reversals += 1
                print(f"{touch['time'].strftime('%Y-%m')}: Hit from ABOVE -> Bounced UP (Support)")
            else:
                print(f"{touch['time'].strftime('%Y-%m')}: Hit from ABOVE -> No bounce (Broke down)")
        else:
            # Should bounce DOWN
            bounced_down = any(c < level_bottom for c in next_closes)
            if bounced_down:
                reversals += 1
                print(f"{touch['time'].strftime('%Y-%m')}: Hit from BELOW -> Bounced DOWN (Resistance)")
            else:
                print(f"{touch['time'].strftime('%Y-%m')}: Hit from BELOW -> No bounce (Broke up)")

    reversal_rate = (reversals / len(touches) * 100) if touches else 0

    print(f"\n{'='*70}")
    print(f"SUMMARY: {reversals}/{len(touches)} reversals = {reversal_rate:.1f}% reversal rate")
    print(f"{'='*70}\n")

    return {
        'touches': len(touches),
        'reversals': reversals,
        'reversal_rate': reversal_rate,
        'touch_details': touches
    }

def visualize_level(df, level_top, level_bottom, level_num, stats):
    """Visualize single level on chart"""
    fig, ax = plt.subplots(figsize=(24, 10))

    # Plot full price history
    ax.plot(df['time'], df['close'], color='black', linewidth=1, label='Close', alpha=0.7)
    ax.plot(df['time'], df['high'], color='gray', linewidth=0.5, alpha=0.3)
    ax.plot(df['time'], df['low'], color='gray', linewidth=0.5, alpha=0.3)

    # Highlight the level zone
    level_mid = (level_top + level_bottom) / 2
    ax.axhspan(level_bottom, level_top, alpha=0.3, color='red',
               label=f'Level {level_num} Zone')
    ax.axhline(level_mid, color='red', linestyle='--', linewidth=2,
               label=f'Mid: {level_mid:.5f}')

    # Mark each touch
    for touch in stats['touch_details']:
        idx = touch['index']
        ax.scatter(touch['time'], touch['close'], color='blue', s=100, zorder=5, alpha=0.6)
        ax.axvline(touch['time'], color='blue', alpha=0.1, linewidth=1)

    ax.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax.set_ylabel('Price', fontsize=12, fontweight='bold')
    ax.set_title(f'Level {level_num}: {level_bottom:.5f} - {level_top:.5f} | '
                 f'{stats["touches"]} touches, {stats["reversals"]} reversals ({stats["reversal_rate"]:.1f}%)',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'level_{level_num}_analysis.png', dpi=150)
    print(f"Chart saved: level_{level_num}_analysis.png")
    plt.close()

def main():
    print("="*70)
    print("ANALYZING YOUR EXACT MANUAL LEVELS")
    print("="*70)

    df = get_monthly_data('EURUSD', num_bars=300)

    if df is None:
        return

    all_stats = []

    for i, (top, bottom) in enumerate(MANUAL_LEVELS, 1):
        stats = analyze_level_deeply(df, top, bottom, i)
        all_stats.append(stats)
        visualize_level(df, top, bottom, i, stats)

    # Overall summary
    print("\n" + "="*70)
    print("OVERALL SUMMARY OF ALL MANUAL LEVELS")
    print("="*70)

    for i, (top, bottom) in enumerate(MANUAL_LEVELS, 1):
        stats = all_stats[i-1]
        mid = (top + bottom) / 2
        height = top - bottom
        height_pct = (height / mid) * 100

        print(f"\nLevel {i}: {bottom:.5f} - {top:.5f}")
        print(f"  Mid: {mid:.5f}")
        print(f"  Height: {height:.5f} ({height_pct:.2f}%)")
        print(f"  Touches: {stats['touches']}")
        print(f"  Reversals: {stats['reversals']}")
        print(f"  Reversal Rate: {stats['reversal_rate']:.1f}%")

if __name__ == "__main__":
    main()
