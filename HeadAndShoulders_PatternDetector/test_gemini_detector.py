"""
Test Gemini AI Pattern Detection on Your Charts
Replace API_KEY with your actual Gemini API key
"""

from gemini_pattern_detector import GeminiPatternDetector
import json
import os

# ============================================
# STEP 1: SET YOUR GEMINI API KEY HERE
# ============================================
import os
API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

# ============================================
# STEP 2: Initialize Detector
# ============================================
print("Initializing Gemini AI Pattern Detector...")
detector = GeminiPatternDetector(API_KEY)

# ============================================
# STEP 3: Test on V17 Charts
# ============================================
charts_to_analyze = {
    "EURUSD": r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\v17_pairs\EURUSD_v17_detection.png",
    "GBPUSD": r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\v17_pairs\GBPUSD_v17_detection.png",
    "USDJPY": r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\v17_pairs\USDJPY_v17_detection.png",
    "AUDUSD": r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\v17_pairs\AUDUSD_v17_detection.png",
    "NZDUSD": r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\v17_pairs\NZDUSD_v17_detection.png",
}

print("\n" + "="*70)
print("ANALYZING CHARTS WITH GEMINI AI")
print("="*70)

results_summary = []

for symbol, chart_path in charts_to_analyze.items():
    if not os.path.exists(chart_path):
        print(f"\n[SKIP] {symbol}: Chart not found at {chart_path}")
        continue

    print(f"\n{'='*70}")
    print(f"ANALYZING: {symbol}")
    print(f"{'='*70}")

    try:
        result = detector.analyze_chart(
            image_path=chart_path,
            symbol=symbol,
            timeframe="MONTHLY"
        )

        # Display results
        patterns_found = result.get('patterns_found', [])
        total = result.get('total_patterns', 0)

        print(f"\n[OK] {symbol}: {total} pattern(s) detected")

        if total > 0:
            for i, pattern in enumerate(patterns_found, 1):
                print(f"\n  Pattern {i}:")
                print(f"    Type: {pattern.get('type', 'N/A')}")
                print(f"    Confidence: {pattern.get('confidence', 0)}%")
                print(f"    Left Shoulder: {pattern.get('left_shoulder', {})}")
                print(f"    Head: {pattern.get('head', {})}")
                print(f"    Right Shoulder: {pattern.get('right_shoulder', {})}")
                print(f"    Neckline: {pattern.get('neckline', {})}")
                print(f"    Quality: {pattern.get('quality_notes', 'N/A')}")

                if 'trading_setup' in pattern:
                    setup = pattern['trading_setup']
                    print(f"    Trading Setup:")
                    print(f"      Entry: {setup.get('entry', 'N/A')}")
                    print(f"      Target: {setup.get('target', 'N/A')}")
                    print(f"      Stop: {setup.get('stop', 'N/A')}")
        else:
            print(f"    No valid patterns detected")
            if 'chart_analysis' in result:
                print(f"    Analysis: {result['chart_analysis']}")

        # Save result
        results_summary.append({
            'symbol': symbol,
            'patterns': total,
            'details': result
        })

    except Exception as e:
        print(f"\n[ERROR] {symbol}: {str(e)}")
        continue

# ============================================
# STEP 4: Save Full Results to JSON
# ============================================
output_file = r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\gemini_analysis_results.json"

with open(output_file, 'w') as f:
    json.dump(results_summary, f, indent=2)

print(f"\n{'='*70}")
print(f"ANALYSIS COMPLETE")
print(f"{'='*70}")
print(f"Results saved to: {output_file}")
print(f"Total charts analyzed: {len(results_summary)}")
print(f"Total patterns found: {sum(r['patterns'] for r in results_summary)}")

# ============================================
# STEP 5: Compare with V17 Algorithmic Detection
# ============================================
print(f"\n{'='*70}")
print("COMPARISON: Gemini AI vs V17 Algorithm")
print(f"{'='*70}")

# You can add comparison logic here
# For example, load V17 results and compare with Gemini results

print("""
Next steps:
1. Review gemini_analysis_results.json for detailed findings
2. Compare Gemini detections with your V17 algorithmic detections
3. Use Gemini's confidence scores to filter patterns
4. Combine both approaches for maximum accuracy
""")
