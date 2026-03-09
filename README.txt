BOSS OKE FOREX BOT - PROJECT STRUCTURE
======================================

ROOT FILES:
-----------
mt5_connector.py          - MetaTrader 5 connection module (used by all scripts)
requirements.txt          - Python dependencies

FOLDERS:
--------

1. analysis/
   - analyze_exact_levels.py        - Deep analysis of manual key levels
   - analyze_key_levels.py          - Key level analysis and comparison
   - test_specific_ranges.py        - Test touch counts at specific price levels
   - test_pair.py                   - Test script for pairs
   - *.png                          - Analysis charts

2. trendline/
   - simple_trendline.py            - V1 trendline detector
   - simple_trendline_v2.py         - V2 with trend detection
   - *.png                          - Trendline charts

   MQ5 Indicators:
   - AutoTrendline_v3.mq5           - Latest trendline indicator (BEST)
   Location: C:\Users\ASUS\AppData\Roaming\MetaQuotes\Terminal\...\MQL5\Indicators\

3. pattern_detection/
   - pattern_detector.py            - V1 pattern detector (PatternPy)
   - pattern_detector_v2.py         - V2 with strict criteria (BEST)
   - *.png                          - Pattern charts

   MQ5 Indicators:
   - PatternDetector_v2.mq5         - Latest pattern indicator (BEST)
   Location: C:\Users\ASUS\AppData\Roaming\MetaQuotes\Terminal\...\MQL5\Indicators\

4. key_levels/
   - key_level_detector_FINAL.py    - FINAL VERSION - Works on any pair! (BEST)
   - key_level_FINAL_EURUSD.py      - Visualizes your exact EURUSD levels
   - key_levels_detector.py         - V1 key levels
   - key_levels_detector_v2.py      - V2 with distribution
   - (other versions...)            - Development iterations
   - *.png                          - Key level charts

   MQ5 Indicators:
   - KeyLevels_v3.mq5              - Needs update from FINAL.py version
   Location: C:\Users\ASUS\AppData\Roaming\MetaQuotes\Terminal\...\MQL5\Indicators\

5. PatternPy/
   - GitHub clone of PatternPy library (pattern detection)

CURRENT STATUS:
---------------
✓ COMPLETED:
  - Trendline detection (AutoTrendline_v3.mq5) - WORKING
  - Pattern detection (PatternDetector_v2.mq5) - WORKING
  - Key levels detection (key_level_detector_FINAL.py) - WORKING on EURUSD, GBPUSD, USDJPY

⚠ READY FOR MQ5:
  - Convert key_level_detector_FINAL.py to MQ5 indicator

KEY LEVEL DETECTION ALGORITHM (Learned from EURUSD manual levels):
------------------------------------------------------------------
Your EURUSD manual levels:
  Level 1: 1.48135 - 1.50091 (11 touches, 64% reversal, 85% up range, near major highs)
  Level 2: 1.23561 - 1.25431 (35 touches, 60% reversal, 53% up range, high touches)
  Level 3: 1.05350 - 1.07291 (38 touches, 68% reversal, 30% up range, highest touches)
  Level 4: 0.83235 - 0.85163 (3 touches, 100% reversal, 1% up range, near all-time low)

Detection Pattern:
  1. Zone height: 1.5-2% of price
  2. Minimum 5 touches, 55%+ reversal rate
  3. Bonus for zones near historical extremes (highs/lows)
  4. Distribute across price range: top, middle-upper, middle-lower, bottom
  5. Score = (touches * 5) + (reversals * 10) + (reversal_rate / 10) + (extreme bonus 100)

NEXT STEPS:
-----------
1. Test key_level_detector_FINAL.py on more pairs
2. Build MQ5 indicator from FINAL Python version
3. Integrate all 3 indicators into trading bot
