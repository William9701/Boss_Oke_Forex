import sys
sys.path.append(r'C:\Users\ASUS\Desktop\Boss_Oke_Forex\key_levels')

from key_level_detector_v4 import KeyLevelDetectorV4

detector = KeyLevelDetectorV4()

# Test AUDUSD
symbol = 'AUDUSD'
df = detector.get_monthly_data(symbol, num_bars=300)

if df is not None:
    zones = detector.find_key_levels(df, symbol, num_levels=4)

    if zones:
        detector.print_levels(zones, symbol)
        detector.visualize(df, zones, symbol)
    else:
        print(f"No levels found for {symbol}")
