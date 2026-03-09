import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.signal import argrelextrema

# Initialize MT5
if not mt5.initialize():
    print("MT5 initialization failed")
    exit()

# Parameters - V4 PROFESSIONAL H&S WITH TREND + MOMENTUM + VOLUME
SYMBOL = "NZDUSD"
LOOKBACK_BARS = 240  # 20 years
SWING_ORDER = 5

# V4: Professional criteria
MIN_PROMINENCE_SHOULDERS = 8.0
MIN_PROMINENCE_HEAD = 10.0
MIN_HEAD_TO_SHOULDER_RATIO = 1.10
MIN_BARS_BETWEEN_POINTS = 5
MAX_BARS_BETWEEN_POINTS = 150
SHOULDER_SYMMETRY_TOLERANCE = 30.0
NECKLINE_TOLERANCE = 15.0

# V4: NEW - Trend confirmation parameters
SMA_PERIOD = 50  # 50-period SMA for trend detection

# V4: NEW - Neckline slope filtering
MAX_NECKLINE_SLOPE_ANGLE = 15.0  # Max degrees upward slope (horizontal/downward preferred)

# V4: NEW - RSI divergence parameters
RSI_PERIOD = 14

# V4: NEW - Volume confirmation
VOLUME_SURGE_THRESHOLD = 1.20  # 20% above average for breakout confirmation

print(f"=== V4 Head & Shoulders Detection on {SYMBOL} (PROFESSIONAL) ===\n")
print(f"Including: Trend Confirmation + Neckline Slope + RSI Divergence + Volume Analysis\n")

# Get monthly data
rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_MN1, 0, LOOKBACK_BARS)
if rates is None:
    print("Failed to get data")
    mt5.shutdown()
    exit()

# Create DataFrame
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

print(f"Loaded {len(df)} monthly bars\n")

# Extract price arrays
highs = df['high'].values
lows = df['low'].values
closes = df['close'].values
volumes = df['tick_volume'].values
times = df['time'].values

# ============= STEP 1: CALCULATE TREND INDICATOR (50 SMA) =============
print("=" * 80)
print("STEP 1: PRECEDING TREND DETECTION")
print("=" * 80)
print("Calculating 50-period SMA to confirm downtrend before Inverse H&S pattern\n")

sma_50 = np.full(len(closes), np.nan)
for i in range(SMA_PERIOD - 1, len(closes)):
    sma_50[i] = np.mean(closes[i - SMA_PERIOD + 1:i + 1])

print(f"[OK] 50-period SMA calculated for trend confirmation")
print(f"  Rule: For Inverse H&S, price must be BELOW SMA when Left Shoulder forms\n")

# ============= STEP 2: CALCULATE RSI FOR DIVERGENCE DETECTION =============
print("=" * 80)
print("STEP 2: RSI CALCULATION FOR DIVERGENCE")
print("=" * 80)
print("Calculating 14-period RSI to detect bullish divergence at Head\n")

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    rsi = np.full(len(prices), np.nan)

    for i in range(period, len(prices)):
        price_changes = np.diff(prices[i - period:i + 1])
        gains = np.where(price_changes > 0, price_changes, 0)
        losses = np.where(price_changes < 0, -price_changes, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            rsi[i] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))

    return rsi

rsi = calculate_rsi(closes, RSI_PERIOD)
print(f"[OK] 14-period RSI calculated")
print(f"  Rule: At Head (lowest price), RSI should show higher low vs Left Shoulder")
print(f"  This indicates weakening selling momentum = bullish divergence\n")

# ============= STEP 3: CALCULATE VOLUME AVERAGES =============
print("=" * 80)
print("STEP 3: VOLUME ANALYSIS PREPARATION")
print("=" * 80)
print("Calculating volume averages for breakout confirmation\n")

volume_sma_20 = np.full(len(volumes), np.nan)
for i in range(20 - 1, len(volumes)):
    volume_sma_20[i] = np.mean(volumes[i - 19:i + 1])

print(f"[OK] 20-period Volume SMA calculated")
print(f"  Rule: Right Shoulder should show LOWER volume than Left Shoulder/Head")
print(f"  Rule: Breakout should show 20%+ volume surge above recent average\n")

# Helper function to calculate prominence
def calculate_prominence(prices, idx, is_high=True):
    lookback = 20
    start_idx = max(0, idx - lookback)
    end_idx = min(len(prices) - 1, idx + lookback)

    center_price = prices[idx]

    if is_high:
        min_nearby = np.min(prices[start_idx:end_idx+1])
        prominence = (center_price - min_nearby) / center_price * 100.0
    else:
        max_nearby = np.max(prices[start_idx:end_idx+1])
        prominence = (max_nearby - center_price) / center_price * 100.0

    return prominence

# ============= STEP 4: FIND ZIGZAG SWING POINTS =============
print("=" * 80)
print("STEP 4: ZIGZAG STRUCTURAL DETECTION")
print("=" * 80)
print("Finding swing highs and lows using order-based extrema detection\n")

swing_high_indices = argrelextrema(highs, np.greater, order=SWING_ORDER)[0]
swing_low_indices = argrelextrema(lows, np.less, order=SWING_ORDER)[0]

print(f"Found {len(swing_high_indices)} swing highs and {len(swing_low_indices)} swing lows")

# Filter by prominence
prominent_highs = []
for idx in swing_high_indices:
    prominence = calculate_prominence(highs, idx, is_high=True)
    if prominence >= MIN_PROMINENCE_SHOULDERS:
        prominent_highs.append((idx, highs[idx], prominence))

prominent_lows = []
for idx in swing_low_indices:
    prominence = calculate_prominence(lows, idx, is_high=False)
    if prominence >= MIN_PROMINENCE_SHOULDERS:
        prominent_lows.append((idx, lows[idx], prominence))

print(f"[OK] After prominence filter: {len(prominent_highs)} highs, {len(prominent_lows)} lows")
print(f"  These are the candidate structural troughs for L-H-R pattern\n")

# Storage for detected patterns
inverse_hs_patterns = []
bearish_hs_patterns = []

# ============= DETECT INVERSE HEAD AND SHOULDERS (BULLISH) =============
print("=" * 80)
print("STEP 5A: INVERSE H&S PATTERN DETECTION WITH PROFESSIONAL FILTERS")
print("=" * 80)
print("Scanning all L-H-R combinations and applying multi-layer filters\n")

best_inverse_pattern = None
best_score = 0
total_combinations = 0
passed_filters = {
    'bar_spacing': 0,
    'head_depth': 0,
    'head_prominence': 0,
    'shoulder_symmetry': 0,
    'downtrend': 0,
    'neckline_slope': 0,
    'rsi_divergence': 0,
    'volume_exhaustion': 0
}

for i in range(len(prominent_lows)):
    for j in range(i + 1, len(prominent_lows)):
        for k in range(j + 1, len(prominent_lows)):
            total_combinations += 1

            ls_idx, ls_low, ls_prom = prominent_lows[i]
            h_idx, h_low, h_prom = prominent_lows[j]
            rs_idx, rs_low, rs_prom = prominent_lows[k]

            # Filter 1: Check bar spacing
            bars_ls_to_h = h_idx - ls_idx
            bars_h_to_rs = rs_idx - h_idx

            if bars_ls_to_h < MIN_BARS_BETWEEN_POINTS or bars_h_to_rs < MIN_BARS_BETWEEN_POINTS:
                continue
            if (rs_idx - ls_idx) > MAX_BARS_BETWEEN_POINTS:
                continue
            passed_filters['bar_spacing'] += 1

            # Filter 2: Head must be significantly lower than both shoulders
            if h_low >= ls_low * (1 - (MIN_HEAD_TO_SHOULDER_RATIO - 1.0)):
                continue
            if h_low >= rs_low * (1 - (MIN_HEAD_TO_SHOULDER_RATIO - 1.0)):
                continue
            passed_filters['head_depth'] += 1

            # Filter 3: Head must have high prominence
            if h_prom < MIN_PROMINENCE_HEAD:
                continue
            passed_filters['head_prominence'] += 1

            # Filter 4: Shoulders should be roughly at similar level
            shoulder_diff = abs(ls_low - rs_low) / ((ls_low + rs_low) / 2.0) * 100.0
            if shoulder_diff > SHOULDER_SYMMETRY_TOLERANCE:
                continue
            passed_filters['shoulder_symmetry'] += 1

            # ============= V4 PROFESSIONAL FILTER 1: PRECEDING DOWNTREND =============
            # Check if price was below SMA50 at Left Shoulder (confirming downtrend)
            if not np.isnan(sma_50[ls_idx]) and closes[ls_idx] >= sma_50[ls_idx]:
                continue  # Skip if not in downtrend
            passed_filters['downtrend'] += 1

            # ============= V4 PROFESSIONAL FILTER 2: NECKLINE SLOPE =============
            # Find the peaks between shoulders (neckline points)
            peak1_idx = ls_idx
            peak1_high = highs[ls_idx]
            for idx in range(ls_idx, h_idx + 1):
                if highs[idx] > peak1_high:
                    peak1_high = highs[idx]
                    peak1_idx = idx

            peak2_idx = h_idx
            peak2_high = highs[h_idx]
            for idx in range(h_idx, rs_idx + 1):
                if highs[idx] > peak2_high:
                    peak2_high = highs[idx]
                    peak2_idx = idx

            # Calculate neckline slope angle
            if peak2_idx == peak1_idx:
                neckline_angle = 0
            else:
                neckline_slope = (peak2_high - peak1_high) / (peak2_idx - peak1_idx)
                neckline_angle = np.degrees(np.arctan(neckline_slope))

            # Prefer horizontal or downward sloping necklines (avoid aggressive upward)
            if neckline_angle > MAX_NECKLINE_SLOPE_ANGLE:
                continue  # Skip if neckline slopes too aggressively upward
            passed_filters['neckline_slope'] += 1

            # Neckline peaks should be roughly at similar level
            neckline_diff = abs(peak1_high - peak2_high) / ((peak1_high + peak2_high) / 2.0) * 100.0
            if neckline_diff > NECKLINE_TOLERANCE:
                continue

            # ============= V4 PROFESSIONAL FILTER 3: RSI BULLISH DIVERGENCE =============
            # At Head (lowest price), RSI should show higher low compared to Left Shoulder
            rsi_ls = rsi[ls_idx]
            rsi_h = rsi[h_idx]

            has_rsi_divergence = False
            if not np.isnan(rsi_ls) and not np.isnan(rsi_h):
                # Price makes lower low, but RSI makes higher low = bullish divergence
                if h_low < ls_low and rsi_h > rsi_ls:
                    has_rsi_divergence = True
                    passed_filters['rsi_divergence'] += 1

            # V4: Give bonus to patterns with RSI divergence, but don't require it
            rsi_bonus = 50.0 if has_rsi_divergence else 0.0

            # ============= V4 PROFESSIONAL FILTER 4: VOLUME SIGNATURE =============
            # Right Shoulder should show lower volume than Left Shoulder/Head (exhaustion)
            vol_ls = volumes[ls_idx]
            vol_h = volumes[h_idx]
            vol_rs = volumes[rs_idx]

            has_volume_exhaustion = False
            if vol_rs < vol_ls and vol_rs < vol_h:
                has_volume_exhaustion = True
                passed_filters['volume_exhaustion'] += 1

            # V4: Give bonus to patterns with volume exhaustion
            volume_bonus = 30.0 if has_volume_exhaustion else 0.0

            # ============= V4 SCORING WITH ALL FACTORS =============
            avg_shoulder = (ls_low + rs_low) / 2.0
            head_depth = (avg_shoulder - h_low) / avg_shoulder * 100.0

            # Higher score = better pattern
            score = (head_depth * 5.0) + (h_prom * 3.0) - shoulder_diff - neckline_diff
            score += rsi_bonus  # Bonus for RSI divergence
            score += volume_bonus  # Bonus for volume exhaustion
            score -= abs(neckline_angle) * 0.5  # Penalty for sloped neckline

            if score > best_score:
                best_score = score
                best_inverse_pattern = {
                    'ls_idx': ls_idx, 'ls_price': ls_low,
                    'h_idx': h_idx, 'h_price': h_low,
                    'rs_idx': rs_idx, 'rs_price': rs_low,
                    'peak1_idx': peak1_idx, 'peak1_price': peak1_high,
                    'peak2_idx': peak2_idx, 'peak2_price': peak2_high,
                    'h_prom': h_prom,
                    'shoulder_diff': shoulder_diff,
                    'neckline_diff': neckline_diff,
                    'neckline_angle': neckline_angle,
                    'has_rsi_divergence': has_rsi_divergence,
                    'has_volume_exhaustion': has_volume_exhaustion,
                    'rsi_ls': rsi_ls if not np.isnan(rsi_ls) else None,
                    'rsi_h': rsi_h if not np.isnan(rsi_h) else None,
                    'rsi_rs': rsi[rs_idx] if not np.isnan(rsi[rs_idx]) else None,
                    'vol_ls': vol_ls,
                    'vol_h': vol_h,
                    'vol_rs': vol_rs,
                    'score': score
                }

print(f"[OK] Scanned {total_combinations} L-H-R combinations")
print(f"\nFilter Results:")
print(f"  - Bar spacing:         {passed_filters['bar_spacing']} passed")
print(f"  - Head depth:          {passed_filters['head_depth']} passed")
print(f"  - Head prominence:     {passed_filters['head_prominence']} passed")
print(f"  - Shoulder symmetry:   {passed_filters['shoulder_symmetry']} passed")
print(f"  - [V4] Downtrend:      {passed_filters['downtrend']} passed <- NEW")
print(f"  - [V4] Neckline slope: {passed_filters['neckline_slope']} passed <- NEW")
print(f"  - [V4] RSI divergence: {passed_filters['rsi_divergence']} passed <- NEW")
print(f"  - [V4] Volume exhaust: {passed_filters['volume_exhaustion']} passed <- NEW")

# Add only the BEST inverse pattern if found
if best_inverse_pattern:
    inverse_hs_patterns.append(best_inverse_pattern)

    print("\n" + "=" * 80)
    print("BEST INVERSE H&S PATTERN FOUND")
    print("=" * 80)

    ls_time = pd.Timestamp(times[best_inverse_pattern['ls_idx']])
    h_time = pd.Timestamp(times[best_inverse_pattern['h_idx']])
    rs_time = pd.Timestamp(times[best_inverse_pattern['rs_idx']])

    print(f"\n[STRUCTURE]")
    print(f"  Left Shoulder:  {ls_time.strftime('%Y-%m')} at {best_inverse_pattern['ls_price']:.2f}")
    print(f"  Head:           {h_time.strftime('%Y-%m')} at {best_inverse_pattern['h_price']:.2f} (prominence: {best_inverse_pattern['h_prom']:.2f}%)")
    print(f"  Right Shoulder: {rs_time.strftime('%Y-%m')} at {best_inverse_pattern['rs_price']:.2f}")
    print(f"  Shoulder diff:  {best_inverse_pattern['shoulder_diff']:.2f}%")

    print(f"\n[NECKLINE]")
    print(f"  Peak1: {pd.Timestamp(times[best_inverse_pattern['peak1_idx']]).strftime('%Y-%m')} at {best_inverse_pattern['peak1_price']:.2f}")
    print(f"  Peak2: {pd.Timestamp(times[best_inverse_pattern['peak2_idx']]).strftime('%Y-%m')} at {best_inverse_pattern['peak2_price']:.2f}")
    print(f"  Slope: {best_inverse_pattern['neckline_angle']:.2f}° ({'[OK] GOOD' if abs(best_inverse_pattern['neckline_angle']) < 10 else '[!] STEEP'})")

    print(f"\n[RSI DIVERGENCE]")
    if best_inverse_pattern['has_rsi_divergence']:
        print(f"  [OK] BULLISH DIVERGENCE DETECTED")
        print(f"    LS RSI: {best_inverse_pattern['rsi_ls']:.2f}")
        print(f"    H RSI:  {best_inverse_pattern['rsi_h']:.2f} (higher despite lower price)")
    else:
        print(f"  [X] No RSI divergence")

    print(f"\n[VOLUME SIGNATURE]")
    if best_inverse_pattern['has_volume_exhaustion']:
        print(f"  [OK] VOLUME EXHAUSTION DETECTED")
        print(f"    LS Vol: {best_inverse_pattern['vol_ls']:.0f}")
        print(f"    H Vol:  {best_inverse_pattern['vol_h']:.0f}")
        print(f"    RS Vol: {best_inverse_pattern['vol_rs']:.0f} (lowest = seller exhaustion)")
    else:
        print(f"  [!] No volume exhaustion")

    print(f"\n[FINAL SCORE]")
    print(f"  {best_inverse_pattern['score']:.2f}")
else:
    print("\n[X] No valid Inverse H&S pattern found")

print(f"\n{'=' * 80}\n")

# ============= DETECT BEARISH HEAD AND SHOULDERS =============
print("=" * 80)
print("STEP 5B: BEARISH H&S PATTERN DETECTION WITH PROFESSIONAL FILTERS")
print("=" * 80)
print("Scanning all L-H-R combinations and applying multi-layer filters\n")

best_bearish_pattern = None
best_score = 0
total_combinations_bearish = 0
passed_filters_bearish = {
    'bar_spacing': 0,
    'head_height': 0,
    'head_prominence': 0,
    'shoulder_symmetry': 0,
    'uptrend': 0,
    'neckline_slope': 0,
    'rsi_divergence': 0,
    'volume_exhaustion': 0
}

for i in range(len(prominent_highs)):
    for j in range(i + 1, len(prominent_highs)):
        for k in range(j + 1, len(prominent_highs)):
            total_combinations_bearish += 1

            ls_idx, ls_high, ls_prom = prominent_highs[i]
            h_idx, h_high, h_prom = prominent_highs[j]
            rs_idx, rs_high, rs_prom = prominent_highs[k]

            # Filter 1: Check bar spacing
            bars_ls_to_h = h_idx - ls_idx
            bars_h_to_rs = rs_idx - h_idx

            if bars_ls_to_h < MIN_BARS_BETWEEN_POINTS or bars_h_to_rs < MIN_BARS_BETWEEN_POINTS:
                continue
            if (rs_idx - ls_idx) > MAX_BARS_BETWEEN_POINTS:
                continue
            passed_filters_bearish['bar_spacing'] += 1

            # Filter 2: Head must be significantly higher than both shoulders
            if h_high <= ls_high * MIN_HEAD_TO_SHOULDER_RATIO:
                continue
            if h_high <= rs_high * MIN_HEAD_TO_SHOULDER_RATIO:
                continue
            passed_filters_bearish['head_height'] += 1

            # Filter 3: Head must have high prominence
            if h_prom < MIN_PROMINENCE_HEAD:
                continue
            passed_filters_bearish['head_prominence'] += 1

            # Filter 4: Shoulders should be roughly at similar level
            shoulder_diff = abs(ls_high - rs_high) / ((ls_high + rs_high) / 2.0) * 100.0
            if shoulder_diff > SHOULDER_SYMMETRY_TOLERANCE:
                continue
            passed_filters_bearish['shoulder_symmetry'] += 1

            # ============= V4 PROFESSIONAL FILTER 1: PRECEDING UPTREND =============
            # Check if price was above SMA50 at Left Shoulder (confirming uptrend)
            if not np.isnan(sma_50[ls_idx]) and closes[ls_idx] <= sma_50[ls_idx]:
                continue  # Skip if not in uptrend
            passed_filters_bearish['uptrend'] += 1

            # ============= V4 PROFESSIONAL FILTER 2: NECKLINE SLOPE =============
            # Find the valleys between shoulders (neckline points)
            valley1_idx = ls_idx
            valley1_low = lows[ls_idx]
            for idx in range(ls_idx, h_idx + 1):
                if lows[idx] < valley1_low:
                    valley1_low = lows[idx]
                    valley1_idx = idx

            valley2_idx = h_idx
            valley2_low = lows[h_idx]
            for idx in range(h_idx, rs_idx + 1):
                if lows[idx] < valley2_low:
                    valley2_low = lows[idx]
                    valley2_idx = idx

            # Calculate neckline slope angle
            if valley2_idx == valley1_idx:
                neckline_angle = 0
            else:
                neckline_slope = (valley2_low - valley1_low) / (valley2_idx - valley1_idx)
                neckline_angle = np.degrees(np.arctan(neckline_slope))

            # Prefer horizontal or upward sloping necklines (avoid aggressive downward)
            if neckline_angle < -MAX_NECKLINE_SLOPE_ANGLE:
                continue  # Skip if neckline slopes too aggressively downward
            passed_filters_bearish['neckline_slope'] += 1

            # Neckline valleys should be roughly at similar level
            neckline_diff = abs(valley1_low - valley2_low) / ((valley1_low + valley2_low) / 2.0) * 100.0
            if neckline_diff > NECKLINE_TOLERANCE:
                continue

            # ============= V4 PROFESSIONAL FILTER 3: RSI BEARISH DIVERGENCE =============
            # At Head (highest price), RSI should show lower high compared to Left Shoulder
            rsi_ls = rsi[ls_idx]
            rsi_h = rsi[h_idx]

            has_rsi_divergence = False
            if not np.isnan(rsi_ls) and not np.isnan(rsi_h):
                # Price makes higher high, but RSI makes lower high = bearish divergence
                if h_high > ls_high and rsi_h < rsi_ls:
                    has_rsi_divergence = True
                    passed_filters_bearish['rsi_divergence'] += 1

            # V4: Give bonus to patterns with RSI divergence
            rsi_bonus = 50.0 if has_rsi_divergence else 0.0

            # ============= V4 PROFESSIONAL FILTER 4: VOLUME SIGNATURE =============
            # Right Shoulder should show lower volume than Left Shoulder/Head (exhaustion)
            vol_ls = volumes[ls_idx]
            vol_h = volumes[h_idx]
            vol_rs = volumes[rs_idx]

            has_volume_exhaustion = False
            if vol_rs < vol_ls and vol_rs < vol_h:
                has_volume_exhaustion = True
                passed_filters_bearish['volume_exhaustion'] += 1

            # V4: Give bonus to patterns with volume exhaustion
            volume_bonus = 30.0 if has_volume_exhaustion else 0.0

            # ============= V4 SCORING WITH ALL FACTORS =============
            avg_shoulder = (ls_high + rs_high) / 2.0
            head_height = (h_high - avg_shoulder) / avg_shoulder * 100.0

            # Higher score = better pattern
            score = (head_height * 5.0) + (h_prom * 3.0) - shoulder_diff - neckline_diff
            score += rsi_bonus  # Bonus for RSI divergence
            score += volume_bonus  # Bonus for volume exhaustion
            score -= abs(neckline_angle) * 0.5  # Penalty for sloped neckline

            if score > best_score:
                best_score = score
                best_bearish_pattern = {
                    'ls_idx': ls_idx, 'ls_price': ls_high,
                    'h_idx': h_idx, 'h_price': h_high,
                    'rs_idx': rs_idx, 'rs_price': rs_high,
                    'valley1_idx': valley1_idx, 'valley1_price': valley1_low,
                    'valley2_idx': valley2_idx, 'valley2_price': valley2_low,
                    'h_prom': h_prom,
                    'shoulder_diff': shoulder_diff,
                    'neckline_diff': neckline_diff,
                    'neckline_angle': neckline_angle,
                    'has_rsi_divergence': has_rsi_divergence,
                    'has_volume_exhaustion': has_volume_exhaustion,
                    'rsi_ls': rsi_ls if not np.isnan(rsi_ls) else None,
                    'rsi_h': rsi_h if not np.isnan(rsi_h) else None,
                    'rsi_rs': rsi[rs_idx] if not np.isnan(rsi[rs_idx]) else None,
                    'vol_ls': vol_ls,
                    'vol_h': vol_h,
                    'vol_rs': vol_rs,
                    'score': score
                }

print(f"[OK] Scanned {total_combinations_bearish} L-H-R combinations")
print(f"\nFilter Results:")
print(f"  - Bar spacing:         {passed_filters_bearish['bar_spacing']} passed")
print(f"  - Head height:         {passed_filters_bearish['head_height']} passed")
print(f"  - Head prominence:     {passed_filters_bearish['head_prominence']} passed")
print(f"  - Shoulder symmetry:   {passed_filters_bearish['shoulder_symmetry']} passed")
print(f"  - [V4] Uptrend:        {passed_filters_bearish['uptrend']} passed <- NEW")
print(f"  - [V4] Neckline slope: {passed_filters_bearish['neckline_slope']} passed <- NEW")
print(f"  - [V4] RSI divergence: {passed_filters_bearish['rsi_divergence']} passed <- NEW")
print(f"  - [V4] Volume exhaust: {passed_filters_bearish['volume_exhaustion']} passed <- NEW")

# Add only the BEST bearish pattern if found
if best_bearish_pattern:
    bearish_hs_patterns.append(best_bearish_pattern)

    print("\n" + "=" * 80)
    print("BEST BEARISH H&S PATTERN FOUND")
    print("=" * 80)

    ls_time = pd.Timestamp(times[best_bearish_pattern['ls_idx']])
    h_time = pd.Timestamp(times[best_bearish_pattern['h_idx']])
    rs_time = pd.Timestamp(times[best_bearish_pattern['rs_idx']])

    print(f"\n[STRUCTURE]")
    print(f"  Left Shoulder:  {ls_time.strftime('%Y-%m')} at {best_bearish_pattern['ls_price']:.2f}")
    print(f"  Head:           {h_time.strftime('%Y-%m')} at {best_bearish_pattern['h_price']:.2f} (prominence: {best_bearish_pattern['h_prom']:.2f}%)")
    print(f"  Right Shoulder: {rs_time.strftime('%Y-%m')} at {best_bearish_pattern['rs_price']:.2f}")
    print(f"  Shoulder diff:  {best_bearish_pattern['shoulder_diff']:.2f}%")

    print(f"\n[NECKLINE]")
    print(f"  Valley1: {pd.Timestamp(times[best_bearish_pattern['valley1_idx']]).strftime('%Y-%m')} at {best_bearish_pattern['valley1_price']:.2f}")
    print(f"  Valley2: {pd.Timestamp(times[best_bearish_pattern['valley2_idx']]).strftime('%Y-%m')} at {best_bearish_pattern['valley2_price']:.2f}")
    print(f"  Slope: {best_bearish_pattern['neckline_angle']:.2f}° ({'[OK] GOOD' if abs(best_bearish_pattern['neckline_angle']) < 10 else '[!] STEEP'})")

    print(f"\n[RSI DIVERGENCE]")
    if best_bearish_pattern['has_rsi_divergence']:
        print(f"  [OK] BEARISH DIVERGENCE DETECTED")
        print(f"    LS RSI: {best_bearish_pattern['rsi_ls']:.2f}")
        print(f"    H RSI:  {best_bearish_pattern['rsi_h']:.2f} (lower despite higher price)")
    else:
        print(f"  [X] No RSI divergence")

    print(f"\n[VOLUME SIGNATURE]")
    if best_bearish_pattern['has_volume_exhaustion']:
        print(f"  [OK] VOLUME EXHAUSTION DETECTED")
        print(f"    LS Vol: {best_bearish_pattern['vol_ls']:.0f}")
        print(f"    H Vol:  {best_bearish_pattern['vol_h']:.0f}")
        print(f"    RS Vol: {best_bearish_pattern['vol_rs']:.0f} (lowest = buyer exhaustion)")
    else:
        print(f"  [!] No volume exhaustion")

    print(f"\n[FINAL SCORE]")
    print(f"  {best_bearish_pattern['score']:.2f}")
else:
    print("\n[X] No valid Bearish H&S pattern found")

print(f"\n{'=' * 80}\n")

# Create visualization with all indicators
fig = plt.figure(figsize=(24, 14))
gs = fig.add_gridspec(4, 1, height_ratios=[3, 1, 1, 1], hspace=0.3)

# Main price chart
ax1 = fig.add_subplot(gs[0])

# Plot candlesticks
for idx, row in df.iterrows():
    color = 'green' if row['close'] >= row['open'] else 'red'
    ax1.plot([row['time'], row['time']], [row['low'], row['high']],
            color=color, linewidth=1, alpha=0.7)
    ax1.plot([row['time'], row['time']], [row['open'], row['close']],
            color=color, linewidth=3, alpha=0.7)

# Plot 50 SMA
valid_sma = ~np.isnan(sma_50)
ax1.plot(times[valid_sma], sma_50[valid_sma], 'b-', linewidth=2, alpha=0.7, label='50 SMA (Trend)')

# Mark all prominent swing points
for idx, price, prom in prominent_lows:
    ax1.scatter(times[idx], price, color='lightblue', s=100, alpha=0.5, zorder=3,
               edgecolors='blue', linewidths=1.5)

for idx, price, prom in prominent_highs:
    ax1.scatter(times[idx], price, color='pink', s=100, alpha=0.5, zorder=3,
               edgecolors='red', linewidths=1.5)

# Draw Inverse H&S patterns
for pattern in inverse_hs_patterns:
    # Draw structure lines (L->H->R)
    ax1.plot([times[pattern['ls_idx']], times[pattern['h_idx']]],
           [pattern['ls_price'], pattern['h_price']],
           'g-', linewidth=3, alpha=0.8, zorder=6)
    ax1.plot([times[pattern['h_idx']], times[pattern['rs_idx']]],
           [pattern['h_price'], pattern['rs_price']],
           'g-', linewidth=3, alpha=0.8, zorder=6)

    # V4: DRAW NECKLINE
    ax1.plot([times[pattern['peak1_idx']], times[pattern['peak2_idx']]],
           [pattern['peak1_price'], pattern['peak2_price']],
           'y--', linewidth=2, alpha=0.9, zorder=7, label='Neckline')

    # Mark key points
    ax1.scatter([times[pattern['ls_idx']], times[pattern['h_idx']], times[pattern['rs_idx']]],
              [pattern['ls_price'], pattern['h_price'], pattern['rs_price']],
              color='lime', s=400, marker='^', zorder=8, edgecolors='darkgreen', linewidths=3)

    # Label with confirmation badges
    mid_time = times[pattern['h_idx']]
    badges = []
    if pattern['has_rsi_divergence']:
        badges.append("RSI[OK]")
    if pattern['has_volume_exhaustion']:
        badges.append("VOL[OK]")

    label_text = f"INVERSE H&S"
    if badges:
        label_text += f"\n{' '.join(badges)}"

    ax1.text(mid_time, pattern['h_price'] - 10, label_text, fontsize=11, ha='center',
           va='top', color='white', fontweight='bold',
           bbox=dict(boxstyle='round', facecolor='green', alpha=0.9))

# Draw Bearish H&S patterns
for pattern in bearish_hs_patterns:
    # Draw structure lines (L->H->R)
    ax1.plot([times[pattern['ls_idx']], times[pattern['h_idx']]],
           [pattern['ls_price'], pattern['h_price']],
           'r-', linewidth=3, alpha=0.8, zorder=6)
    ax1.plot([times[pattern['h_idx']], times[pattern['rs_idx']]],
           [pattern['h_price'], pattern['rs_price']],
           'r-', linewidth=3, alpha=0.8, zorder=6)

    # V4: DRAW NECKLINE
    ax1.plot([times[pattern['valley1_idx']], times[pattern['valley2_idx']]],
           [pattern['valley1_price'], pattern['valley2_price']],
           'orange', linestyle='--', linewidth=2, alpha=0.9, zorder=7, label='Neckline (Bearish)')

    # Mark key points
    ax1.scatter([times[pattern['ls_idx']], times[pattern['h_idx']], times[pattern['rs_idx']]],
              [pattern['ls_price'], pattern['h_price'], pattern['rs_price']],
              color='red', s=400, marker='v', zorder=8, edgecolors='darkred', linewidths=3)

    # Label with confirmation badges
    mid_time = times[pattern['h_idx']]
    badges = []
    if pattern['has_rsi_divergence']:
        badges.append("RSI[OK]")
    if pattern['has_volume_exhaustion']:
        badges.append("VOL[OK]")

    label_text = f"BEARISH H&S"
    if badges:
        label_text += f"\n{' '.join(badges)}"

    ax1.text(mid_time, pattern['h_price'] + 10, label_text, fontsize=11, ha='center',
           va='bottom', color='white', fontweight='bold',
           bbox=dict(boxstyle='round', facecolor='red', alpha=0.9))

ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=12))
ax1.set_ylabel('Price', fontsize=12)
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)
ax1.set_title(f'{SYMBOL} - V4 Head & Shoulders Detection (PROFESSIONAL)\nWith Trend + Neckline Slope + RSI Divergence + Volume Analysis',
             fontsize=14, fontweight='bold')

# RSI subplot
ax2 = fig.add_subplot(gs[1], sharex=ax1)
valid_rsi = ~np.isnan(rsi)
ax2.plot(times[valid_rsi], rsi[valid_rsi], 'purple', linewidth=1.5, label='RSI(14)')
ax2.axhline(70, color='r', linestyle='--', alpha=0.5, linewidth=1)
ax2.axhline(30, color='g', linestyle='--', alpha=0.5, linewidth=1)
ax2.set_ylabel('RSI', fontsize=10)
ax2.set_ylim(0, 100)
ax2.legend(loc='upper left', fontsize=9)
ax2.grid(True, alpha=0.3)

# Mark RSI at pattern points
for pattern in inverse_hs_patterns:
    if pattern['rsi_ls'] is not None:
        ax2.scatter([times[pattern['ls_idx']], times[pattern['h_idx']], times[pattern['rs_idx']]],
                  [pattern['rsi_ls'], pattern['rsi_h'], pattern['rsi_rs']],
                  color='lime', s=200, marker='o', zorder=5, edgecolors='darkgreen', linewidths=2)

        # Draw divergence line if present
        if pattern['has_rsi_divergence']:
            ax2.plot([times[pattern['ls_idx']], times[pattern['h_idx']]],
                   [pattern['rsi_ls'], pattern['rsi_h']],
                   'g--', linewidth=2, alpha=0.8, label='Bullish Divergence')

# Mark RSI at bearish pattern points
for pattern in bearish_hs_patterns:
    if pattern['rsi_ls'] is not None:
        ax2.scatter([times[pattern['ls_idx']], times[pattern['h_idx']], times[pattern['rs_idx']]],
                  [pattern['rsi_ls'], pattern['rsi_h'], pattern['rsi_rs']],
                  color='red', s=200, marker='o', zorder=5, edgecolors='darkred', linewidths=2)

        # Draw divergence line if present
        if pattern['has_rsi_divergence']:
            ax2.plot([times[pattern['ls_idx']], times[pattern['h_idx']]],
                   [pattern['rsi_ls'], pattern['rsi_h']],
                   'r--', linewidth=2, alpha=0.8, label='Bearish Divergence')

# Volume subplot
ax3 = fig.add_subplot(gs[2], sharex=ax1)
ax3.bar(times, volumes, color='gray', alpha=0.5, width=20, label='Volume')
valid_vol_sma = ~np.isnan(volume_sma_20)
ax3.plot(times[valid_vol_sma], volume_sma_20[valid_vol_sma], 'orange', linewidth=1.5, label='Vol SMA(20)')
ax3.set_ylabel('Volume', fontsize=10)
ax3.legend(loc='upper left', fontsize=9)
ax3.grid(True, alpha=0.3)

# Mark volumes at pattern points
for pattern in inverse_hs_patterns:
    ax3.scatter([times[pattern['ls_idx']], times[pattern['h_idx']], times[pattern['rs_idx']]],
              [pattern['vol_ls'], pattern['vol_h'], pattern['vol_rs']],
              color='lime', s=200, marker='o', zorder=5, edgecolors='darkgreen', linewidths=2)

for pattern in bearish_hs_patterns:
    ax3.scatter([times[pattern['ls_idx']], times[pattern['h_idx']], times[pattern['rs_idx']]],
              [pattern['vol_ls'], pattern['vol_h'], pattern['vol_rs']],
              color='red', s=200, marker='o', zorder=5, edgecolors='darkred', linewidths=2)

# Trend indicator subplot
ax4 = fig.add_subplot(gs[3], sharex=ax1)
price_vs_sma = closes - sma_50
ax4.plot(times, price_vs_sma, 'b-', linewidth=1.5, label='Price - SMA50')
ax4.axhline(0, color='black', linestyle='-', alpha=0.3, linewidth=1)
ax4.fill_between(times, 0, price_vs_sma, where=(price_vs_sma < 0), color='red', alpha=0.3, label='Below SMA (Downtrend)')
ax4.fill_between(times, 0, price_vs_sma, where=(price_vs_sma > 0), color='green', alpha=0.3, label='Above SMA (Uptrend)')
ax4.set_ylabel('Trend', fontsize=10)
ax4.set_xlabel('Date', fontsize=12)
ax4.legend(loc='upper left', fontsize=9)
ax4.grid(True, alpha=0.3)

plt.setp(ax1.get_xticklabels(), rotation=45)
plt.setp(ax2.get_xticklabels(), visible=False)
plt.setp(ax3.get_xticklabels(), visible=False)
plt.setp(ax4.get_xticklabels(), rotation=45)

plt.tight_layout()

output_path = r'C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\head_shoulders_v4_detection.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"Chart saved to: {output_path}")

mt5.shutdown()
plt.close()
