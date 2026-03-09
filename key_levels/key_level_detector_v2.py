import pandas as pd
import MetaTrader5 as mt5
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class KeyLevelDetectorV2:
    """
    V2 Key Level Detector - Improved to catch recent extremes

    IMPROVEMENTS:
    1. Lower minimum touches (3 instead of 5) for recent extremes
    2. Special scoring for absolute highs/lows in dataset
    3. Recency bonus - recent touches get higher weight
    4. Better extreme detection at top/bottom 10% of range
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

    def find_key_levels(self, df, symbol, num_levels=4):
        """Find key levels with improved extreme detection"""
        print(f"\nFinding {num_levels} key levels for {symbol}...")

        price_min = df['low'].min()
        price_max = df['high'].max()
        price_range = price_max - price_min

        # Get major swings for bonus scoring
        major_highs = df['high'].nlargest(15).values
        major_lows = df['low'].nsmallest(15).values

        # V2: Identify absolute extreme zones (top/bottom 5% of range)
        extreme_high_threshold = price_max - (price_range * 0.05)
        extreme_low_threshold = price_min + (price_range * 0.05)

        # Test many potential zones
        all_zones = []

        # Zone heights: 1.5-2.5% (extended range for V2)
        zone_heights = [0.015, 0.017, 0.019, 0.020, 0.025]

        for zone_height_pct in zone_heights:
            step = price_min * 0.002  # 0.2% steps
            current = price_min

            while current < price_max:
                zone_bottom = current
                zone_top = current * (1 + zone_height_pct)
                zone_mid = (zone_top + zone_bottom) / 2

                # V2: Check if this is an extreme zone
                is_extreme_high = zone_mid >= extreme_high_threshold
                is_extreme_low = zone_mid <= extreme_low_threshold

                # Test this zone
                result = self.test_zone(df, zone_bottom, zone_top)

                # V2: DYNAMIC minimum criteria based on location
                if is_extreme_high or is_extreme_low:
                    # Relaxed criteria for extremes: 3 touches, 50% reversal
                    min_touches = 3
                    min_reversal = 50.0
                else:
                    # Standard criteria: 5 touches, 55% reversal
                    min_touches = 5
                    min_reversal = 55.0

                if result['touches'] >= min_touches and result['reversal_rate'] >= min_reversal:
                    # Check if near major swing
                    near_high = min([abs(h - zone_mid) for h in major_highs]) / zone_mid < 0.02
                    near_low = min([abs(l - zone_mid) for l in major_lows]) / zone_mid < 0.02

                    # V2: IMPROVED SCORING
                    score = result['touches'] * 5
                    score += result['reversals'] * 10
                    score += result['reversal_rate'] / 10

                    # V2: Add recency bonus
                    score += result['recent_touches'] * 15  # Recent touches worth more

                    # BONUS for near extremes
                    if near_high or near_low:
                        score += 100

                    # V2: EXTRA BONUS for absolute extremes (top/bottom 5%)
                    if is_extreme_high or is_extreme_low:
                        score += 150
                        result['is_absolute_extreme'] = True
                    else:
                        result['is_absolute_extreme'] = False

                    result['score'] = score
                    result['near_extreme'] = near_high or near_low
                    all_zones.append(result)

                current += step

        print(f"Found {len(all_zones)} candidate zones")

        if len(all_zones) == 0:
            print(f"No zones found for {symbol}!")
            return []

        # Sort by score
        all_zones.sort(key=lambda x: x['score'], reverse=True)

        # Distribute across price range (key insight from EURUSD)
        final_zones = self.distribute_across_range(all_zones, num_levels, price_min, price_max)

        # Sort by price (high to low)
        final_zones.sort(key=lambda x: x['mid'], reverse=True)

        return final_zones

    def test_zone(self, df, zone_bottom, zone_top):
        """Test zone for touches and reversals - V2 with recency tracking"""
        zone_mid = (zone_top + zone_bottom) / 2

        touches = 0
        reversals = 0
        recent_touches = 0  # V2: Track touches in last 50 bars

        i = 0
        while i < len(df) - 1:
            bar_high = df['high'].iloc[i]
            bar_low = df['low'].iloc[i]

            if bar_low <= zone_top and bar_high >= zone_bottom:
                touches += 1

                # V2: Track recent touches (last 50 bars = ~4 years on monthly)
                if i < 50:
                    recent_touches += 1

                # Check reversal
                if i > 0 and i < len(df) - 3:
                    prev_close = df['close'].iloc[i - 1]
                    from_above = prev_close > zone_mid

                    if from_above:
                        for j in range(1, min(4, len(df) - i)):
                            if df['close'].iloc[i + j] > zone_top:
                                reversals += 1
                                break
                    else:
                        for j in range(1, min(4, len(df) - i)):
                            if df['close'].iloc[i + j] < zone_bottom:
                                reversals += 1
                                break

                i += 3
            else:
                i += 1

        reversal_rate = (reversals / touches * 100) if touches > 0 else 0

        return {
            'bottom': zone_bottom,
            'top': zone_top,
            'mid': zone_mid,
            'touches': touches,
            'reversals': reversals,
            'reversal_rate': reversal_rate,
            'recent_touches': recent_touches,  # V2
            'score': 0
        }

    def distribute_across_range(self, all_zones, num_levels, price_min, price_max):
        """
        Distribute levels across price range
        V2: Ensures top/bottom extremes are represented
        """
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
                # V2: Prefer absolute extremes if available
                absolute_extremes = [z for z in zones_in_section if z.get('is_absolute_extreme', False)]

                if absolute_extremes:
                    best = max(absolute_extremes, key=lambda x: x['score'])
                else:
                    best = max(zones_in_section, key=lambda x: x['score'])

                distributed.append(best)

        return distributed

    def print_levels(self, zones, symbol):
        """Print detected levels"""
        print(f"\n{'='*70}")
        print(f"{symbol} - DETECTED {len(zones)} KEY LEVELS (V2)")
        print(f"{'='*70}\n")

        for i, zone in enumerate(zones, 1):
            height = zone['top'] - zone['bottom']
            extreme_marker = " [EXTREME]" if zone.get('near_extreme') else ""
            absolute_marker = " [ABS TOP/BOT]" if zone.get('is_absolute_extreme') else ""

            print(f"Level {i}: {zone['bottom']:.5f} - {zone['top']:.5f}{extreme_marker}{absolute_marker}")
            print(f"  Mid: {zone['mid']:.5f}")
            print(f"  Height: {height:.5f} ({height/zone['mid']*100:.2f}%)")
            print(f"  Touches: {zone['touches']} (Recent: {zone['recent_touches']})")
            print(f"  Reversals: {zone['reversals']} ({zone['reversal_rate']:.1f}%)")
            print(f"  Score: {zone['score']:.0f}")
            print()

    def visualize(self, df, zones, symbol):
        """Visualize levels"""
        fig, ax = plt.subplots(figsize=(24, 12))

        ax.plot(df['time'], df['close'], color='black', linewidth=1.5, label='Close', alpha=0.8)
        ax.fill_between(df['time'], df['low'], df['high'], color='gray', alpha=0.08)

        colors = ['red', 'blue', 'green', 'orange']
        for i, zone in enumerate(zones):
            color = colors[i % len(colors)]

            ax.axhspan(zone['bottom'], zone['top'], alpha=0.3, color=color)
            ax.axhline(zone['mid'], color=color, linestyle='--', linewidth=1.5, alpha=0.7)

            extreme = "!" if zone.get('near_extreme') else ""
            absolute = "!!" if zone.get('is_absolute_extreme') else ""
            label_text = f"L{i+1}{extreme}{absolute}\n{zone['mid']:.5f}\n{zone['touches']}T ({zone['recent_touches']}R) {zone['reversal_rate']:.0f}%"
            ax.text(df['time'].iloc[-10], zone['mid'], label_text,
                   fontsize=11, color='white', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor=color, alpha=0.9),
                   ha='left', va='center')

        ax.set_xlabel('Time', fontsize=13, fontweight='bold')
        ax.set_ylabel('Price', fontsize=13, fontweight='bold')
        ax.set_title(f'{symbol} - Key Reversal Levels (V2)', fontsize=15, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11)

        plt.tight_layout()
        filename = f'{symbol}_key_levels_v2.png'
        plt.savefig(filename, dpi=150)
        print(f"Chart saved: {filename}")
        plt.close()

if __name__ == "__main__":
    detector = KeyLevelDetectorV2()

    # Test on USDJPY to see if it catches the 161-162 top zone
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
