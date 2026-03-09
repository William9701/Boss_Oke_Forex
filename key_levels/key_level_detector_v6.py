import pandas as pd
import MetaTrader5 as mt5
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class KeyLevelDetectorV6:
    """
    V6 Key Level Detector - SEPARATED CLEAN REVERSALS ONLY

    KEY REQUIREMENTS:
    - Price must touch zone from a clear direction (from above or below)
    - Price must REVERSE STRONGLY (move at least 2.5% away from zone)
    - Touches must be SEPARATED in time (minimum 5 bars apart)
    - NO clustered/consecutive touches (filters out consolidation zones)
    - Minimum 3 touches with 80%+ reversal rate
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
        """Find key levels with proper touch + reversal detection"""
        print(f"\nFinding {num_levels} key levels for {symbol}...")

        price_min = df['low'].min()
        price_max = df['high'].max()

        # Test many potential zones
        all_zones = []

        # V4: Wider zone heights (1.5% to 5% to capture ranges like 155-162 on USDJPY)
        zone_heights = [0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05]

        for zone_height_pct in zone_heights:
            step = price_min * 0.004  # 0.4% steps
            current = price_min

            while current < price_max:
                zone_bottom = current
                zone_top = current * (1 + zone_height_pct)
                zone_mid = (zone_top + zone_bottom) / 2

                # V6: Test this zone with SEPARATED reversal detection
                result = self.test_zone_v6(df, zone_bottom, zone_top)

                # V6: Minimum 3 touches, 80% reversal rate (clean separated reversals)
                if result['touches'] >= 3 and result['reversal_rate'] >= 80:
                    # Score
                    score = result['touches'] * 8
                    score += result['reversals'] * 12
                    score += result['reversal_rate'] / 5

                    # Bonus for recent touches
                    score += result['recent_touches'] * 15

                    # Bonus for good distribution over time
                    if result['time_span'] > 100:
                        score += 50

                    result['score'] = score
                    all_zones.append(result)

                current += step

        print(f"Found {len(all_zones)} candidate zones (3+ touches, 80%+ reversal, SEPARATED clean reversals)")

        if len(all_zones) == 0:
            print(f"No zones found for {symbol}!")
            return []

        # Remove overlapping zones (keep highest score)
        all_zones = self.remove_overlaps(all_zones)

        # Sort by score
        all_zones.sort(key=lambda x: x['score'], reverse=True)

        # Distribute across price range
        final_zones = self.distribute_across_range(all_zones, num_levels, price_min, price_max)

        # Sort by price (high to low)
        final_zones.sort(key=lambda x: x['mid'], reverse=True)

        return final_zones

    def test_zone_v6(self, df, zone_bottom, zone_top):
        """V6: SEPARATED CLEAN REVERSALS - touches must be well separated in time"""
        zone_mid = (zone_top + zone_bottom) / 2

        touches = 0
        reversals = 0
        recent_touches = 0
        touch_indices = []

        # V6: Minimum reversal distance (2.5% move away from zone)
        MIN_REVERSAL_DISTANCE = 0.025

        # V6: Minimum bars between touches (5 bars = ~5 months separation)
        MIN_BARS_BETWEEN_TOUCHES = 5

        i = 0
        last_touch_idx = -999  # Track last touch to enforce separation

        while i < len(df) - 5:  # Need more bars ahead to verify reversal
            bar_high = df['high'].iloc[i]
            bar_low = df['low'].iloc[i]
            bar_close = df['close'].iloc[i]

            # V6: Did price touch this zone?
            if bar_low <= zone_top and bar_high >= zone_bottom:

                # V6: ENFORCE TIME SEPARATION - skip if too close to previous touch
                if i - last_touch_idx < MIN_BARS_BETWEEN_TOUCHES:
                    i += 1
                    continue

                # V6: Check WHERE price came from (look back 3-5 bars)
                came_from_above = False
                came_from_below = False

                for lookback in range(1, 6):
                    if i >= lookback:
                        prev_close = df['close'].iloc[i - lookback]
                        if prev_close > zone_top * 1.02:  # Clearly above zone (2%+)
                            came_from_above = True
                            break
                        elif prev_close < zone_bottom * 0.98:  # Clearly below zone (2%+)
                            came_from_below = True
                            break

                # Only count if price came from a clear direction
                if not (came_from_above or came_from_below):
                    i += 1
                    continue

                touches += 1
                touch_indices.append(i)
                last_touch_idx = i  # Update last touch position

                if i < 50:  # Recent (last 50 bars = ~4 years)
                    recent_touches += 1

                # V6: Check for STRONG reversal (price must move 2.5%+ away from zone)
                if i < len(df) - 5:
                    if came_from_above:
                        # Resistance - check for strong bounce DOWN
                        for j in range(1, 6):
                            future_low = df['low'].iloc[i + j]
                            distance_moved = (zone_bottom - future_low) / zone_bottom
                            if distance_moved >= MIN_REVERSAL_DISTANCE:
                                reversals += 1
                                break

                    elif came_from_below:
                        # Support - check for strong bounce UP
                        for j in range(1, 6):
                            future_high = df['high'].iloc[i + j]
                            distance_moved = (future_high - zone_top) / zone_top
                            if distance_moved >= MIN_REVERSAL_DISTANCE:
                                reversals += 1
                                break

                # V6: Skip ahead after counting a touch
                i += MIN_BARS_BETWEEN_TOUCHES
            else:
                i += 1

        reversal_rate = (reversals / touches * 100) if touches > 0 else 0

        # Calculate time span
        time_span = 0
        if len(touch_indices) >= 2:
            time_span = max(touch_indices) - min(touch_indices)

        return {
            'bottom': zone_bottom,
            'top': zone_top,
            'mid': zone_mid,
            'touches': touches,
            'reversals': reversals,
            'reversal_rate': reversal_rate,
            'recent_touches': recent_touches,
            'time_span': time_span,
            'touch_indices': touch_indices,  # Store indices for visualization
            'score': 0
        }

    def remove_overlaps(self, zones):
        """Remove overlapping zones, keep highest score"""
        filtered = []

        for zone in sorted(zones, key=lambda x: x['score'], reverse=True):
            is_overlap = False

            for existing in filtered:
                # Check if zones overlap significantly (>50% overlap)
                overlap_bottom = max(zone['bottom'], existing['bottom'])
                overlap_top = min(zone['top'], existing['top'])

                if overlap_top > overlap_bottom:
                    overlap_size = overlap_top - overlap_bottom
                    zone_size = zone['top'] - zone['bottom']

                    if overlap_size / zone_size > 0.5:
                        is_overlap = True
                        break

            if not is_overlap:
                filtered.append(zone)

        return filtered

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
        print(f"{symbol} - DETECTED {len(zones)} KEY LEVELS (V6 - SEPARATED REVERSALS)")
        print(f"{'='*70}\n")

        for i, zone in enumerate(zones, 1):
            height = zone['top'] - zone['bottom']

            print(f"Level {i}: {zone['bottom']:.5f} - {zone['top']:.5f}")
            print(f"  Mid: {zone['mid']:.5f}")
            print(f"  Height: {height:.5f} ({height/zone['mid']*100:.2f}%)")
            print(f"  Touches: {zone['touches']} (Recent: {zone['recent_touches']})")
            print(f"  Reversals: {zone['reversals']} ({zone['reversal_rate']:.1f}%)")
            print(f"  Time Span: {zone['time_span']} bars")
            print(f"  Score: {zone['score']:.0f}")
            print()

    def visualize(self, df, zones, symbol):
        """Visualize levels with candlestick chart"""
        fig, ax = plt.subplots(figsize=(24, 12))

        # Draw candlesticks manually
        width = 15  # width in days for monthly candles
        width2 = 3  # width of the wick

        for idx in range(len(df)):
            row = df.iloc[idx]
            color = 'green' if row['close'] >= row['open'] else 'red'

            # Draw high-low line (wick)
            ax.plot([row['time'], row['time']], [row['low'], row['high']],
                   color=color, linewidth=1, alpha=0.8)

            # Draw open-close rectangle (body)
            height = abs(row['close'] - row['open'])
            bottom = min(row['open'], row['close'])

            from matplotlib.patches import Rectangle
            rect = Rectangle((row['time'] - pd.Timedelta(days=width2), bottom),
                           pd.Timedelta(days=width2*2), height,
                           facecolor=color, edgecolor=color, alpha=0.8)
            ax.add_patch(rect)

        colors = ['red', 'blue', 'green', 'orange']
        for i, zone in enumerate(zones):
            color = colors[i % len(colors)]

            # Draw zone as horizontal band
            ax.axhspan(zone['bottom'], zone['top'], alpha=0.3, color=color)
            ax.axhline(zone['mid'], color=color, linestyle='--', linewidth=1.5, alpha=0.7)

            # Mark touch/reversal points with circles
            if 'touch_indices' in zone:
                for touch_idx in zone['touch_indices']:
                    if touch_idx < len(df):
                        touch_time = df['time'].iloc[touch_idx]
                        touch_price = zone['mid']
                        ax.scatter(touch_time, touch_price, color=color, s=100,
                                 marker='o', edgecolors='white', linewidths=2, zorder=10)

            # Label with zone info
            label_text = f"L{i+1}\n{zone['mid']:.5f}\n{zone['touches']}T ({zone['reversals']}Rev)\n{zone['reversal_rate']:.0f}%"
            ax.text(df['time'].iloc[-10], zone['mid'], label_text,
                   fontsize=11, color='white', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor=color, alpha=0.9),
                   ha='left', va='center')

        ax.set_xlabel('Time', fontsize=13, fontweight='bold')
        ax.set_ylabel('Price', fontsize=13, fontweight='bold')
        ax.set_title(f'{symbol} - Key Levels V6 (Separated Clean Reversals)', fontsize=15, fontweight='bold')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        filename = f'{symbol}_key_levels_v6.png'
        plt.savefig(filename, dpi=150)
        print(f"Chart saved: {filename}")
        plt.close()

if __name__ == "__main__":
    detector = KeyLevelDetectorV6()

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
