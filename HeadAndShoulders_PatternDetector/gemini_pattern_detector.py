"""
Gemini AI-Powered Head & Shoulders Pattern Detector
Uses Google's Gemini Vision API to analyze forex charts
"""

import google.generativeai as genai
from PIL import Image
import json
import os

class GeminiPatternDetector:
    def __init__(self, api_key):
        """Initialize Gemini API"""
        genai.configure(api_key=api_key)

        # Use Gemini 2.5 Flash (latest multimodal model with vision support)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

        print("[OK] Gemini AI Pattern Detector initialized")

    def analyze_chart(self, image_path, symbol, timeframe="MONTHLY"):
        """
        Analyze forex chart image for Head & Shoulders patterns

        Args:
            image_path: Path to chart PNG/JPG
            symbol: Forex pair (e.g., "EURUSD")
            timeframe: Chart timeframe

        Returns:
            dict: Pattern detection results with confidence scores
        """

        # Load image
        img = Image.open(image_path)

        # Craft expert prompt for pattern detection
        prompt = f"""
You are a senior institutional forex trader with 20+ years experience in technical analysis.

Analyze this {timeframe} chart for {symbol} and detect Head & Shoulders patterns.

STRICT REQUIREMENTS:
1. **Inverse Head & Shoulders (Bullish)**:
   - Left Shoulder: A swing low
   - Head: Lower low (the lowest point)
   - Right Shoulder: Higher low (similar height to left shoulder)
   - Neckline: Connects the peaks between shoulders and head (resistance line)

2. **Bearish Head & Shoulders**:
   - Left Shoulder: A swing high
   - Head: Higher high (the highest point)
   - Right Shoulder: Lower high (similar height to left shoulder)
   - Neckline: Connects the valleys between shoulders and head (support line)

FOR EACH PATTERN DETECTED, provide:
- Pattern Type: "Inverse H&S" or "Bearish H&S"
- Confidence Score: 0-100% (be strict - only high-quality patterns)
- Left Shoulder location: Approximate date/position and price
- Head location: Approximate date/position and price
- Right Shoulder location: Approximate date/position and price
- Neckline description: Slope (upward/horizontal/downward), approximate price level
- Quality Assessment: Why this is a valid pattern (symmetry, clear structure, etc.)
- Trading Recommendation: Entry point, target, stop loss if pattern is high quality

CRITICAL RULES:
- Head must be the HIGHEST (bearish) or LOWEST (inverse) point
- Shoulders must be adjacent swing points (immediately before/after head)
- Shoulders should be relatively symmetrical in price height
- Neckline must connect meaningful support/resistance points
- Reject noisy, unclear, or poorly-formed patterns

If NO valid Head & Shoulders pattern exists, clearly state "NO VALID PATTERN DETECTED" and explain why.

Respond in JSON format:
{{
    "patterns_found": [
        {{
            "type": "Inverse H&S" or "Bearish H&S",
            "confidence": 85,
            "left_shoulder": {{"date": "2020-05", "price": 1.0500}},
            "head": {{"date": "2020-08", "price": 1.0200}},
            "right_shoulder": {{"date": "2020-11", "price": 1.0480}},
            "neckline": {{"slope": "upward", "price_range": "1.0600-1.0650"}},
            "quality_notes": "Excellent symmetry, clear structure, head is significantly lower",
            "trading_setup": {{"entry": "1.0670", "target": "1.1200", "stop": "1.0450"}}
        }}
    ],
    "total_patterns": 1,
    "chart_analysis": "Overall market structure analysis..."
}}
"""

        # Send to Gemini
        print(f"\n[Gemini] Analyzing {symbol} chart...")
        response = self.model.generate_content([prompt, img])

        # Parse response
        try:
            # Extract JSON from response
            response_text = response.text

            # Try to find JSON in response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                json_str = response_text

            result = json.loads(json_str)

            print(f"[Gemini] Found {result.get('total_patterns', 0)} patterns")
            return result

        except json.JSONDecodeError:
            # Return raw text if JSON parsing fails
            print("[Warning] Could not parse JSON, returning raw text")
            return {
                "raw_response": response.text,
                "patterns_found": [],
                "total_patterns": 0
            }

    def analyze_multiple_charts(self, chart_paths):
        """Analyze multiple charts in batch"""
        results = {}

        for symbol, path in chart_paths.items():
            if os.path.exists(path):
                results[symbol] = self.analyze_chart(path, symbol)
            else:
                print(f"[Error] Chart not found: {path}")

        return results

    def compare_with_algorithmic_detection(self, gemini_result, algo_result):
        """
        Compare Gemini AI detection with your V17 algorithmic detection

        Args:
            gemini_result: Results from Gemini
            algo_result: Results from your V17 detector

        Returns:
            Comparison analysis
        """
        comparison = {
            "gemini_patterns": gemini_result.get("total_patterns", 0),
            "algo_patterns": len(algo_result) if algo_result else 0,
            "agreement": False,
            "differences": []
        }

        # Add comparison logic here
        # Check if both detected same pattern type, similar positions, etc.

        return comparison


def example_usage():
    """Example of how to use Gemini detector"""

    # Your API key
    API_KEY = "YOUR_GEMINI_API_KEY_HERE"

    # Initialize detector
    detector = GeminiPatternDetector(API_KEY)

    # Analyze single chart
    result = detector.analyze_chart(
        image_path=r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\v17_pairs\EURUSD_v17_detection.png",
        symbol="EURUSD",
        timeframe="MONTHLY"
    )

    print("\n" + "="*70)
    print("GEMINI AI ANALYSIS RESULTS")
    print("="*70)
    print(json.dumps(result, indent=2))

    # Analyze multiple charts
    charts = {
        "EURUSD": r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\v17_pairs\EURUSD_v17_detection.png",
        "GBPUSD": r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\v17_pairs\GBPUSD_v17_detection.png",
        "USDJPY": r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\v17_pairs\USDJPY_v17_detection.png",
    }

    batch_results = detector.analyze_multiple_charts(charts)

    for symbol, result in batch_results.items():
        print(f"\n{symbol}: {result.get('total_patterns', 0)} patterns detected")


if __name__ == "__main__":
    print("""
    GEMINI AI PATTERN DETECTOR
    ==========================

    To use:
    1. Set your API key in example_usage()
    2. Run: python gemini_pattern_detector.py

    Or use in your code:
        from gemini_pattern_detector import GeminiPatternDetector
        detector = GeminiPatternDetector(api_key)
        result = detector.analyze_chart(image_path, symbol)
    """)
