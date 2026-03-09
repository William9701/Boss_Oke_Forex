import pandas as pd
import MetaTrader5 as mt5
import numpy as np
from scipy.signal import argrelextrema
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class KeyLevelDetectorV3:
    """
    V3 Key Level Detector - PROPER SWING-BASED DETECTION

    KEY CHANGE:
    - Detect SWING HIGHS/LOWS first (using scipy)
    - Test zones against SWING POINTS only (not every bar)
    - Minimum 5 SWING touches (proper bounces)
    - Check if swings actually reversed after touching zone
    """

    def get_monthly_data(self, symbol, num_bars=300):
        if not mt5.initialize():
            print(f"MT5 initialization failed")
            return None

        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_MN1, 0, num_bars)
        if rates is None:
            mt5.shutdown()
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        print(f"\n{symbol}: Loaded {len(df)} monthly bars")
        print(f"Price range: {df['low'].min():.5f} to {df['high'].max():.5f}")

        mt5.shutdown()
        return df

    def find_swing_points(self, df, order=5):
        """Find swing highs and lows using scipy"""
        highs = df['high'].values
        lows = df['low'].values

        # Find local maxima (swing highs)
        swing_high_indices = argrelextrema(highs, np.greater, order=order)[0]

        # Find local minima (swing lows)
        swing_low_indices = argrelextrema(lows, np.less, order=order)[0]

        swing_highs = [(i, highs[i]) for i in swing_high_indices]
        swing_lows = [(i, lows[i]) for i in swing_low_indices]

        print(f"Found {len(swing_highs)} swing highs, {len(swing_lows)} swing lows")

        return swing_highs, swing_lows

    def find_key_levels(self, df, symbol, num_levels=4):
        """Find key levels using SWING-BASED detection"""
        print(f"\nFinding {num_levels} key levels for {symbol}...")

        price_min = df['low'].min()
        price_max = df['high'].max()

        # V3: Find swing points FIRST
        swing_highs, swing_lows = self.find_swing_points(df, order=5)

        # Test many potential zones
        all_zones = []

        # Zone heights: 1.5-3%
        zone_heights = [0.015, 0.017, 0.019, 0.020, 0.025, 0.030]

        for zone_height_pct in zone_heights:
            step = price_min * 0.003  # 0.3% steps
            current = price_min

            while current < price_max:
                zone_bottom = current
                zone_top = current * (1 + zone_height_pct)
                zone_mid = (zone_top + zone_bottom) / 2

                # V3: Test this zone against SWINGS only
                result = self.test_zone_with_swings(df, zone_bottom, zone_top, swing_highs, swing_lows)

                # V3: Minimum 5 SWING touches, 60% reversal rate
                if result['swing_touches'] >= 5 and result['reversal_rate'] >= 60:
                    # Score based on swing touches and reversals
                    score = result['swing_touches'] * 10
                    score += result['reversals'] * 15
                    score += result['reversal_rate'] / 5

                    # Bonus for recent touches (last 50 bars)
                    score += result['recent_touches'] * 20

                    # Extra bonus if touches are well-distributed (not clustered)
                    if result['time_span'] > 100:  # Touches span >100 bars
                        score += 50

                    result['score'] = score
                    all_zones.append(result)

                current += step

        print(f"Found {len(all_zones)} candidate zones (5+ swing touches, 60%+ reversal)")

        if len(all_zones) == 0:
            print(f"No zones found for {symbol}!")
            return []

        # Sort by score
        all_zones.sort(key=lambda x: x['score'], reverse=True)

        # Distribute across price range
        final_zones = self.distribute_across_range(all_zones, num_levels, price_min, price_max)

        # Sort by price (high to low)
        final_zones.sort(key=lambda x: x['mid'], reverse=True)

        return final_zones

    def test_zone_with_swings(self, df, zone_bottom, zone_top, swing_highs, swing_lows):
        """V3: Test zone against SWING POINTS only"""
        zone_mid = (zone_top + zone_bottom) / 2

        swing_touches = 0
        reversals = 0
        recent_touches = 0
        touch_indices = []

        # Test swing HIGHS (resistance checks)
        for idx, swing_high in swing_highs:
            if zone_bottom <= swing_high <= zone_top:
                swing_touches += 1
                touch_indices.append(idx)

                if idx < 50:  # Recent (last 50 bars)
                    recent_touches += 1

                # Check if it reversed DOWN after touching (resistance)
                # Look at next 3 bars
                reversed = False
                for j in range(1, min(4, len(df) - idx)):
                    if df['close'].iloc[idx + j] < zone_bottom:
                        reversed = True
                        reversals += 1
                        break

        # Test swing LOWS (support checks)
        for idx, swing_low in swing_lows:
            if zone_bottom <= swing_low <= zone_top:
                swing_touches += 1
                touch_indices.append(idx)

                if idx < 50:  # Recent
                    recent_touches += 1

                # Check if it reversed UP after touching (support)
                reversed = False
                for j in range(1, min(4, len(df) - idx)):
                    if df['close'].iloc[idx + j] > zone_top:
                        reversed = True
                        reversals += 1
                        break

        reversal_rate = (reversals / swing_touches * 100) if swing_touches > 0 else 0

        # Calculate time span of touches
        time_span = 0
        if len(touch_indices) >= 2:
            time_span = max(touch_indices) - min(touch_indices)

        return {
            'bottom': zone_bottom,
            'top': zone_top,
            'mid': zone_mid,
            'swing_touches': swing_touches,
            'reversals': reversals,
            'reversal_rate': reversal_rate,
            'recent_touches': recent_touches,
            'time_span': time_span,
            'score': 0
        }

    def distribute_across_range(self, all_zones, num_levels, price_min, price_max):
        """Distribute levels across price range"""
        if len(all_zones) < num_levels:
            return all_zones[:num_levels]

        price_range = price_max - price_min
        section_size = price_range / num_levels

        distributed = []

        for section in range(num_levels):
            section_min = price_min + (section * section_size)
            section_max = price_min + ((section + 1) * section_size)

            # Find zones in this section
            zones_in_section = [
                z for z in all_zones
                if section_min <= z['mid'] <= section_max
            ]

            if zones_in_section:
                # Pick highest scoring zone
                best = max(zones_in_section, key=lambda x: x['score'])
                distributed.append(best)

        return distributed

    def print_levels(self, zones, symbol):
        """Print detected levels"""
        print(f"\n{'='*70}")
        print(f"{symbol} - DETECTED {len(zones)} KEY LEVELS (V3 - SWING-BASED)")
        print(f"{'='*70}\n")

        for i, zone in enumerate(zones, 1):
            height = zone['top'] - zone['bottom']

            print(f"Level {i}: {zone['bottom']:.5f} - {zone['top']:.5f}")
            print(f"  Mid: {zone['mid']:.5f}")
            print(f"  Height: {height:.5f} ({height/zone['mid']*100:.2f}%)")
            print(f"  SWING Touches: {zone['swing_touches']} (Recent: {zone['recent_touches']})")
            print(f"  Reversals: {zone['reversals']} ({zone['reversal_rate']:.1f}%)")
            print(f"  Time Span: {zone['time_span']} bars")
            print(f"  Score: {zone['score']:.0f}")
            print()

    def visualize(self, df, zones, symbol):
        """Visualize levels with swing points"""
        fig, ax = plt.subplots(figsize=(24, 12))

        ax.plot(df['time'], df['close'], color='black', linewidth=1.5, label='Close', alpha=0.8)
        ax.fill_between(df['time'], df['low'], df['high'], color='gray', alpha=0.08)

        # Draw swing points
        swing_highs, swing_lows = self.find_swing_points(df, order=5)

        for idx, high in swing_highs:
            ax.plot(df['time'].iloc[idx], high, 'v', color='red', markersize=4, alpha=0.3)

        for idx, low in swing_lows:
            ax.plot(df['time'].iloc[idx], low, '^', color='green', markersize=4, alpha=0.3)

        colors = ['red', 'blue', 'green', 'orange']
        for i, zone in enumerate(zones):
            color = colors[i % len(colors)]

            ax.axhspan(zone['bottom'], zone['top'], alpha=0.3, color=color)
            ax.axhline(zone['mid'], color=color, linestyle='--', linewidth=1.5, alpha=0.7)

            label_text = f"L{i+1}\n{zone['mid']:.5f}\n{zone['swing_touches']}ST {zone['reversal_rate']:.0f}%"
            ax.text(df['time'].iloc[-10], zone['mid'], label_text,
                   fontsize=11, color='white', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor=color, alpha=0.9),
                   ha='left', va='center')

        ax.set_xlabel('Time', fontsize=13, fontweight='bold')
        ax.set_ylabel('Price', fontsize=13, fontweight='bold')
        ax.set_title(f'{symbol} - Key Levels V3 (Swing-Based)', fontsize=15, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11)

        plt.tight_layout()
        filename = f'{symbol}_key_levels_v3.png'
        plt.savefig(filename, dpi=150)
        print(f"Chart saved: {filename}")
        plt.close()

if __name__ == "__main__":
    detector = KeyLevelDetectorV3()

    # Test on USDJPY first
    for symbol in ['USDJPY', 'EURUSD', 'GBPUSD']:
        df = detector.get_monthly_data(symbol, num_bars=300)

        if df is not None:
            zones = detector.find_key_levels(df, symbol, num_levels=4)

            if zones:
                detector.print_levels(zones, symbol)
                detector.visualize(df, zones, symbol)
            else:
                print(f"No levels found for {symbol}")

        print("\n" + "="*70 + "\n")
