"""
Test zeta-zetra head and shoulders code on NZDUSD with MT5 data
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import linregress
import MetaTrader5 as mt5

# plt.style.use('seaborn-darkgrid')  # Removed - deprecated

def pivot_id(ohlc: pd.DataFrame, l:int , n1:int , n2:int ):
    """
    Get the pivot id
    """
    # Check if the length conditions met
    if l-n1 < 0 or l+n2 >= len(ohlc):
        return 0

    pivot_low  = 1
    pivot_high = 1

    for i in range(l-n1, l+n2+1):
        if(ohlc.loc[l,"Low"] > ohlc.loc[i, "Low"]):
            pivot_low = 0

        if(ohlc.loc[l, "High"] < ohlc.loc[i, "High"]):
            pivot_high = 0

    if pivot_low and pivot_high:
        return 3
    elif pivot_low:
        return 1
    elif pivot_high:
        return 2
    else:
        return 0


def pivot_point_position(row):
    """Get the Pivot Point position"""
    if row['Pivot']==1:
        return row['Low']-1e-3
    elif row['Pivot']==2:
        return row['Low']+1e-3
    else:
        return np.nan


def _find_points(df, candle_id, back_candles):
    """Find points provides all the necessary arrays and data of interest"""
    maxim = np.array([])
    minim = np.array([])
    xxmin = np.array([])
    xxmax = np.array([])
    minbcount=0 #minimas before head
    maxbcount=0 #maximas before head
    minacount=0 #minimas after head
    maxacount=0 #maximas after head

    for i in range(candle_id-back_candles, candle_id+back_candles):
        if df.loc[i,"ShortPivot"] == 1:
            minim = np.append(minim, df.loc[i, "Low"])
            xxmin = np.append(xxmin, i)
            if i < candle_id:
                minbcount=+1
            elif i>candle_id:
                minacount+=1
        if df.loc[i, "ShortPivot"] == 2:
            maxim = np.append(maxim, df.loc[i, "High"])
            xxmax = np.append(xxmax, i)
            if i < candle_id:
                maxbcount+=1
            elif i>candle_id:
                maxacount+=1

    return maxim, minim, xxmax, xxmin, maxacount, minacount, maxbcount, minbcount


def find_inverse_head_and_shoulders(df, back_candles=14):
    """Find all the inverse head and shoulders chart patterns"""
    all_points = []
    for candle_id in range(back_candles+20, len(df)-back_candles):

        if df.loc[candle_id, "Pivot"] != 1 or df.loc[candle_id,"ShortPivot"] != 1:
            continue

        maxim, minim, xxmax, xxmin, maxacount, minacount, maxbcount, minbcount = _find_points(df, candle_id, back_candles)
        if minbcount<1 or minacount<1 or maxbcount<1 or maxacount<1:
            continue

        slmax, intercmax, rmax, pmax, semax = linregress(xxmax, maxim)

        headidx = np.argmin(minim, axis=0)

        try:
            if minim[headidx-1]-minim[headidx]>1.5e-3 and minim[headidx+1]-minim[headidx]>1.5e-3 and abs(slmax)<=1e-4:
                all_points.append(candle_id)
        except:
            pass

    return all_points


def find_head_and_shoulders(df: pd.DataFrame, back_candles: int = 14):
    """Find all head and shoulder chart patterns"""
    all_points = []
    for candle_id in range(back_candles+20, len(df)-back_candles):

        if df.loc[candle_id, "Pivot"] != 2 or df.loc[candle_id,"ShortPivot"] != 2:
            continue

        maxim, minim, xxmax, xxmin, maxacount, minacount, maxbcount, minbcount = _find_points(df, candle_id, back_candles)
        if minbcount<1 or minacount<1 or maxbcount<1 or maxacount<1:
            continue

        slmin, intercmin, rmin, pmin, semin = linregress(xxmin, minim)
        headidx = np.argmax(maxim, axis=0)

        if maxim[headidx]-maxim[headidx-1]>1.5e-3 and maxim[headidx]-maxim[headidx+1]>1.5e-3 and abs(slmin)<=1e-4:
            all_points.append(candle_id)

    return all_points


def visualize_patterns(ohlc, all_inverse, all_bearish, symbol):
    """Visualize detected patterns on a single chart"""
    fig, ax = plt.subplots(figsize=(24, 12))

    # Plot price
    ax.plot(ohlc['Date'], ohlc['Close'], color='black', linewidth=1.5, label='Close', alpha=0.8)

    # Mark inverse H&S patterns
    for point in all_inverse:
        ax.plot(ohlc.loc[point, 'Date'], ohlc.loc[point, 'Low'], 'v',
                color='green', markersize=12, label='Inverse H&S' if point == all_inverse[0] else '')

    # Mark bearish H&S patterns
    for point in all_bearish:
        ax.plot(ohlc.loc[point, 'Date'], ohlc.loc[point, 'High'], '^',
                color='red', markersize=12, label='Bearish H&S' if point == all_bearish[0] else '')

    ax.set_xlabel('Date', fontsize=13, fontweight='bold')
    ax.set_ylabel('Price', fontsize=13, fontweight='bold')
    ax.set_title(f'{symbol} - Zeta Head & Shoulders Detection', fontsize=15, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

    plt.tight_layout()
    filename = f'zeta_{symbol}_hs_detection.png'
    plt.savefig(filename, dpi=150)
    print(f"\nChart saved: {filename}")
    plt.close()


if __name__ == "__main__":

    # Load NZDUSD data from MT5
    print("Loading NZDUSD data from MT5...")

    if not mt5.initialize():
        print("MT5 initialization failed")
        exit()

    # Get monthly data
    rates = mt5.copy_rates_from_pos("NZDUSD", mt5.TIMEFRAME_MN1, 0, 300)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        print("Failed to get NZDUSD data")
        exit()

    # Convert to DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')

    # Prepare OHLC format
    ohlc = pd.DataFrame()
    ohlc['Date'] = df['time']
    ohlc['Open'] = df['open']
    ohlc['High'] = df['high']
    ohlc['Low'] = df['low']
    ohlc['Close'] = df['close']

    print(f"Loaded {len(ohlc)} monthly bars for NZDUSD")
    print(f"Date range: {ohlc['Date'].iloc[0]} to {ohlc['Date'].iloc[-1]}")

    # Calculate pivots
    print("\nCalculating pivots...")
    ohlc["Pivot"] = ohlc.apply(lambda x: pivot_id(ohlc, x.name, 15, 15), axis=1)
    ohlc['ShortPivot'] = ohlc.apply(lambda x: pivot_id(ohlc, x.name, 5, 5), axis=1)
    ohlc['PointPos'] = ohlc.apply(lambda row: pivot_point_position(row), axis=1)

    back_candles = 14

    # Find patterns
    print("\nDetecting patterns...")
    all_inverse = find_inverse_head_and_shoulders(ohlc, back_candles=back_candles)
    all_bearish = find_head_and_shoulders(ohlc, back_candles=back_candles)

    print(f"\n{'='*60}")
    print(f"NZDUSD - ZETA HEAD & SHOULDERS DETECTION")
    print(f"{'='*60}")
    print(f"Inverse H&S patterns found: {len(all_inverse)}")
    print(f"Bearish H&S patterns found: {len(all_bearish)}")

    if all_inverse:
        print(f"\nInverse H&S at candles: {all_inverse}")

    if all_bearish:
        print(f"\nBearish H&S at candles: {all_bearish}")

    # Visualize
    visualize_patterns(ohlc, all_inverse, all_bearish, "NZDUSD")
