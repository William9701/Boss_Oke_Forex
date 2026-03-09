import pandas as pd
import MetaTrader5 as mt5
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# YOUR EXACT MANUAL LEVELS FOR EURUSD
EURUSD_KEY_LEVELS = [
    (1.50091, 1.48135),  # Level 1
    (1.25431, 1.23561),  # Level 2
    (1.07291, 1.05350),  # Level 3
    (0.85163, 0.83235)   # Level 4
]

def get_monthly_data(symbol='EURUSD', num_bars=300):
    if not mt5.initialize():
        print(f"MT5 initialization failed")
        return None

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_MN1, 0, num_bars)
    if rates is None:
        mt5.shutdown()
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')

    print(f"Loaded {len(df)} monthly bars for {symbol}")
    print(f"Price range: {df['low'].min():.5f} to {df['high'].max():.5f}\n")

    mt5.shutdown()
    return df

def visualize_exact_levels(df, symbol):
    """Visualize YOUR exact manual levels"""
    fig, ax = plt.subplots(figsize=(24, 12))

    # Plot price
    ax.plot(df['time'], df['close'], color='black', linewidth=1.5, label='Close', alpha=0.8)
    ax.fill_between(df['time'], df['low'], df['high'], color='gray', alpha=0.08)

    # Plot YOUR exact levels
    colors = ['red', 'blue', 'green', 'orange']

    for i, (top, bottom) in enumerate(EURUSD_KEY_LEVELS, 1):
        mid = (top + bottom) / 2
        color = colors[i % len(colors)]

        # Zone
        ax.axhspan(bottom, top, alpha=0.3, color=color,
                  label=f"Level {i}: {bottom:.5f} - {top:.5f}")

        # Mid line
        ax.axhline(mid, color=color, linestyle='--', linewidth=2, alpha=0.8)

        # Label
        label_text = f"L{i}\n{mid:.5f}\n{bottom:.5f}-{top:.5f}"
        ax.text(df['time'].iloc[-10], mid, label_text,
               fontsize=11, color='white', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.5', facecolor=color, alpha=0.95),
               ha='left', va='center')

    ax.set_xlabel('Time', fontsize=13, fontweight='bold')
    ax.set_ylabel('Price', fontsize=13, fontweight='bold')
    ax.set_title(f'{symbol} - YOUR EXACT KEY LEVELS', fontsize=16, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left', fontsize=10)

    plt.tight_layout()
    filename = f'{symbol}_EXACT_key_levels.png'
    plt.savefig(filename, dpi=150)
    print(f"Chart saved: {filename}\n")
    plt.close()

def print_levels():
    """Print YOUR exact levels"""
    print("="*70)
    print("YOUR EXACT KEY LEVELS FOR EURUSD")
    print("="*70 + "\n")

    for i, (top, bottom) in enumerate(EURUSD_KEY_LEVELS, 1):
        mid = (top + bottom) / 2
        height = top - bottom
        height_pips = height * 10000

        print(f"Level {i}: {bottom:.5f} - {top:.5f}")
        print(f"  Mid Point: {mid:.5f}")
        print(f"  Zone Height: {height:.5f} ({height_pips:.1f} pips)")
        print()

if __name__ == "__main__":
    print_levels()

    symbol = 'EURUSD'
    df = get_monthly_data(symbol, num_bars=300)

    if df is not None:
        visualize_exact_levels(df, symbol)
        print("✓ YOUR EXACT LEVELS VISUALIZED!")
