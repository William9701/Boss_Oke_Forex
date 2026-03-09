import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.signal import argrelextrema
import pywt
import sys

# Initialize MT5
if not mt5.initialize():
    print("MT5 initialization failed")
    exit()

# Parameters - V16 WITH POST-SNAP HEAD VALIDATION
SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "AUDUSD"
LOOKBACK_BARS = 240  # 20 years
SWING_ORDER = 5  # Keep at 5 for clean swing detection

# V9: Professional criteria
MIN_PROMINENCE_SHOULDERS = 6.0
MIN_PROMINENCE_HEAD = 10.0
MIN_HEAD_TO_SHOULDER_RATIO = 1.10
MIN_BARS_BETWEEN_POINTS = 5
MAX_BARS_BETWEEN_POINTS = 150
SHOULDER_SYMMETRY_TOLERANCE = 50.0
NECKLINE_TOLERANCE = 15.0

# Trend confirmation parameters
SMA_PERIOD = 50

# Neckline slope filtering
MAX_NECKLINE_SLOPE_ANGLE = 15.0

# RSI divergence parameters
RSI_PERIOD = 14

# Volume confirmation
VOLUME_SURGE_THRESHOLD = 1.20

# Wavelet denoising parameters
WAVELET_TYPE = 'db4'
WAVELET_LEVEL = 1

# Neckline extension
NECKLINE_EXTENSION_BARS = 50

print(f"=== V16 Head & Shoulders Detection on {SYMBOL} (POST-SNAP VALIDATION) ===\n")
print(f"Including: ZigZag + Proper Head & Shoulder Detection\n")
print(f"V16: Detect > Snap > Validate head is highest/lowest > Re-adjust if needed\n")

# Get data from MT5
rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_MN1, 0, LOOKBACK_BARS)
if rates is None or len(rates) == 0:
    print(f"Failed to get data for {SYMBOL}")
    mt5.shutdown()
    exit()

df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

times = df['time'].values
opens = df['open'].values
highs = df['high'].values
lows = df['low'].values
closes = df['close'].values
volumes = df['tick_volume'].values

print(f"Loaded {len(df)} monthly bars\n")

# ============= STEP 0: WAVELET DENOISING =============
print("=" * 80)
print("STEP 0: WAVELET DENOISING (84.5% ACCURACY)")
print("=" * 80)

coeffs_high = pywt.wavedec(highs, WAVELET_TYPE, level=WAVELET_LEVEL)
coeffs_low = pywt.wavedec(lows, WAVELET_TYPE, level=WAVELET_LEVEL)
coeffs_close = pywt.wavedec(closes, WAVELET_TYPE, level=WAVELET_LEVEL)

sigma = np.median(np.abs(coeffs_high[-1])) / 0.6745
threshold = sigma * np.sqrt(2 * np.log(len(highs)))

coeffs_high_thresh = [coeffs_high[0]] + [pywt.threshold(c, threshold, mode='soft') for c in coeffs_high[1:]]
coeffs_low_thresh = [coeffs_low[0]] + [pywt.threshold(c, threshold, mode='soft') for c in coeffs_low[1:]]
coeffs_close_thresh = [coeffs_close[0]] + [pywt.threshold(c, threshold, mode='soft') for c in coeffs_close[1:]]

highs_denoised = pywt.waverec(coeffs_high_thresh, WAVELET_TYPE)[:len(highs)]
lows_denoised = pywt.waverec(coeffs_low_thresh, WAVELET_TYPE)[:len(lows)]
closes_denoised = pywt.waverec(coeffs_close_thresh, WAVELET_TYPE)[:len(closes)]

print(f"[OK] Wavelet denoising applied\n")

# ============= STEP 1: CALCULATE SMA FOR TREND =============
print("=" * 80)
print("STEP 1: PRECEDING TREND DETECTION")
print("=" * 80)

sma_50 = np.full(len(closes_denoised), np.nan)
for i in range(SMA_PERIOD - 1, len(closes_denoised)):
    sma_50[i] = np.mean(closes_denoised[i - SMA_PERIOD + 1:i + 1])

print(f"[OK] 50-period SMA calculated\n")

# ============= STEP 2: CALCULATE RSI =============
print("=" * 80)
print("STEP 2: RSI CALCULATION FOR DIVERGENCE")
print("=" * 80)

def calculate_rsi(prices, period):
    rsi = np.full(len(prices), np.nan)
    for i in range(period, len(prices)):
        gains = []
        losses = []
        for j in range(1, period + 1):
            change = prices[i - j + 1] - prices[i - j]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            rsi[i] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))
    return rsi

rsi = calculate_rsi(closes_denoised, RSI_PERIOD)
print(f"[OK] 14-period RSI calculated\n")

# ============= STEP 3: CALCULATE VOLUME AVERAGES =============
print("=" * 80)
print("STEP 3: VOLUME ANALYSIS PREPARATION")
print("=" * 80)

volume_sma_20 = np.full(len(volumes), np.nan)
for i in range(20 - 1, len(volumes)):
    volume_sma_20[i] = np.mean(volumes[i - 19:i + 1])

print(f"[OK] 20-period Volume SMA calculated\n")

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

swing_high_indices = argrelextrema(highs_denoised, np.greater, order=SWING_ORDER)[0]
swing_low_indices = argrelextrema(lows_denoised, np.less, order=SWING_ORDER)[0]

print(f"Found {len(swing_high_indices)} swing highs and {len(swing_low_indices)} swing lows")

# Store ALL swing points for ZigZag visualization
all_swing_highs = []
for idx in swing_high_indices:
    prominence = calculate_prominence(highs_denoised, idx, is_high=True)
    all_swing_highs.append((idx, highs_denoised[idx], prominence))

all_swing_lows = []
for idx in swing_low_indices:
    prominence = calculate_prominence(lows_denoised, idx, is_high=False)
    all_swing_lows.append((idx, lows_denoised[idx], prominence))

# Filter by prominence for H&S detection
prominent_highs = [(idx, price, prom) for idx, price, prom in all_swing_highs if prom >= MIN_PROMINENCE_SHOULDERS]
prominent_lows = [(idx, price, prom) for idx, price, prom in all_swing_lows if prom >= MIN_PROMINENCE_SHOULDERS]

print(f"[OK] After prominence filter: {len(prominent_highs)} highs, {len(prominent_lows)} lows for H&S detection")
print(f"[V9] Total swing points for ZigZag: {len(all_swing_highs)} highs + {len(all_swing_lows)} lows\n")

# Storage for detected patterns
inverse_hs_patterns = []
bearish_hs_patterns = []

# ============= DETECT INVERSE HEAD AND SHOULDERS (BULLISH) =============
print("=" * 80)
print("STEP 5A: INVERSE H&S PATTERN DETECTION (V16)")
print("=" * 80)

best_inverse_pattern = None
best_score = 0

# V13: Right shoulder must be NEXT swing after head (within 1-3 positions)
MAX_SHOULDER_DISTANCE = 3  # Only check next 1-3 swings

for i, (ls_idx, ls_low, ls_prom) in enumerate(prominent_lows[:-2]):
    for j, (h_idx, h_low, h_prom) in enumerate(prominent_lows[i+1:-1], start=i+1):
        # V13: Only check next 1-3 swings after head for right shoulder
        max_k = min(j + 1 + MAX_SHOULDER_DISTANCE, len(prominent_lows))
        for k in range(j+1, max_k):
            rs_idx, rs_low, rs_prom = prominent_lows[k]

            if (h_idx - ls_idx) < MIN_BARS_BETWEEN_POINTS:
                continue
            if (rs_idx - h_idx) < MIN_BARS_BETWEEN_POINTS:
                continue
            if (rs_idx - ls_idx) > MAX_BARS_BETWEEN_POINTS:
                continue

            if h_low >= ls_low / MIN_HEAD_TO_SHOULDER_RATIO:
                continue
            if h_low >= rs_low / MIN_HEAD_TO_SHOULDER_RATIO:
                continue

            if h_prom < MIN_PROMINENCE_HEAD:
                continue

            # V9: Head must be LOWER than BOTH shoulders (strict but simple)
            if h_low >= ls_low or h_low >= rs_low:
                continue

            shoulder_diff = abs(ls_low - rs_low) / ((ls_low + rs_low) / 2.0) * 100.0
            if shoulder_diff > SHOULDER_SYMMETRY_TOLERANCE:
                continue

            if not np.isnan(sma_50[ls_idx]) and closes_denoised[ls_idx] >= sma_50[ls_idx]:
                continue

            peak1_idx = ls_idx
            peak1_high = highs_denoised[ls_idx]
            for idx in range(ls_idx, h_idx + 1):
                if highs_denoised[idx] > peak1_high:
                    peak1_high = highs_denoised[idx]
                    peak1_idx = idx

            peak2_idx = h_idx
            peak2_high = highs_denoised[h_idx]
            for idx in range(h_idx, rs_idx + 1):
                if highs_denoised[idx] > peak2_high:
                    peak2_high = highs_denoised[idx]
                    peak2_idx = idx

            neckline_angle = 0
            if peak2_idx != peak1_idx:
                slope = (peak2_high - peak1_high) / (peak2_idx - peak1_idx)
                neckline_angle = np.arctan(slope) * 180.0 / np.pi

            if neckline_angle > MAX_NECKLINE_SLOPE_ANGLE:
                continue

            neckline_diff = abs(peak1_high - peak2_high) / ((peak1_high + peak2_high) / 2.0) * 100.0
            if neckline_diff > NECKLINE_TOLERANCE:
                continue

            has_rsi_div = False
            rsi_ls = rsi[ls_idx]
            rsi_h = rsi[h_idx]
            rsi_rs = rsi[rs_idx]
            if not np.isnan(rsi_ls) and not np.isnan(rsi_h):
                if h_low < ls_low and rsi_h > rsi_ls:
                    has_rsi_div = True

            has_vol_exhaust = False
            if volumes[rs_idx] < volumes[ls_idx] and volumes[rs_idx] < volumes[h_idx]:
                has_vol_exhaust = True

            avg_shoulder = (ls_low + rs_low) / 2.0
            head_height = (avg_shoulder - h_low) / avg_shoulder * 100.0

            score = (head_height * 5.0) + (h_prom * 3.0)
            score -= shoulder_diff * 0.3
            score -= neckline_diff * 5.0
            if has_rsi_div:
                score += 50.0
            if has_vol_exhaust:
                score += 30.0
            score -= abs(neckline_angle) * 3.0

            if score > best_score:
                best_score = score
                best_inverse_pattern = {
                    'ls_idx': ls_idx,
                    'h_idx': h_idx,
                    'rs_idx': rs_idx,
                    'peak1_idx': peak1_idx,
                    'peak1_price': peak1_high,
                    'peak2_idx': peak2_idx,
                    'peak2_price': peak2_high,
                    'has_rsi_divergence': has_rsi_div,
                    'has_volume_exhaustion': has_vol_exhaust,
                    'score': score,
                    'shoulder_diff': shoulder_diff,
                    'neckline_diff': neckline_diff,
                    'neckline_angle': neckline_angle
                }

if best_inverse_pattern:
    # V15: SNAP shoulders to adjacent swings in the prominent_lows list
    print(f"[OK] Found Inverse H&S pattern (Score: {best_score:.2f})")

    # Find the head index in the prominent_lows list
    head_idx_in_list = None
    for idx, (swing_idx, swing_low, swing_prom) in enumerate(prominent_lows):
        if swing_idx == best_inverse_pattern['h_idx']:
            head_idx_in_list = idx
            break

    if head_idx_in_list is not None and head_idx_in_list > 0 and head_idx_in_list < len(prominent_lows) - 1:
        # V15: Snap left shoulder to PREVIOUS swing
        new_ls_idx, new_ls_low, new_ls_prom = prominent_lows[head_idx_in_list - 1]

        # V15: Snap right shoulder to NEXT swing
        new_rs_idx, new_rs_low, new_rs_prom = prominent_lows[head_idx_in_list + 1]

        print(f"[V16] SNAPPING shoulders to adjacent swings:")
        print(f"      Original LS: idx={best_inverse_pattern['ls_idx']}, New LS: idx={new_ls_idx}")
        print(f"      Original RS: idx={best_inverse_pattern['rs_idx']}, New RS: idx={new_rs_idx}")

        # Update the pattern with snapped shoulders
        best_inverse_pattern['ls_idx'] = new_ls_idx
        best_inverse_pattern['rs_idx'] = new_rs_idx

        # V16: POST-SNAP VALIDATION - Head must be LOWEST among L-H-R
        h_low = lows_denoised[best_inverse_pattern['h_idx']]
        ls_low = lows_denoised[new_ls_idx]
        rs_low = lows_denoised[new_rs_idx]

        print(f"[V16] POST-SNAP VALIDATION:")
        print(f"      LS low: {ls_low:.5f}, H low: {h_low:.5f}, RS low: {rs_low:.5f}")

        # Check if head is actually the lowest
        if h_low < ls_low and h_low < rs_low:
            print(f"      [OK] Head is LOWEST - Pattern valid!")
        else:
            # Head is NOT the lowest - need to re-adjust
            print(f"      [X] Head is NOT lowest - RE-ADJUSTING...")

            # Find which is actually the lowest
            if ls_low < h_low and ls_low < rs_low:
                # Left shoulder is actually the head
                print(f"      -> Left shoulder ({ls_low:.5f}) is lowest - making it the new head")
                new_head_idx_in_list = head_idx_in_list - 1
            elif rs_low < h_low and rs_low < ls_low:
                # Right shoulder is actually the head
                print(f"      -> Right shoulder ({rs_low:.5f}) is lowest - making it the new head")
                new_head_idx_in_list = head_idx_in_list + 1
            else:
                new_head_idx_in_list = head_idx_in_list  # Shouldn't happen but safeguard

            # Re-adjust with new head
            if new_head_idx_in_list > 0 and new_head_idx_in_list < len(prominent_lows) - 1:
                # New head
                new_h_idx, new_h_low, new_h_prom = prominent_lows[new_head_idx_in_list]

                # New shoulders (adjacent to new head)
                new_ls_idx, new_ls_low, new_ls_prom = prominent_lows[new_head_idx_in_list - 1]
                new_rs_idx, new_rs_low, new_rs_prom = prominent_lows[new_head_idx_in_list + 1]

                print(f"      -> New pattern: LS={new_ls_idx}, H={new_h_idx}, RS={new_rs_idx}")

                # Update pattern
                best_inverse_pattern['ls_idx'] = new_ls_idx
                best_inverse_pattern['h_idx'] = new_h_idx
                best_inverse_pattern['rs_idx'] = new_rs_idx

        # Recalculate neckline with final (potentially re-adjusted) shoulders
        final_ls_idx = best_inverse_pattern['ls_idx']
        final_h_idx = best_inverse_pattern['h_idx']
        final_rs_idx = best_inverse_pattern['rs_idx']

        peak1_idx = final_ls_idx
        peak1_high = highs_denoised[final_ls_idx]
        for idx in range(final_ls_idx, final_h_idx + 1):
            if highs_denoised[idx] > peak1_high:
                peak1_high = highs_denoised[idx]
                peak1_idx = idx

        peak2_idx = final_h_idx
        peak2_high = highs_denoised[final_h_idx]
        for idx in range(final_h_idx, final_rs_idx + 1):
            if highs_denoised[idx] > peak2_high:
                peak2_high = highs_denoised[idx]
                peak2_idx = idx

        best_inverse_pattern['peak1_idx'] = peak1_idx
        best_inverse_pattern['peak1_price'] = peak1_high
        best_inverse_pattern['peak2_idx'] = peak2_idx
        best_inverse_pattern['peak2_price'] = peak2_high

    inverse_hs_patterns.append(best_inverse_pattern)
    print()
else:
    print("[X] No Inverse H&S pattern found\n")

# ============= DETECT BEARISH HEAD AND SHOULDERS =============
print("=" * 80)
print("STEP 5B: BEARISH H&S PATTERN DETECTION (V16)")
print("=" * 80)

best_bearish_pattern = None
best_score = 0

for i, (ls_idx, ls_high, ls_prom) in enumerate(prominent_highs[:-2]):
    for j, (h_idx, h_high, h_prom) in enumerate(prominent_highs[i+1:-1], start=i+1):
        # V13: Only check next 1-3 swings after head for right shoulder
        max_k = min(j + 1 + MAX_SHOULDER_DISTANCE, len(prominent_highs))
        for k in range(j+1, max_k):
            rs_idx, rs_high, rs_prom = prominent_highs[k]

            if (h_idx - ls_idx) < MIN_BARS_BETWEEN_POINTS:
                continue
            if (rs_idx - h_idx) < MIN_BARS_BETWEEN_POINTS:
                continue
            if (rs_idx - ls_idx) > MAX_BARS_BETWEEN_POINTS:
                continue

            if h_high <= ls_high * MIN_HEAD_TO_SHOULDER_RATIO:
                continue
            if h_high <= rs_high * MIN_HEAD_TO_SHOULDER_RATIO:
                continue

            if h_prom < MIN_PROMINENCE_HEAD:
                continue

            # V9: Head must be HIGHER than BOTH shoulders (strict but simple)
            if h_high <= ls_high or h_high <= rs_high:
                continue

            shoulder_diff = abs(ls_high - rs_high) / ((ls_high + rs_high) / 2.0) * 100.0
            if shoulder_diff > SHOULDER_SYMMETRY_TOLERANCE:
                continue

            if not np.isnan(sma_50[ls_idx]) and closes_denoised[ls_idx] <= sma_50[ls_idx]:
                continue

            valley1_idx = ls_idx
            valley1_low = lows_denoised[ls_idx]
            for idx in range(ls_idx, h_idx + 1):
                if lows_denoised[idx] < valley1_low:
                    valley1_low = lows_denoised[idx]
                    valley1_idx = idx

            valley2_idx = h_idx
            valley2_low = lows_denoised[h_idx]
            for idx in range(h_idx, rs_idx + 1):
                if lows_denoised[idx] < valley2_low:
                    valley2_low = lows_denoised[idx]
                    valley2_idx = idx

            neckline_angle = 0
            if valley2_idx != valley1_idx:
                slope = (valley2_low - valley1_low) / (valley2_idx - valley1_idx)
                neckline_angle = np.arctan(slope) * 180.0 / np.pi

            if neckline_angle < -MAX_NECKLINE_SLOPE_ANGLE:
                continue

            neckline_diff = abs(valley1_low - valley2_low) / ((valley1_low + valley2_low) / 2.0) * 100.0
            if neckline_diff > NECKLINE_TOLERANCE:
                continue

            has_rsi_div = False
            rsi_ls = rsi[ls_idx]
            rsi_h = rsi[h_idx]
            rsi_rs = rsi[rs_idx]
            if not np.isnan(rsi_ls) and not np.isnan(rsi_h):
                if h_high > ls_high and rsi_h < rsi_ls:
                    has_rsi_div = True

            has_vol_exhaust = False
            if volumes[rs_idx] < volumes[ls_idx] and volumes[rs_idx] < volumes[h_idx]:
                has_vol_exhaust = True

            avg_shoulder = (ls_high + rs_high) / 2.0
            head_height = (h_high - avg_shoulder) / avg_shoulder * 100.0

            score = (head_height * 5.0) + (h_prom * 3.0)
            score -= shoulder_diff * 0.3
            score -= neckline_diff * 5.0
            if has_rsi_div:
                score += 50.0
            if has_vol_exhaust:
                score += 30.0
            score -= abs(neckline_angle) * 3.0

            if score > best_score:
                best_score = score
                best_bearish_pattern = {
                    'ls_idx': ls_idx,
                    'h_idx': h_idx,
                    'rs_idx': rs_idx,
                    'valley1_idx': valley1_idx,
                    'valley1_price': valley1_low,
                    'valley2_idx': valley2_idx,
                    'valley2_price': valley2_low,
                    'has_rsi_divergence': has_rsi_div,
                    'has_volume_exhaustion': has_vol_exhaust,
                    'score': score,
                    'shoulder_diff': shoulder_diff,
                    'neckline_diff': neckline_diff,
                    'neckline_angle': neckline_angle
                }

if best_bearish_pattern:
    # V15: SNAP shoulders to adjacent swings in the prominent_highs list
    print(f"[OK] Found Bearish H&S pattern (Score: {best_score:.2f})")

    # Find the head index in the prominent_highs list
    head_idx_in_list = None
    for idx, (swing_idx, swing_high, swing_prom) in enumerate(prominent_highs):
        if swing_idx == best_bearish_pattern['h_idx']:
            head_idx_in_list = idx
            break

    if head_idx_in_list is not None and head_idx_in_list > 0 and head_idx_in_list < len(prominent_highs) - 1:
        # V15: Snap left shoulder to PREVIOUS swing
        new_ls_idx, new_ls_high, new_ls_prom = prominent_highs[head_idx_in_list - 1]

        # V15: Snap right shoulder to NEXT swing
        new_rs_idx, new_rs_high, new_rs_prom = prominent_highs[head_idx_in_list + 1]

        print(f"[V16] SNAPPING shoulders to adjacent swings:")
        print(f"      Original LS: idx={best_bearish_pattern['ls_idx']}, New LS: idx={new_ls_idx}")
        print(f"      Original RS: idx={best_bearish_pattern['rs_idx']}, New RS: idx={new_rs_idx}")

        # Update the pattern with snapped shoulders
        best_bearish_pattern['ls_idx'] = new_ls_idx
        best_bearish_pattern['rs_idx'] = new_rs_idx

        # V16: POST-SNAP VALIDATION - Head must be HIGHEST among L-H-R
        h_high = highs_denoised[best_bearish_pattern['h_idx']]
        ls_high = highs_denoised[new_ls_idx]
        rs_high = highs_denoised[new_rs_idx]

        print(f"[V16] POST-SNAP VALIDATION:")
        print(f"      LS high: {ls_high:.5f}, H high: {h_high:.5f}, RS high: {rs_high:.5f}")

        # Check if head is actually the highest
        if h_high > ls_high and h_high > rs_high:
            print(f"      [OK] Head is HIGHEST - Pattern valid!")
        else:
            # Head is NOT the highest - need to re-adjust
            print(f"      [X] Head is NOT highest - RE-ADJUSTING...")

            # Find which is actually the highest
            if ls_high > h_high and ls_high > rs_high:
                # Left shoulder is actually the head
                print(f"      -> Left shoulder ({ls_high:.5f}) is highest - making it the new head")
                new_head_idx_in_list = head_idx_in_list - 1
            elif rs_high > h_high and rs_high > ls_high:
                # Right shoulder is actually the head
                print(f"      -> Right shoulder ({rs_high:.5f}) is highest - making it the new head")
                new_head_idx_in_list = head_idx_in_list + 1
            else:
                new_head_idx_in_list = head_idx_in_list  # Shouldn't happen but safeguard

            # Re-adjust with new head
            if new_head_idx_in_list > 0 and new_head_idx_in_list < len(prominent_highs) - 1:
                # New head
                new_h_idx, new_h_high, new_h_prom = prominent_highs[new_head_idx_in_list]

                # New shoulders (adjacent to new head)
                new_ls_idx, new_ls_high, new_ls_prom = prominent_highs[new_head_idx_in_list - 1]
                new_rs_idx, new_rs_high, new_rs_prom = prominent_highs[new_head_idx_in_list + 1]

                print(f"      -> New pattern: LS={new_ls_idx}, H={new_h_idx}, RS={new_rs_idx}")

                # Update pattern
                best_bearish_pattern['ls_idx'] = new_ls_idx
                best_bearish_pattern['h_idx'] = new_h_idx
                best_bearish_pattern['rs_idx'] = new_rs_idx

        # Recalculate neckline with final (potentially re-adjusted) shoulders
        final_ls_idx = best_bearish_pattern['ls_idx']
        final_h_idx = best_bearish_pattern['h_idx']
        final_rs_idx = best_bearish_pattern['rs_idx']

        valley1_idx = final_ls_idx
        valley1_low = lows_denoised[final_ls_idx]
        for idx in range(final_ls_idx, final_h_idx + 1):
            if lows_denoised[idx] < valley1_low:
                valley1_low = lows_denoised[idx]
                valley1_idx = idx

        valley2_idx = final_h_idx
        valley2_low = lows_denoised[final_h_idx]
        for idx in range(final_h_idx, final_rs_idx + 1):
            if lows_denoised[idx] < valley2_low:
                valley2_low = lows_denoised[idx]
                valley2_idx = idx

        best_bearish_pattern['valley1_idx'] = valley1_idx
        best_bearish_pattern['valley1_price'] = valley1_low
        best_bearish_pattern['valley2_idx'] = valley2_idx
        best_bearish_pattern['valley2_price'] = valley2_low

        print(f"[V16] NECKLINE after re-adjustment:")
        print(f"      Valley1: idx={valley1_idx}, price={valley1_low:.5f}")
        print(f"      Valley2: idx={valley2_idx}, price={valley2_low:.5f}")

    bearish_hs_patterns.append(best_bearish_pattern)
    print()
else:
    print("[X] No Bearish H&S pattern found\n")

# ============= V9: VISUALIZATION WITH ZIGZAG =============
print("=" * 80)
print("STEP 6: CHART VISUALIZATION WITH ZIGZAG OVERLAY")
print("=" * 80)

fig = plt.figure(figsize=(20, 12))
gs = fig.add_gridspec(4, 1, height_ratios=[3, 1, 1, 1], hspace=0.05)

# Main price chart
ax1 = fig.add_subplot(gs[0])
ax1.plot(times, closes, 'lightgray', linewidth=1, alpha=0.5, label='Price (Raw)')
ax1.plot(times, closes_denoised, 'black', linewidth=1.5, alpha=0.7, label='Price (Denoised)')

# V9: DRAW ZIGZAG
all_swings = []
for idx, price, prom in all_swing_highs:
    all_swings.append((idx, highs_denoised[idx], 'high', prom))
for idx, price, prom in all_swing_lows:
    all_swings.append((idx, lows_denoised[idx], 'low', prom))

all_swings.sort(key=lambda x: x[0])

if len(all_swings) > 0:
    zigzag_times = [times[s[0]] for s in all_swings]
    zigzag_prices = [s[1] for s in all_swings]

    ax1.plot(zigzag_times, zigzag_prices, 'cyan', linewidth=2, alpha=0.8,
             label='ZigZag Pattern', zorder=4, linestyle='-', marker='o', markersize=5)

    high_times = [times[idx] for idx, price, typ, prom in all_swings if typ == 'high']
    high_prices = [price for idx, price, typ, prom in all_swings if typ == 'high']
    low_times = [times[idx] for idx, price, typ, prom in all_swings if typ == 'low']
    low_prices = [price for idx, price, typ, prom in all_swings if typ == 'low']

    ax1.scatter(high_times, high_prices, color='blue', s=100, marker='v',
                zorder=5, alpha=0.6, edgecolors='darkblue', linewidths=1.5, label='Swing Highs')
    ax1.scatter(low_times, low_prices, color='orange', s=100, marker='^',
                zorder=5, alpha=0.6, edgecolors='darkorange', linewidths=1.5, label='Swing Lows')

# SMA trend
valid_sma = ~np.isnan(sma_50)
ax1.plot(times[valid_sma], sma_50[valid_sma], 'purple', linewidth=2, alpha=0.6, label='50 SMA (Trend)')

# Draw Inverse H&S patterns
for pattern in inverse_hs_patterns:
    ls_idx = pattern['ls_idx']
    h_idx = pattern['h_idx']
    rs_idx = pattern['rs_idx']

    ax1.plot([times[ls_idx], times[h_idx]], [lows_denoised[ls_idx], lows_denoised[h_idx]],
           'lime', linewidth=4, alpha=0.9, zorder=6)
    ax1.plot([times[h_idx], times[rs_idx]], [lows_denoised[h_idx], lows_denoised[rs_idx]],
           'lime', linewidth=4, alpha=0.9, zorder=6)

    extension_idx = min(rs_idx + NECKLINE_EXTENSION_BARS, len(times) - 1)
    extension_time = times[extension_idx]

    if pattern['peak2_idx'] != pattern['peak1_idx']:
        slope = (pattern['peak2_price'] - pattern['peak1_price']) / (pattern['peak2_idx'] - pattern['peak1_idx'])
        extension_price = pattern['peak2_price'] + slope * (extension_idx - pattern['peak2_idx'])
    else:
        extension_price = pattern['peak2_price']

    ax1.plot([times[pattern['peak1_idx']], times[pattern['peak2_idx']], extension_time],
           [pattern['peak1_price'], pattern['peak2_price'], extension_price],
           'yellow', linewidth=2, alpha=0.9, zorder=7, linestyle='--', label='Extended Neckline (Inverse)')

    ax1.scatter([times[ls_idx], times[h_idx], times[rs_idx]],
              [lows_denoised[ls_idx], lows_denoised[h_idx], lows_denoised[rs_idx]],
              color='lime', s=400, marker='^', zorder=8, edgecolors='darkgreen', linewidths=3)

    ax1.text(times[h_idx], lows_denoised[h_idx] * 0.98, "INVERSE H&S (V9)", fontsize=11, ha='center',
           va='top', color='white', fontweight='bold',
           bbox=dict(boxstyle='round', facecolor='green', alpha=0.9))

# Draw Bearish H&S patterns
for pattern in bearish_hs_patterns:
    ls_idx = pattern['ls_idx']
    h_idx = pattern['h_idx']
    rs_idx = pattern['rs_idx']

    ax1.plot([times[ls_idx], times[h_idx]], [highs_denoised[ls_idx], highs_denoised[h_idx]],
           'red', linewidth=4, alpha=0.9, zorder=6)
    ax1.plot([times[h_idx], times[rs_idx]], [highs_denoised[h_idx], highs_denoised[rs_idx]],
           'red', linewidth=4, alpha=0.9, zorder=6)

    extension_idx = min(rs_idx + NECKLINE_EXTENSION_BARS, len(times) - 1)
    extension_time = times[extension_idx]

    if pattern['valley2_idx'] != pattern['valley1_idx']:
        slope = (pattern['valley2_price'] - pattern['valley1_price']) / (pattern['valley2_idx'] - pattern['valley1_idx'])
        extension_price = pattern['valley2_price'] + slope * (extension_idx - pattern['valley2_idx'])
    else:
        extension_price = pattern['valley2_price']

    ax1.plot([times[pattern['valley1_idx']], times[pattern['valley2_idx']], extension_time],
           [pattern['valley1_price'], pattern['valley2_price'], extension_price],
           'orange', linewidth=2, alpha=0.9, zorder=7, linestyle='--', label='Extended Neckline (Bearish)')

    ax1.scatter([times[ls_idx], times[h_idx], times[rs_idx]],
              [highs_denoised[ls_idx], highs_denoised[h_idx], highs_denoised[rs_idx]],
              color='red', s=400, marker='v', zorder=8, edgecolors='darkred', linewidths=3)

    ax1.text(times[h_idx], highs_denoised[h_idx] * 1.02, "BEARISH H&S (V9)", fontsize=11, ha='center',
           va='bottom', color='white', fontweight='bold',
           bbox=dict(boxstyle='round', facecolor='red', alpha=0.9))

ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=12))
ax1.set_ylabel('Price', fontsize=12)
ax1.legend(loc='upper left', fontsize=9)
ax1.grid(True, alpha=0.3)
ax1.set_title(f'{SYMBOL} - V9 H&S Detection (SHOULDER FIX)\nZigZag + Proper Head & Shoulder Validation',
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

# Volume subplot
ax3 = fig.add_subplot(gs[2], sharex=ax1)
ax3.bar(times, volumes, color='gray', alpha=0.5, width=20, label='Volume')
valid_vol_sma = ~np.isnan(volume_sma_20)
ax3.plot(times[valid_vol_sma], volume_sma_20[valid_vol_sma], 'orange', linewidth=1.5, label='Vol SMA(20)')
ax3.set_ylabel('Volume', fontsize=10)
ax3.legend(loc='upper left', fontsize=9)
ax3.grid(True, alpha=0.3)

# Trend indicator subplot
ax4 = fig.add_subplot(gs[3], sharex=ax1)
price_vs_sma = closes_denoised - sma_50
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

output_path = rf'C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\v16_pairs\{SYMBOL}_v16_detection.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\n[V16] Chart saved to: {output_path}")

mt5.shutdown()
plt.close()
