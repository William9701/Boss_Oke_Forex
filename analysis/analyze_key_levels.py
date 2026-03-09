import pandas as pd
import MetaTrader5 as mt5
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class KeyLevelAnalyzer:
    def __init__(self):
        self.manual_levels = [
            (1.50091, 1.48135),
            (1.25431, 1.23561),
            (1.07291, 1.05350),
            (0.85163, 0.83235)
        ]

    def get_monthly_data(self, symbol='EURUSD', num_bars=300):
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
        print(f"Price range: {df['low'].min():.5f} to {df['high'].max():.5f}")

        mt5.shutdown()
        return df

    def analyze_manual_levels(self, df):
        """Analyze manual levels to understand what makes them special"""
        print("\n=== ANALYZING MANUAL KEY LEVELS ===\n")

        for i, (top, bottom) in enumerate(self.manual_levels, 1):
            zone_mid = (top + bottom) / 2
            zone_height = top - bottom

            print(f"Level {i}: {bottom:.5f} - {top:.5f} (Mid: {zone_mid:.5f})")

            # Count how many times price touched this zone
            touches = 0
            reversals = 0

            for idx in range(len(df)):
                bar_high = df['high'].iloc[idx]
                bar_low = df['low'].iloc[idx]

                # Check if price entered the zone
                if bar_low <= top and bar_high >= bottom:
                    touches += 1

                    # Check if it reversed (next 3 bars move away from zone)
                    if idx < len(df) - 3:
                        # Determine if zone is support or resistance
                        if zone_mid < df['close'].iloc[idx]:
                            # Zone below price = support, check for bounce up
                            next_moves = [df['close'].iloc[idx+j] > zone_mid for j in range(1, 4)]
                            if sum(next_moves) >= 2:
                                reversals += 1
                        else:
                            # Zone above price = resistance, check for bounce down
                            next_moves = [df['close'].iloc[idx+j] < zone_mid for j in range(1, 4)]
                            if sum(next_moves) >= 2:
                                reversals += 1

            reversal_rate = (reversals / touches * 100) if touches > 0 else 0

            print(f"  Touches: {touches}")
            print(f"  Reversals: {reversals}")
            print(f"  Reversal Rate: {reversal_rate:.1f}%")
            print()

    def find_price_clusters(self, df, num_levels=4):
        """
        Find price levels where market spent most time or had most reactions
        Strategy: Look for price areas with multiple touches and strong reversals
        """
        print("\n=== FINDING KEY LEVELS DYNAMICALLY ===\n")

        price_min = df['low'].min()
        price_max = df['high'].max()

        # Create price bins (zones) - use ~2% height based on analysis
        zone_height_pct = 0.017  # 1.7% average from manual analysis
        num_zones = int((price_max - price_min) / (price_min * zone_height_pct))

        print(f"Analyzing {num_zones} potential zones...")

        zone_scores = []

        # Test each potential zone
        for z in range(num_zones):
            zone_bottom = price_min + (z * price_min * zone_height_pct)
            zone_top = zone_bottom + (zone_bottom * zone_height_pct)
            zone_mid = (zone_top + zone_bottom) / 2

            touches = 0
            reversals = 0
            total_time_in_zone = 0

            for idx in range(len(df)):
                bar_high = df['high'].iloc[idx]
                bar_low = df['low'].iloc[idx]
                bar_close = df['close'].iloc[idx]

                # Check if price is in this zone
                in_zone = bar_low <= zone_top and bar_high >= zone_bottom

                if in_zone:
                    touches += 1

                    # Check how much of the bar is in the zone
                    overlap_low = max(bar_low, zone_bottom)
                    overlap_high = min(bar_high, zone_top)
                    overlap_pct = (overlap_high - overlap_low) / (bar_high - bar_low) if bar_high > bar_low else 1
                    total_time_in_zone += overlap_pct

                    # Check for reversal in next 2-3 bars
                    if idx < len(df) - 3:
                        # Determine zone role (support or resistance)
                        price_before = df['close'].iloc[max(0, idx-1)]

                        if price_before > zone_mid:
                            # Coming from above - zone is support
                            # Look for bounce UP
                            bounced = sum([df['close'].iloc[idx+j] > zone_top for j in range(1, 4)]) >= 2
                            if bounced:
                                reversals += 2  # Weight reversals higher
                        else:
                            # Coming from below - zone is resistance
                            # Look for bounce DOWN
                            bounced = sum([df['close'].iloc[idx+j] < zone_bottom for j in range(1, 4)]) >= 2
                            if bounced:
                                reversals += 2

            # Score this zone
            if touches >= 3:  # Must have at least 3 touches to be significant
                # Score based on: reversals (most important), touches, time in zone
                score = (reversals * 5) + (touches * 2) + total_time_in_zone

                zone_scores.append({
                    'bottom': zone_bottom,
                    'top': zone_top,
                    'mid': zone_mid,
                    'touches': touches,
                    'reversals': reversals,
                    'time_in_zone': total_time_in_zone,
                    'score': score
                })

        # Sort by score and get top levels
        zone_scores.sort(key=lambda x: x['score'], reverse=True)

        # Remove overlapping zones (keep highest score)
        filtered_zones = []
        for zone in zone_scores:
            is_overlap = False
            for existing in filtered_zones:
                # Check if zones overlap
                if not (zone['top'] < existing['bottom'] or zone['bottom'] > existing['top']):
                    is_overlap = True
                    break

            if not is_overlap:
                filtered_zones.append(zone)

            if len(filtered_zones) >= num_levels:
                break

        # Sort by price level (high to low)
        filtered_zones.sort(key=lambda x: x['mid'], reverse=True)

        return filtered_zones

    def print_detected_levels(self, zones):
        """Print detected key levels"""
        print(f"\n=== DETECTED KEY LEVELS (Top {len(zones)}) ===\n")

        for i, zone in enumerate(zones, 1):
            print(f"Level {i}: {zone['bottom']:.5f} - {zone['top']:.5f}")
            print(f"  Mid: {zone['mid']:.5f}")
            print(f"  Touches: {zone['touches']}")
            print(f"  Reversals: {zone['reversals']}")
            print(f"  Score: {zone['score']:.2f}")
            print()

    def compare_with_manual(self, detected_zones):
        """Compare detected levels with manual levels"""
        print("\n=== COMPARISON WITH MANUAL LEVELS ===\n")

        for i, (manual_top, manual_bottom) in enumerate(self.manual_levels, 1):
            manual_mid = (manual_top + manual_bottom) / 2

            # Find closest detected zone
            closest_zone = min(detected_zones, key=lambda z: abs(z['mid'] - manual_mid))
            distance = abs(closest_zone['mid'] - manual_mid)
            distance_pct = (distance / manual_mid) * 100

            print(f"Manual Level {i}: {manual_bottom:.5f} - {manual_top:.5f} (Mid: {manual_mid:.5f})")
            print(f"  Closest Detected: {closest_zone['bottom']:.5f} - {closest_zone['top']:.5f} (Mid: {closest_zone['mid']:.5f})")
            print(f"  Distance: {distance:.5f} ({distance_pct:.2f}%)")

            if distance_pct < 5:
                print(f"  [MATCH!]")
            else:
                print(f"  [No match]")
            print()

    def visualize_levels(self, df, detected_zones, symbol):
        """Visualize detected vs manual levels"""
        fig, ax = plt.subplots(figsize=(20, 12))

        # Plot price
        ax.plot(df['time'], df['close'], label='Close Price', color='black', linewidth=1, alpha=0.7)

        # Plot manual levels (in blue with transparency)
        for i, (top, bottom) in enumerate(self.manual_levels, 1):
            ax.axhspan(bottom, top, alpha=0.2, color='blue', label=f'Manual {i}' if i == 1 else '')
            mid = (top + bottom) / 2
            ax.text(df['time'].iloc[10], mid, f'M{i}', fontsize=12, color='blue', fontweight='bold')

        # Plot detected levels (in red with transparency)
        for i, zone in enumerate(detected_zones, 1):
            ax.axhspan(zone['bottom'], zone['top'], alpha=0.3, color='red',
                      label=f'Detected {i}' if i == 1 else '')
            ax.text(df['time'].iloc[-10], zone['mid'], f'D{i}', fontsize=12, color='red', fontweight='bold')

        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Price', fontsize=12)
        ax.set_title(f'{symbol} Monthly - Key Level Detection Analysis', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{symbol}_key_levels_analysis.png', dpi=150)
        print(f"\nChart saved as {symbol}_key_levels_analysis.png")
        plt.close()

if __name__ == "__main__":
    analyzer = KeyLevelAnalyzer()

    symbol = 'EURUSD'
    df = analyzer.get_monthly_data(symbol, num_bars=300)

    if df is not None:
        # Analyze manual levels
        analyzer.analyze_manual_levels(df)

        # Find key levels dynamically
        detected_zones = analyzer.find_price_clusters(df, num_levels=4)

        # Print results
        analyzer.print_detected_levels(detected_zones)

        # Compare with manual
        analyzer.compare_with_manual(detected_zones)

        # Visualize
        analyzer.visualize_levels(df, detected_zones, symbol)
